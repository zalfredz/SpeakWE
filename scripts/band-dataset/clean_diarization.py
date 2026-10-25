"""Clean diarize.py output before calibration (roadmap A2).

pyannote sometimes merges examiner and candidate into one speaker, so examiner questions leak into the
"candidate" speech. Here the speaker is decided per sentence (majority of its words), question sentences are
treated as examiner speech unless they sit inside one speaker's flowing speech (rhetorical), and videos where the candidate still owns many questions are flagged "merged".

Run from the repo root: python scripts/band-dataset/clean_diarization.py [--selftest]
Reads diarization/<id>.json + transcripts/<id>.json, writes diarization_clean/<id>.json (same fields as
diarize.py plus quality, candidate_questions). Fast and idempotent: re-run after new diarization files appear.
"""
import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "data" / "private" / "youtube-band-dataset"
MERGED_QUESTIONS = 10   # clean videos show 0-9 candidate questions; merged speakers show 11+
EXAMINER_Q = "EXAMINER_Q"
RHETORICAL_GAP_S = 0.6   # "Why? Because..." flows on with no pause; an examiner question is followed by a turn change


def sentences(words):
    """Split words into sentences at terminal punctuation."""
    out, cur = [], []
    for w in words:
        cur.append(w)
        if w["w"].rstrip().endswith((".", "?", "!")):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def majority(sentence):
    talk = {}
    for w in sentence:
        if w.get("speaker"):
            talk[w["speaker"]] = talk.get(w["speaker"], 0) + (w["e"] - w["s"])
    return max(talk, key=talk.get) if talk else None


def clean(dia, words):
    """`words` = every transcript word with its diarization speaker (as diarize.assign gives)."""
    end = dia["test_end"]
    in_test = [w for w in words if end is None or w["s"] < end]
    sents = [[majority(s), s[-1]["w"].rstrip().endswith("?"), s] for s in sentences(in_test)]
    # a question inside one speaker's flowing speech is rhetorical: keep it as that speaker's statement
    for i in range(1, len(sents) - 1):
        (pspk, pq, prev), (spk, q, s), (nspk, nq, nxt) = sents[i - 1], sents[i], sents[i + 1]
        if q and not pq and not nq and pspk == spk == nspk                 and s[0]["s"] - prev[-1]["e"] <= RHETORICAL_GAP_S and nxt[0]["s"] - s[-1]["e"] <= RHETORICAL_GAP_S:
            sents[i][1] = False
    talk, questions = {}, {}
    for spk, is_q, s in sents:
        if spk is None:
            continue
        if is_q:
            questions[spk] = questions.get(spk, 0) + 1
        else:
            talk[spk] = talk.get(spk, 0) + sum(w["e"] - w["s"] for w in s)
    candidate = max(talk, key=talk.get) if talk else None
    others = {k: v for k, v in questions.items() if k != candidate}
    examiner = max(others, key=others.get) if others else None
    cand_q = questions.get(candidate, 0)
    # question sentences become examiner turns, so calibrate.py splits answers at them
    q_turns = [{"start": s[0]["s"], "end": s[-1]["e"], "speaker": EXAMINER_Q} for spk, is_q, s in sents if is_q]
    return {
        **dia, "candidate": candidate, "examiner": examiner,
        "turns": sorted(dia["turns"] + q_turns, key=lambda t: t["start"]),
        "speaker_talk_s": {k: round(v, 1) for k, v in talk.items()},
        "candidate_words": [{**w, "speaker": candidate} for spk, is_q, s in sents if spk == candidate and not is_q for w in s],
        "candidate_questions": cand_q,
        "quality": "merged" if cand_q >= MERGED_QUESTIONS else "ok",
    }


def selftest():
    w = lambda t, s, spk: {"w": t, "s": s, "e": s + 0.5, "speaker": spk}
    words = [w(" Do", 0, "A"), w(" you", 0.5, "B"), w(" work?", 1, "B"),          # examiner question, mislabelled B
             w(" Yes,", 2, "B"), w(" I", 2.5, "B"), w(" do.", 3, "B"),
             w(" Why?", 4, "A"), w(" Because", 5, "B"), w(" I", 5.5, "B"), w(" like", 6, "B"), w(" it.", 6.5, "B"),
             w(" Why?", 7, "B"), w(" It's", 7.5, "B"), w(" fun.", 8, "B")]                  # rhetorical: kept
    out = clean({"test_end": None, "turns": []}, words)
    assert out["candidate"] == "B" and out["examiner"] == "A", out
    assert "".join(x["w"] for x in out["candidate_words"]) == " Yes, I do. Because I like it. Why? It's fun.", out["candidate_words"]
    assert out["candidate_questions"] == 1 and out["quality"] == "ok"
    assert [t["speaker"] for t in out["turns"]] == [EXAMINER_Q, EXAMINER_Q]
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        return selftest()
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from diarize import assign   # same word -> speaker rule as diarize.py (no torch import at module level)
    out_dir = ROOT / "diarization_clean"
    out_dir.mkdir(exist_ok=True)
    counts = {"ok": 0, "merged": 0}
    for path in sorted((ROOT / "diarization").glob("*.json")):
        dia = json.loads(path.read_text(encoding="utf-8"))
        tr = json.loads((ROOT / "transcripts" / path.name).read_text(encoding="utf-8"))
        words = assign([w for s in tr["segments"] for w in s["words"]], [t for t in dia["turns"]])
        res = clean(dia, words)
        (out_dir / path.name).write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        counts[res["quality"]] += 1
        if res["quality"] == "merged":
            print(f"merged {res['id']} candidate_questions={res['candidate_questions']} talk={res['speaker_talk_s']}")
    print(f"cleaned {sum(counts.values())} videos: {counts}")


if __name__ == "__main__":
    main()
