"""YouTube IELTS band dataset: metadata -> audio -> verbatim transcript -> score candidates.

Usage (from the repo root):  .venv/Scripts/python.exe scripts/band-dataset/pipeline.py all
Steps are resumable: finished files are skipped.
"""
import csv, json, os, re, sys, time
from pathlib import Path

# CUDA DLLs come from the nvidia-* pip wheels; Windows needs their bin dirs on the DLL path.
for _d in (Path(sys.prefix) / "Lib/site-packages/nvidia").glob("*/bin"):
    os.add_dll_directory(str(_d))
    os.environ["PATH"] = str(_d) + os.pathsep + os.environ["PATH"]

# code lives in scripts/band-dataset/; the data (audio, transcripts, labels) stays in the git-ignored private folder
ROOT = Path(__file__).resolve().parents[2] / "data" / "private" / "youtube-band-dataset"
META, AUDIO, TRANS = ROOT / "metadata", ROOT / "audio", ROOT / "transcripts"
LOG = ROOT / "progress.log"


def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_links():
    band, rows = None, []
    for line in (ROOT / "links.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("BAND"):
            band = float(line.split()[1])
        elif "http" in line:
            vid = re.split(r"[/=]", line.strip())[-1]
            rows.append({"id": vid, "band": band, "url": f"https://www.youtube.com/watch?v={vid}"})
    return rows


def audio_file(r):
    """Finished audio file for a row, ignoring yt-dlp partial downloads."""
    return next((p for p in (AUDIO / f"band{r['band']:g}").glob(f"{r['id']}.*") if p.suffix in (".m4a", ".webm", ".opus", ".mp3")), None)


def ydl(opts):
    import yt_dlp
    return yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, **opts})


