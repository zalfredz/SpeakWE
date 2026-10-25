"""Assess one completed session (design §6.5). Adapters are injected so the flow is testable without GPU or network."""
import json
import logging
from collections import defaultdict

from django.db import transaction

from ..models import Assessment
from . import calibration
from .errors import AudioError, GeminiError, GeminiOutputError, TranscribeError
from .features import session_features, turn_features
from .request import CRITERIA_PACK_VERSION, PROMPT_VERSION, build, segment_map
from .scoring import CRITERIA, overall
from .validate import fix_priority_order, validate

log = logging.getLogger(__name__)

SCOPE = {"full": "full_test", "part1": "part1_only", "part2": "part2_only", "part3": "part3_only"}
MIN_PART_SPEECH_MS = 60_000
MAX_ATTEMPTS = 3
MIN_PART_ANSWERS = 3          # not applied to Part 2, which is one long turn plus short follow-ups


def _segments(turn_index: int, raw: list[dict]) -> list[dict]:
    return [{"id": f"t{turn_index}-{n}", "start_ms": round(s["start"] * 1000), "end_ms": round(s["end"] * 1000), "words": s["words"]}
            for n, s in enumerate(raw, 1)]


def _qualifying_parts(turns, steps, per_turn) -> tuple[list[int], list[int]]:
    # measured on recognised speech, so silent or empty recordings never count as evidence
    speech, count = defaultdict(int), defaultdict(int)
    for t in turns:
        part = steps[t.index]["part"]
        speech.setdefault(part, 0)
        if per_turn[t.index]["words"]:
            speech[part] += per_turn[t.index]["speech_s"] * 1000
            count[part] += 1
    ok = [p for p in sorted(speech) if speech[p] >= MIN_PART_SPEECH_MS and (p == 2 or count[p] >= MIN_PART_ANSWERS)]
    return ok, [p for p in sorted(speech) if p not in ok]


def assess(job, *, transcribe, convert, client) -> None:
    if job.status in ("ready", "partial") or Assessment.objects.filter(job=job).exists():
        return
    job.status, job.attempts, job.error_code = "processing", job.attempts + 1, ""
    job.save(update_fields=["status", "attempts", "error_code", "updated_at"])
    session = job.session
    steps = {s["index"]: s for s in session.plan}
    scope = SCOPE[session.mode]
    provenance = {"model": getattr(client, "model", None), "prompt_version": PROMPT_VERSION,
                  "criteria_pack_version": CRITERIA_PACK_VERSION, "rubric_version": "ielts-public-key-distinctions",
                  "calibration": "none"}
    try:
        turns = list(session.turns.filter(answered_at__isnull=False).order_by("index"))
        for t in turns:
            if t.transcript is None:
                try:
                    t.transcript = transcribe(t.audio.path)
                except Exception as e:
                    raise TranscribeError(str(e)) from e
                t.save(update_fields=["transcript"])

        per_turn = {t.index: turn_features([w for s in t.transcript for w in s["words"]], (t.duration_ms or 0) / 1000) for t in turns}
        parts, excluded = _qualifying_parts(turns, steps, per_turn)
        used = [t for t in turns if steps[t.index]["part"] in parts and per_turn[t.index]["words"]]
        sess_features = session_features([(per_turn[t.index], (t.duration_ms or 0) / 1000) for t in used])
        features = {"session": sess_features, "turns": {f"t{i}": f for i, f in per_turn.items()}}
        provenance["excluded_parts"] = excluded

        if not used:
            with transaction.atomic():
                Assessment.objects.create(job=job, status="insufficient_evidence", scope=scope, features=features, provenance=provenance)
                job.status = "ready"
                job.save(update_fields=["status", "updated_at"])
            return

        payload = []
        for t in used:
            try:
                audio = convert(t.audio.path)
            except Exception as e:
                raise AudioError(str(e)) from e
            payload.append({"turn_id": f"t{t.index}", "part": steps[t.index]["part"], "kind": steps[t.index]["kind"],
                            "task_text": steps[t.index]["text"], "segments": _segments(t.index, t.transcript),
                            "features": per_turn[t.index], "audio": audio})
        body = build(mode=session.mode, scope=scope, parts=parts, turns=payload, session_features=sess_features)
        segments = segment_map(payload)
        log.warning("Gemini free tier: do not use with real users' recordings (job %s)", job.pk)

        base_contents = body["contents"]
        for attempt in range(MAX_ATTEMPTS):
            try:
                output = client.generate(body)
            except GeminiOutputError as e:
                log.warning("Gemini answer not JSON (attempt %s, job %s): %s", attempt + 1, job.pk, e)
                body["contents"] = base_contents + [{"role": "user", "parts": [{"text": "Your previous answer was not valid JSON. Return only the complete JSON object."}]}]
                continue
            except GeminiError as e:
                if e.status != 400 or "responseJsonSchema" not in body["generationConfig"]:
                    raise
                log.warning("Gemini rejected the response schema; retrying in plain JSON mode (job %s)", job.pk)
                body["generationConfig"].pop("responseJsonSchema")
                provenance["structured_output"] = False
                continue
            fix_priority_order(output)
            errors = validate(output, segments, scope)
            if not errors:
                break
            log.warning("Gemini output rejected (attempt %s, job %s): %s", attempt + 1, job.pk, errors[:5])
            # tell the model exactly what failed; only the latest answer + feedback are kept, so the request does not grow
            body["contents"] = base_contents + [
                {"role": "model", "parts": [{"text": json.dumps(output, ensure_ascii=False)}]},
                {"role": "user", "parts": [{"text": "The SpeakWE validator rejected your answer:\n- " + "\n- ".join(errors[:15])
                                            + "\nFix every problem and return the complete JSON again. Quotes must be copied from ONE segment, "
                                              "keeping fillers and repeated words."}]},
            ]
        else:
            job.status, job.error_code = "failed", "invalid_output"
            job.save(update_fields=["status", "error_code", "updated_at"])
            return

        bands = {k: output["criteria"][k]["band"] for k in CRITERIA}
        shown = None if excluded else overall(bands, scope)
        if shown is not None:
            # Gemini compresses bands toward 6; the learner sees the examiner-calibrated model "a", "b" runs in shadow
            values = calibration.inputs(sess_features, [w for t in used for s in t.transcript for w in s["words"]], bands)
            models = calibration.load()
            features["ml"] = {k: calibration.predict(m, values) for k, m in models.items()} | {"gemini_overall": shown}
            if "a" in models:
                shown = features["ml"]["a"]
                provenance["calibration"] = f"ridge-a-{models['a']['trained']}"
        status = "partial" if excluded and output["status"] == "ready" else output["status"]
        with transaction.atomic():
            Assessment.objects.create(job=job, status=status, scope=scope, report=output, features=features, provenance=provenance,
                                      overall=shown)
            job.status = "partial" if status == "partial" else "ready"
            job.save(update_fields=["status", "updated_at"])
    except Exception as e:   # anything must end in 'failed' so the learner gets a retry, never an endless spinner
        if isinstance(e, TranscribeError):
            code = "transcribe_error"
        elif isinstance(e, AudioError):
            code = "audio_error"
        elif isinstance(e, GeminiError):
            code = f"gemini_http_{e.status}"
        else:
            code = "internal_error"
            log.exception("Assessment job %s crashed", job.pk)
        log.warning("Assessment job %s failed: %s", job.pk, e)
        job.status, job.error_code = "failed", code
        job.save(update_fields=["status", "error_code", "updated_at"])
