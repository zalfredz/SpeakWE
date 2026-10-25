"""Separate examiner and candidate speech in the band videos (roadmap A2).

Run from the repo root: .venv-ml/Scripts/python.exe scripts/band-dataset/diarize.py [--limit N]
Resumable: videos with an existing diarization/<id>.json are skipped.
Output per video: diarization/<id>.json = {turns: [{start, end, speaker}], test_end, candidate, examiner, candidate_words: [...]}
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

# code lives in scripts/band-dataset/; the data stays in the git-ignored private folder
REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "data" / "private" / "youtube-band-dataset"
OUT = ROOT / "diarization"
LOG = ROOT / "diarize.log"
# ffmpeg binary that ships with imageio-ffmpeg in the app venv
FFMPEG = next((REPO / ".venv/Lib/site-packages/imageio_ffmpeg/binaries").glob("ffmpeg*.exe"))
END_RE = re.compile(r"(this is|that's|that is) the end of (the|your) (speaking )?test|end of the (speaking )?test|let'?s (start|move on to|go through) (with )?(the |some |your )?feedback", re.I)


def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def env_token():
    for line in (REPO / "backend/.env").read_text(encoding="utf-8").splitlines():
        if line.startswith("HF_TOKEN="):
            return line.split("=", 1)[1].strip()
    return os.environ.get("HF_TOKEN")


def load_audio(path: Path) -> np.ndarray:
    raw = subprocess.run([str(FFMPEG), "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-f", "f32le", "pipe:1"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def test_end(words) -> float | None:
    """Time the examiner closes the test (feedback follows). Searches a sliding window of words after the first third."""
    if not words:
        return None
    total = words[-1]["e"]
    for i in range(len(words)):
        if words[i]["s"] < total * 0.33:
            continue
        window = "".join(w["w"] for w in words[i:i + 12])
        if END_RE.search(window):
            return words[i]["s"]
    return None


def assign(words, turns):
    """Speaker of each word = the diarization turn that covers the word's midpoint."""
    out, j = [], 0
    for w in words:
        mid = (w["s"] + w["e"]) / 2
        while j < len(turns) and turns[j]["end"] < mid:
            j += 1
        speaker = turns[j]["speaker"] if j < len(turns) and turns[j]["start"] <= mid else None
        out.append({**w, "speaker": speaker})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    import torch
    from pyannote.audio import Pipeline
    from pyannote.audio.core.task import Problem, Resolution, Specifications
    # torch>=2.6 loads weights_only; allowlist the few classes the official pyannote checkpoints pickle
    torch.serialization.add_safe_globals([torch.torch_version.TorchVersion, Problem, Resolution, Specifications])
    pipe = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=env_token())
    pipe.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    OUT.mkdir(exist_ok=True)
    ids = [p.stem for p in sorted((ROOT / "transcripts").glob("*.json"))]
    done = 0
    for vid in ids:
        if args.limit and done >= args.limit:
            break
        out = OUT / f"{vid}.json"
        if out.exists():
            continue
        t0 = time.time()
        try:
            audio_path = next((ROOT / "audio").glob(f"*/{vid}.m4a"))
            wav = load_audio(audio_path)
            dia = pipe({"waveform": torch.from_numpy(wav)[None], "sample_rate": 16000}, min_speakers=2, max_speakers=3)
            turns = [{"start": round(seg.start, 2), "end": round(seg.end, 2), "speaker": spk}
                     for seg, _, spk in dia.itertracks(yield_label=True)]
            tr = json.loads((ROOT / "transcripts" / f"{vid}.json").read_text(encoding="utf-8"))
            words = assign([w for s in tr["segments"] for w in s["words"]], turns)
            end = test_end(words)
            in_test = [w for w in words if end is None or w["s"] < end]
            # candidate = most speech time during the test; examiner = most question-ending words
            talk, questions = {}, {}
            for w in in_test:
                if w["speaker"]:
                    talk[w["speaker"]] = talk.get(w["speaker"], 0) + (w["e"] - w["s"])
                    if w["w"].rstrip().endswith("?"):
                        questions[w["speaker"]] = questions.get(w["speaker"], 0) + 1
            candidate = max(talk, key=talk.get) if talk else None
            examiner = max(questions, key=questions.get) if questions else None
            out.write_text(json.dumps({
                "id": vid, "turns": turns, "test_end": end, "candidate": candidate, "examiner": examiner,
                "speaker_talk_s": {k: round(v, 1) for k, v in talk.items()},
                "candidate_words": [w for w in in_test if w["speaker"] == candidate],
            }, ensure_ascii=False), encoding="utf-8")
            done += 1
            log(f"ok {vid} {len(wav)/16000:.0f}s audio in {time.time()-t0:.0f}s speakers={sorted(talk)} cand={candidate} exam={examiner} end={end}")
        except Exception as e:  # keep going; failures are listed in the log
            log(f"FAIL {vid}: {e}")
    log(f"finished {done} videos")


if __name__ == "__main__":
    sys.exit(main())
