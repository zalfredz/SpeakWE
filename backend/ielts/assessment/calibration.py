"""Overall band from the ML calibration models (scripts/band-dataset/baseline.py writes calibration.json).

Both are ridge regressions trained on examiner-labelled mock tests:
  "a" uses Gemini's four criterion bands + fluency/lexical features and is the overall the learner sees;
  "b" uses only the local features and is stored in shadow until it matches "a" (then Gemini can go).
No Django or numpy imports, so baseline.py can share inputs() from the ML venv.
"""
import json
import math
from pathlib import Path

MODELS_PATH = Path(__file__).with_name("calibration.json")


def lexical(words: list[dict]) -> dict:
    toks = ["".join(c for c in w["w"].lower() if c.isalpha() or c == "'") for w in words]
    toks = [t for t in toks if t]
    if not toks:
        return {"guiraud": 0.0, "mean_word_len": 0.0, "long_word_ratio": 0.0}
    return {"guiraud": len(set(toks)) / math.sqrt(len(toks)), "mean_word_len": sum(map(len, toks)) / len(toks),
            "long_word_ratio": sum(len(t) >= 7 for t in toks) / len(toks)}


def inputs(sess: dict, words: list[dict], bands: dict | None) -> dict:
    """Model inputs: session_features() output, the candidate's words, Gemini's criterion bands (or None)."""
    per_min = lambda k: sess[k] / max(sess["speech_s"], 1) * 60   # counts scale with test length
    values = {k: sess[k] for k in ("pause_ratio", "mean_length_of_run", "speech_rate_wpm", "fillers_per_min")}
    values |= {"repetitions": per_min("repetitions"), "self_corrections": per_min("self_corrections")} | lexical(words)
    return values | (bands or {})


def half_band(v: float) -> float:
    return min(9.0, max(1.0, math.floor(v * 2 + 0.5) / 2))   # x.25 rounds up, like the IELTS overall rule


def predict(model: dict, values: dict) -> float:
    z = sum(c * (values[k] - m) / s for k, c, m, s in zip(model["features"], model["coef"], model["mean"], model["scale"]))
    return half_band(model["intercept"] + z)


def load() -> dict:
    return json.loads(MODELS_PATH.read_text(encoding="utf-8")) if MODELS_PATH.exists() else {}
