"""ML baseline on top of the Gemini calibration (roadmap A5).

Learns examiner overall band from Gemini's four criterion bands + the app's fluency features + simple lexical
features of the candidate's words. Validation holds out one YouTube channel at a time (leave-one-channel-out), so
a channel's recording style or labelling habits cannot leak into its own score. Hyperparameters are tuned inside
each training fold only (nested CV). Targets are examiner labels only, never Gemini scores, so the models do not
learn Gemini's habit of pulling every band toward 6.

Run from the repo root: .venv-ml/Scripts/python.exe scripts/band-dataset/baseline.py
Writes baseline_report.md (private dataset folder) and backend/ielts/assessment/calibration.json: ridge model "a"
(with Gemini, shown to learners) and "b" (local features only, shadow), both fitted on every video.
"""
import csv
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, GroupKFold, LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "data" / "private" / "youtube-band-dataset"
sys.path.insert(0, str(REPO / "backend"))
from ielts.assessment.calibration import MODELS_PATH, half_band, inputs, predict  # noqa: E402  (no Django needed)

CRITERIA = ["fc", "lr", "gra", "p"]
LOCAL = ["pause_ratio", "mean_length_of_run", "speech_rate_wpm", "fillers_per_min", "repetitions", "self_corrections",
         "guiraud", "mean_word_len", "long_word_ratio"]
FEATURES = {"a": CRITERIA + LOCAL, "b": LOCAL}


def label_band(text):
    """Same as calibrate.label_band (that module needs Django, which .venv-ml lacks)."""
    parts = [float(p) for p in (text or "").split("-") if p]
    return sum(parts) / len(parts) if parts else None


def load():
    channel = {r["id"]: r["channel"] for r in csv.DictReader((ROOT / "manifest.csv").open(encoding="utf-8"))}
    rows = []
    for p in sorted((ROOT / "calibration").glob("*.json")):
        if p.stem == "summary":
            continue
        r = json.loads(p.read_text(encoding="utf-8"))
        y = label_band(r["label_exact"])
        if not r["valid"] or y is None:
            continue
        dia = json.loads((ROOT / "diarization_clean" / p.name).read_text(encoding="utf-8"))
        rows.append({"id": r["id"], "channel": channel[r["id"]], "group": r["label_group"], "y": y,
                     "gemini": r["gemini_overall"], "values": inputs(r["features"], dia["candidate_words"], r["gemini_bands"])})
    return rows


ielts_round = np.vectorize(half_band)

MODELS = {
    "ridge": (lambda: make_pipeline(StandardScaler(), Ridge()), {"ridge__alpha": [0.1, 1, 3, 10, 30, 100]}),
    "gbm": (lambda: HistGradientBoostingRegressor(loss="absolute_error", random_state=0),
            {"max_depth": [2, 3], "learning_rate": [0.03, 0.1], "max_iter": [100, 300], "min_samples_leaf": [5, 10]}),
}


def tuned(name, X, y, groups):
    make, grid = MODELS[name]
    # inner CV is grouped by channel too; fewer channels in a fold -> fewer splits
    inner = GroupKFold(n_splits=min(3, len(set(groups))))
    return GridSearchCV(make(), grid, cv=inner, scoring="neg_mean_absolute_error").fit(X, y, groups=groups)


def report(name, pred, rows):
    y = np.array([r["y"] for r in rows])
    err = ielts_round(pred) - y
    by = {}
    for g in sorted({r["group"] for r in rows}):
        m = np.array([r["group"] == g for r in rows])
        by[g] = (int(m.sum()), np.abs(err[m]).mean(), err[m].mean(), (np.abs(err[m]) <= 0.5).mean())
    return name, (len(y), np.abs(err).mean(), err.mean(), (np.abs(err) <= 0.5).mean()), by


def export(search, features):
    """Ridge pipeline -> plain numbers the backend evaluates without sklearn."""
    scaler, ridge = search.best_estimator_
    return {"features": features, "mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist(),
            "coef": ridge.coef_.tolist(), "intercept": float(ridge.intercept_), "alpha": search.best_params_["ridge__alpha"]}


def main():
    assert list(ielts_round([6.24, 6.25, 9.7, 0.2])) == [6.0, 6.5, 9.0, 1.0]
    rows = load()
    y = np.array([r["y"] for r in rows])
    groups = np.array([r["channel"] for r in rows])
    X = {k: np.array([[r["values"][f] for f in feats] for r in rows]) for k, feats in FEATURES.items()}
    exported = {}
    results = [report("Gemini (as is)", np.array([r["gemini"] for r in rows]), rows)]
    for key, name in [("a", "ridge"), ("a", "gbm"), ("b", "ridge")]:
        pred = np.zeros(len(y))
        for tr, te in LeaveOneGroupOut().split(X[key], y, groups):
            pred[te] = tuned(name, X[key][tr], y[tr], groups[tr]).predict(X[key][te])
        label = "with Gemini" if key == "a" else "without Gemini"
        results.append(report(f"{name} {label} (leave-one-channel-out)", pred, rows))
        if name == "ridge":
            search = tuned("ridge", X[key], y, groups)
            exported[key] = export(search, FEATURES[key]) | {
                "cv_mae": round(float(np.abs(ielts_round(pred) - y).mean()), 3), "videos": len(rows),
                "channels": len(set(groups)), "trained": str(date.today())}
            # the exported numbers must reproduce sklearn's predictions
            assert all(predict(exported[key], r["values"]) == half_band(v) for r, v in zip(rows, search.predict(X[key])))
    MODELS_PATH.write_text(json.dumps(exported, indent=1), encoding="utf-8")

    lines = ["# ML baseline", "", f"{len(rows)} videos from {len(set(groups))} channels. "
             "Each channel is predicted by a model that never saw it; hyperparameters tuned inside training folds only. "
             "Predictions rounded to half bands.", ""]
    for name, (n, mae, bias, w), by in results:
        lines += [f"## {name}", "", "| Band | n | MAE | bias | within 0.5 |", "| --- | --- | --- | --- | --- |"]
        for g, (gn, gm, gb, gw) in by.items():
            lines.append(f"| {g} | {gn} | {gm:.2f} | {gb:+.2f} | {gw:.0%} |")
        lines += [f"| all | {n} | {mae:.2f} | {bias:+.2f} | {w:.0%} |", ""]
    for key, m in exported.items():
        lines.append(f"Exported model {key}: alpha {m['alpha']}, standardised weights " + ", ".join(
            f"{k} {c:+.2f}" for k, c in sorted(zip(m["features"], m["coef"]), key=lambda t: -abs(t[1]))))
    (ROOT / "baseline_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
