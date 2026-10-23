"""Calibrate the app's Gemini evaluator on the rated YouTube mock tests (roadmap A4).

Uses the backend's own request builder, validator and overall rule, so the numbers describe the app.
Each video: candidate speech (from diarize.py) is split into answers at the examiner's turns; every answer
becomes one turn (audio clip + transcript segments), exactly like an app session.

Run from the repo root: .venv/Scripts/python.exe scripts/band-dataset/calibrate.py [--limit N] [--sleep S]
Resumable: calibration/<id>.json is skipped. Summary: calibration/summary.json + calibration_report.md
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# code lives in scripts/band-dataset/; the data stays in the git-ignored private folder
REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "data" / "private" / "youtube-band-dataset"
sys.path.insert(0, str(REPO / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "speakwe.settings")
import django  # noqa: E402

django.setup()
from django.conf import settings  # noqa: E402

from ielts.assessment.errors import GeminiError, GeminiOutputError  # noqa: E402
from ielts.assessment.features import session_features, turn_features  # noqa: E402
from ielts.assessment.gemini import GeminiClient  # noqa: E402
from ielts.assessment.request import build, segment_map  # noqa: E402
from ielts.assessment.scoring import CRITERIA, overall  # noqa: E402
from ielts.assessment.validate import fix_priority_order, validate  # noqa: E402

import imageio_ffmpeg  # noqa: E402

OUT = ROOT / "calibration"
LOG = ROOT / "calibrate.log"
SEG_GAP_S = 1.2          # a new transcript segment starts after a pause this long inside one answer
MIN_ANSWER_S = 2.0       # ignore tiny candidate fragments ("yes", "okay")


def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def clip_mp3(src: Path, start: float, end: float) -> bytes:
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-ss", f"{start:.2f}", "-to", f"{end:.2f}", "-i", str(src),
           "-ac", "1", "-ar", "16000", "-b:a", "32k", "-f", "mp3", "pipe:1"]
    return subprocess.run(cmd, capture_output=True, check=True, timeout=120).stdout


def answers(dia: dict) -> list[dict]:
    """Group candidate words into answers: a new answer starts whenever the examiner spoke in between."""
    exam_turns = [t for t in dia["turns"] if t["speaker"] != dia["candidate"]]
    groups, current, last_end = [], [], None
    for w in dia["candidate_words"]:
        interrupted = last_end is not None and any(t["start"] >= last_end and t["end"] <= w["s"] and t["end"] - t["start"] > 0.8
                                                   for t in exam_turns)
        if interrupted and current:
            groups.append(current)
            current = []
        current.append(w)
        last_end = w["e"]
    if current:
        groups.append(current)
    return [g for g in groups if g[-1]["e"] - g[0]["s"] >= MIN_ANSWER_S]


def question_before(dia: dict, start: float, words_all: list[dict]) -> str:
    """Examiner words spoken in the 15 s before an answer: the task text for the prompt."""
    text = "".join(w["w"] for w in words_all if w.get("speaker") not in (None, dia["candidate"]) and start - 15 <= w["s"] < start)
    return text.strip()[-200:] or "(question not transcribed)"


def build_session(vid: str, dia: dict, words_all: list[dict]):
    src = next((ROOT / "audio").glob(f"*/{vid}.m4a"))
    turns = []
    for n, words in enumerate(answers(dia), 1):
        start, end = max(0.0, words[0]["s"] - 0.3), words[-1]["e"] + 0.3
        rel = [{**w, "s": round(w["s"] - start, 3), "e": round(w["e"] - start, 3)} for w in words]
        segs, cur = [], [rel[0]]
        for a, b in zip(rel, rel[1:]):
            if b["s"] - a["e"] > SEG_GAP_S:
                segs.append(cur)
                cur = []
            cur.append(b)
        segs.append(cur)
        turns.append({
            "turn_id": f"t{n}", "part": 1, "kind": "question", "task_text": question_before(dia, words[0]["s"], words_all),
            "segments": [{"id": f"t{n}-{k}", "start_ms": round(s[0]["s"] * 1000), "end_ms": round(s[-1]["e"] * 1000), "words": s}
                         for k, s in enumerate(segs, 1)],
            "features": turn_features(rel, end - start), "audio": clip_mp3(src, start, end), "duration_s": end - start,
        })
    return turns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=4.0, help="pause between Gemini calls (free-tier rate limits)")
    args = ap.parse_args()
    client = GeminiClient(settings.GEMINI_API_KEY, settings.GEMINI_MODEL)
    labels = {r["id"]: r for r in csv.DictReader((ROOT / "labels.csv").open(encoding="utf-8"))}
    OUT.mkdir(exist_ok=True)
    done = 0
    for dpath in sorted((ROOT / "diarization").glob("*.json")):
        vid = dpath.stem
        out = OUT / f"{vid}.json"
        if out.exists() or (args.limit and done >= args.limit):
            continue
        dia = json.loads(dpath.read_text(encoding="utf-8"))
        tr = json.loads((ROOT / "transcripts" / f"{vid}.json").read_text(encoding="utf-8"))
        cand = {(w["s"], w["e"]) for w in dia["candidate_words"]}
        words_all = [{**w, "speaker": dia["candidate"] if (w["s"], w["e"]) in cand else "other"}
                     for s in tr["segments"] for w in s["words"]]
        try:
            turns = build_session(vid, dia, words_all)
            sess = session_features([(t["features"], t["duration_s"]) for t in turns])
            body = build(mode="full", scope="full_test", parts=[1, 2, 3], turns=turns, session_features=sess)
            segments = segment_map(turns)
            base, result, errors = body["contents"], None, []
            for attempt in range(3):
                try:
                    output = client.generate(body)
                except GeminiOutputError:
                    continue
                except GeminiError as e:
                    if e.status == 429:          # rate limited: wait and retry the same attempt
                        log(f"429 on {vid}; waiting 60 s")
                        time.sleep(60)
                        continue
                    if e.status == 400 and "responseJsonSchema" in body["generationConfig"]:
                        body["generationConfig"].pop("responseJsonSchema")
                        continue
                    raise
                fix_priority_order(output)
                errors = validate(output, segments, "full_test")
                if not errors:
                    result = output
                    break
                body["contents"] = base + [
                    {"role": "model", "parts": [{"text": json.dumps(output, ensure_ascii=False)}]},
                    {"role": "user", "parts": [{"text": "The SpeakWE validator rejected your answer:\n- " + "\n- ".join(errors[:15])
                                                + "\nFix every problem and return the complete JSON again."}]}]
            bands = {k: result["criteria"][k]["band"] for k in CRITERIA} if result else None
            lab = labels.get(vid, {})
            out.write_text(json.dumps({
                "id": vid, "label_group": lab.get("band_group"), "label_exact": lab.get("band_exact"),
                "examiner_overall": lab.get("examiner_overall"), "answers": len(turns), "features": sess,
                "gemini_bands": bands, "gemini_overall": overall(bands, "full_test") if bands else None,
                "valid": result is not None, "errors": errors[:10], "report": result, "model": client.model,
            }, ensure_ascii=False), encoding="utf-8")
            done += 1
            log(f"ok {vid} label={lab.get('band_exact')} gemini={overall(bands, 'full_test') if bands else 'INVALID'} answers={len(turns)}")
        except Exception as e:
            log(f"FAIL {vid}: {type(e).__name__}: {str(e)[:200]}")
        time.sleep(args.sleep)
    log(f"finished {done} videos")


if __name__ == "__main__":
    main()
