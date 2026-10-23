"""Server-side checks on Gemini output (prompt doc ielts-eval-v2 §6). Returns a list of problems; empty = valid."""
import re

from .scoring import CRITERIA

STATUSES = {"ready", "partial", "insufficient_evidence"}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("[?]", "")).strip().lower()


MAX_SKIPPED_WORDS = 3   # Gemini tends to drop a filler or a repeated word ("I- I am" -> "I am") when quoting


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.replace("[?]", "").lower())


def quote_in(quote: str, segment_text: str) -> bool:
    """Every quoted word must appear in the segment, in order, with at most MAX_SKIPPED_WORDS segment words skipped.
    Punctuation and case are ignored, so invented words still fail but cleaned-up disfluencies pass."""
    q, seg = _tokens(quote), _tokens(segment_text)
    if not q:
        return False
    for start in (i for i, t in enumerate(seg) if t == q[0]):
        k, skipped = 1, 0
        for t in seg[start + 1:]:
            if k == len(q):
                break
            if t == q[k]:
                k += 1
            else:
                skipped += 1
                if skipped > MAX_SKIPPED_WORDS:
                    break
        if k == len(q):
            return True
    return False


def fix_priority_order(output: dict) -> None:
    """The server, not the model, enforces 'FC first when FC is the lowest band' (prompt doc §8 v2)."""
    try:
        criteria, priorities = output["criteria"], output["feedback"]["priorities"]
        bands = {k: c.get("band") for k, c in criteria.items() if isinstance(c, dict) and type(c.get("band")) is int}
        if "fc" not in bands or bands["fc"] != min(bands.values()):
            return
        idx = next(i for i, p in enumerate(priorities) if isinstance(p, dict) and p.get("criterion") == "fc")
        priorities.insert(0, priorities.pop(idx))
    except (KeyError, TypeError, AttributeError, StopIteration):
        return


def _seg_id(raw) -> str:
    return str(raw or "").removeprefix("seg ").strip()


def validate(output: dict, segments: dict, scope: str) -> list[str]:
    errors = []
    if not isinstance(output, dict):
        return ["output is not a JSON object"]
    if "overall" in output:
        errors.append("overall must not be sent by the model")
    if output.get("status") not in STATUSES:
        errors.append(f"bad status {output.get('status')!r}")
    if output.get("scope") != scope:
        errors.append(f"scope {output.get('scope')!r} does not match session scope {scope!r}")

    criteria = output.get("criteria")
    if not isinstance(criteria, dict) or set(criteria) != set(CRITERIA) or not all(isinstance(criteria[k], dict) for k in CRITERIA):
        return errors + ["criteria must have exactly fc, lr, gra, p as objects"]

    limitation_owner = {}
    for key in CRITERIA:
        c = criteria[key]
        band = c.get("band")
        if band is not None and (type(band) is not int or not 0 <= band <= 9):
            errors.append(f"{key}: band must be a whole number 0–9 or null, got {band!r}")
            continue
        evidence = c.get("evidence") or []
        if not isinstance(evidence, list) or not all(isinstance(e, dict) for e in evidence):
            errors.append(f"{key}: evidence must be a list of objects")
            continue
        if band is not None:
            if len(evidence) < 2:
                errors.append(f"{key}: needs at least 2 evidence items")
            if band < 9 and not any(e.get("type") == "limitation" for e in evidence):
                errors.append(f"{key}: band below 9 needs a limitation")
        for e in evidence:
            sid = _seg_id(e.get("segment_id"))
            seg = segments.get(sid)
            if seg is None:
                errors.append(f"{key}: unknown segment {sid!r}")
                continue
            if e.get("turn_id") != seg["turn_id"]:
                errors.append(f"{key}: turn_id {e.get('turn_id')!r} does not belong to {sid}")
            if (e.get("start_ms"), e.get("end_ms")) != (seg["start_ms"], seg["end_ms"]):
                errors.append(f"{key}: timestamp of {sid} does not match the segment")
            quote = _norm(str(e.get("quote", "")))
            if not quote_in(quote, seg["text"]):
                errors.append(f"{key}: quote not found in {sid}: {e.get('quote')!r}")
            if e.get("type") == "limitation":
                if key == "p" and not str(e.get("heard_as", "")).strip():
                    errors.append("p: pronunciation limitation needs heard_as")
                owner = limitation_owner.setdefault((sid, quote), key)
                if owner != key:
                    errors.append(f"limitation {quote!r} in {sid} counted in more than one criterion ({owner}, {key})")

    bands = {k: criteria[k].get("band") for k in CRITERIA if type(criteria[k].get("band")) is int}
    feedback = output.get("feedback")
    if not isinstance(feedback, dict):
        return errors + ["feedback must be an object"]
    priorities = feedback.get("priorities") or []
    if not isinstance(priorities, list) or not all(isinstance(p, dict) for p in priorities):
        return errors + ["priorities must be a list of objects"]
    if bands and not 1 <= len(priorities) <= 3:
        errors.append("feedback needs 1 to 3 priorities")
    if "fc" in bands and priorities and bands["fc"] == min(bands.values()) and priorities[0].get("criterion") != "fc":
        errors.append("first priority must be fc when fc is the lowest band")
    for pr in priorities:
        for sid in pr.get("evidence_segment_ids") or []:
            if _seg_id(sid) not in segments:
                errors.append(f"priority: unknown segment {sid!r}")
    return errors
