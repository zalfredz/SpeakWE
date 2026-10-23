"""Fluency signals from word timestamps. They support Gemini's judgement; they are not scores."""
import re

PAUSE_S = 0.3
FILLERS = {"um", "uh", "er", "erm", "hmm", "mm", "uhm", "umm"}


def _clean(word: str) -> str:
    return re.sub(r"[^a-z'-]", "", word.lower())


def turn_features(words: list[dict], duration_s: float) -> dict:
    tokens = [_clean(x["w"]) for x in words]
    pauses = [words[i + 1]["s"] - words[i]["e"] for i in range(len(words) - 1)]
    long_pauses = [p for p in pauses if p >= PAUSE_S]
    runs, run = [], 0
    for i in range(len(words)):
        run += 1
        if i == len(words) - 1 or pauses[i] >= PAUSE_S:
            runs.append(run)
            run = 0
    content = [t.rstrip("-") for t in tokens if t.rstrip("-") not in FILLERS]
    minutes = duration_s / 60 if duration_s else 0
    return {
        "duration_s": round(duration_s, 2),
        "speech_s": round(words[-1]["e"] - words[0]["s"], 2) if words else 0.0,
        "words": len(words),
        "pause_ratio": round(sum(long_pauses) / duration_s, 3) if duration_s else 0.0,
        "mean_length_of_run": round(sum(runs) / len(runs), 2) if runs else 0.0,
        "speech_rate_wpm": round(len(words) / minutes, 1) if minutes else 0.0,
        "fillers_per_min": round(sum(t in FILLERS for t in tokens) / minutes, 1) if minutes else 0.0,
        "repetitions": sum(content[i] == content[i + 1] and content[i] != "" for i in range(len(content) - 1)),
        "self_corrections": sum(t.endswith("-") for t in tokens),
    }


def session_features(turns: list[tuple[dict, float]]) -> dict:
    """Combine per-turn features; ratios are weighted by answer duration."""
    total = sum(d for _, d in turns)
    if not total:
        return {"duration_s": 0.0, "speech_s": 0.0, "pause_ratio": 0.0, "mean_length_of_run": 0.0,
                "speech_rate_wpm": 0.0, "fillers_per_min": 0.0, "repetitions": 0, "self_corrections": 0}
    weighted = lambda k: round(sum(f[k] * d for f, d in turns) / total, 3)
    return {
        "duration_s": round(total, 2),
        "speech_s": round(sum(f["speech_s"] for f, _ in turns), 2),
        "pause_ratio": weighted("pause_ratio"),
        "mean_length_of_run": weighted("mean_length_of_run"),
        "speech_rate_wpm": weighted("speech_rate_wpm"),
        "fillers_per_min": weighted("fillers_per_min"),
        "repetitions": sum(f["repetitions"] for f, _ in turns),
        "self_corrections": sum(f["self_corrections"] for f, _ in turns),
    }