def step_meta(rows):
    META.mkdir(exist_ok=True)
    for r in rows:
        out = META / f"{r['id']}.json"
        if out.exists():
            continue
        try:
            info = ydl({"skip_download": True}).extract_info(r["url"], download=False)
            keep = {k: info.get(k) for k in ("id", "title", "channel", "uploader", "duration", "upload_date", "description", "webpage_url")}
            out.write_text(json.dumps(keep, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as e:
            log(f"meta FAIL {r['id']}: {e}")


def step_audio(rows):
    for r in rows:
        d = AUDIO / f"band{r['band']:g}"
        d.mkdir(parents=True, exist_ok=True)
        if audio_file(r):
            continue
        try:
            # m4a needs no ffmpeg; faster-whisper decodes it directly
            ydl({"format": "bestaudio[ext=m4a]/bestaudio", "outtmpl": str(d / "%(id)s.%(ext)s")}).download([r["url"]])
            log(f"audio ok {r['id']}")
        except Exception as e:
            log(f"audio FAIL {r['id']}: {e}")


# Prompt with fillers nudges Whisper to keep disfluencies instead of cleaning them.
PROMPT = "Umm, so, uh, I- I mean, well, hmm, you know, like, er, I think... yeah."


def step_transcribe(rows, model_name="medium.en"):
    from faster_whisper import WhisperModel, BatchedInferencePipeline
    TRANS.mkdir(exist_ok=True)
    # Batched mode measured on GTX 1650: 7.9x realtime and keeps fillers (54 vs 1 in sequential mode).
    model = BatchedInferencePipeline(WhisperModel(model_name, device="cuda", compute_type="int8_float16"))
    for r in rows:
        out = TRANS / f"{r['id']}.json"
        src = audio_file(r)
        if out.exists() or not src:
            continue
        t0 = time.time()
        try:
            segs, info = model.transcribe(str(src), language="en", initial_prompt=PROMPT, word_timestamps=True, batch_size=8)
            segs = [{"start": s.start, "end": s.end, "text": s.text.strip(),
                     "words": [{"w": w.word, "s": w.start, "e": w.end, "p": round(w.probability, 3)} for w in s.words]}
                    for s in segs]
            out.write_text(json.dumps({"id": r["id"], "band_label": r["band"], "model": model_name, "mode": "batched8",
                                       "audio_seconds": info.duration, "segments": segs}, ensure_ascii=False), encoding="utf-8")
            log(f"trans ok {r['id']} {info.duration:.0f}s audio in {time.time() - t0:.0f}s")
        except Exception as e:
            log(f"trans FAIL {r['id']}: {e}")


CRIT = r"(fluency(?: and coherence)?|lexical(?: resource)?|vocabulary|grammar|grammatical(?: range(?: and accuracy)?)?|pronunciation|overall|band(?: score)?)"
SCORE_RE = re.compile(CRIT + r"[^0-9\n]{0,25}?\b([4-9](?:\.5)?)\b", re.I)


# Manual corrections after reviewing metadata (2026-10-22).
OVERRIDES = {
    "vLPJ2WPCX0I": {"band_exact": "9", "note": "listed under BAND 8 but title says Band 9"},
    "WAVTPzCdLbA": {"band_exact": "8", "note": "band set by user (title only says 'To Get Band 8')"},
    "u5zmVCfCb7o": {"band_exact": "9", "note": "band set by user (no band in title/description)"},
}
RANGE_RE = re.compile(r"band(?: score)?(?: of)?\s*([4-9](?:\.[05])?)(?:\s*[-–]\s*([4-9](?:\.[05])?))?", re.I)


def step_labels(rows):
    """labels.csv: band_group = whole band (7 covers 7.0-7.5), band_exact from the video title."""
    with (ROOT / "labels.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        # spoken_scores.csv is curated by hand from examiner feedback in the transcripts
        sp_path = ROOT / "spoken_scores.csv"
        spoken = {x["id"]: x for x in csv.DictReader(sp_path.open(encoding="utf-8"))} if sp_path.exists() else {}
        w.writerow(["id", "band_group", "band_exact", "listed_band", "label_source", "needs_check", "examiner_overall", "note"])
        for r in rows:
            title = json.loads((META / f"{r['id']}.json").read_text(encoding="utf-8"))["title"]
            m = RANGE_RE.search(title)
            exact = (f"{float(m[1]):g}-{float(m[2]):g}" if m[2] else f"{float(m[1]):g}") if m else ""
            o = OVERRIDES.get(r["id"], {})
            exact = o.get("band_exact", exact)
            group = int(float(exact.split("-")[0])) if exact else ""
            needs = o.get("needs_check", not exact or ("band_exact" not in o and group != int(r["band"])))
            src = "override" if "band_exact" in o else "title"
            w.writerow([r["id"], group, exact, f"{r['band']:g}", src, needs, spoken.get(r["id"], {}).get("spoken_overall", ""), o.get("note", "")])


def step_scores(rows):
    """Candidate scores found in title/description/transcript. Candidates only: review before use."""
    with (ROOT / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "band_label", "title", "channel", "duration_s", "has_audio", "has_transcript", "score_candidates"])
        for r in rows:
            m = META / f"{r['id']}.json"
            meta = json.loads(m.read_text(encoding="utf-8")) if m.exists() else {}
            t = TRANS / f"{r['id']}.json"
            text = " ".join(s["text"] for s in json.loads(t.read_text(encoding="utf-8"))["segments"]) if t.exists() else ""
            found = []
            for where, src in (("title", meta.get("title") or ""), ("desc", meta.get("description") or ""), ("transcript", text[-3000:])):
                found += [f"{where}:{k.lower()}={v}" for k, v in SCORE_RE.findall(src)]
            w.writerow([r["id"], r["band"], meta.get("title"), meta.get("channel"), meta.get("duration"),
                        audio_file(r) is not None, t.exists(), " | ".join(dict.fromkeys(found))])


if __name__ == "__main__":
    rows = read_links()
    assert len({r["id"] for r in rows}) == len(rows), "duplicate ids in links.txt"
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("meta", "all"): step_meta(rows)
    if step in ("audio", "all"): step_audio(rows)
    if step in ("transcribe", "all"): step_transcribe(rows)
    if step in ("scores", "all", "meta", "labels"): step_labels(rows)
    if step in ("scores", "all", "meta"): step_scores(rows)
