"""JSON API for IELTS sessions. No login yet, so no cookie session to protect."""
import hashlib
import json
import secrets

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import FileResponse, HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .assessment.audio import to_mp3
from .bank import load_bank
from .checkins import current_streak, local_date
from .flow import MODES, BankTooSmall, build_plan, time_skipped
from .models import Assessment, AssessmentJob, CheckIn, PracticeSession, Turn
from .states import InvalidTransition

ANSWER_KINDS = ("question", "long_turn")
# Only these may be requested through /state; finalizing/completed go through /complete.
CLIENT_STATES = ("mic_check", "active", "interrupted", "abandoned")


def error(status, code, detail=""):
    return JsonResponse({"error": code, "detail": detail}, status=status)


def iso(dt):
    return dt.isoformat() if dt else None


def turn_json(turn):
    return {"index": turn.index, "begun_at": iso(turn.begun_at), "answered_at": iso(turn.answered_at),
            "duration_ms": turn.duration_ms, "mime": turn.mime}


def session_json(s):
    return {"id": str(s.id), "mode": s.mode, "status": s.status, "plan": s.plan, "training_consent": s.training_consent,
            "turns": [turn_json(t) for t in s.turns.order_by("index")],
            "created_at": iso(s.created_at), "started_at": iso(s.started_at), "completed_at": iso(s.completed_at),
            "part_limits": {str(p): {"limit_s": limit, "min_questions": settings.SPEAKWE["PART_MIN_QUESTIONS"][p]}
                            for p, limit in settings.SPEAKWE["PART_LIMIT_S"].items()}}


def unanswered(s, upto=None):
    """Answer steps before `upto` that still need an answer; questions cut by a part's time limit do not count."""
    turns = {t.index: (t.begun_at, t.answered_at) for t in s.turns.all()}
    skipped = time_skipped(s.plan, turns, settings.SPEAKWE)
    return [st["index"] for st in s.plan[:upto] if st["kind"] in ANSWER_KINDS
            and not turns.get(st["index"], (None, None))[1] and st["index"] not in skipped]


def body(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


def get_session(session_id):
    return PracticeSession.objects.filter(pk=session_id).first()


def answer_step(session, index):
    """Return (step, error_response) for a turn index that must be an answer step."""
    if not 0 <= index < len(session.plan):
        return None, error(404, "not_found", "No such step.")
    step = session.plan[index]
    if step["kind"] not in ANSWER_KINDS:
        return None, error(400, "not_an_answer_step", f"Step {index} is {step['kind']}.")
    return step, None


@csrf_exempt
@require_POST
def create_session(request):
    data = body(request)
    mode = data.get("mode")
    if mode not in MODES:
        return error(400, "bad_mode", f"mode must be one of {', '.join(MODES)}")
    seed = secrets.randbelow(2**31)
    try:
        plan = build_plan(mode, load_bank(), seed, settings.SPEAKWE)
    except BankTooSmall as e:
        return error(409, "bank_too_small", str(e))
    s = PracticeSession.objects.create(mode=mode, seed=seed, plan=plan, practice_tz=settings.SPEAKWE["PRACTICE_TZ"],
                                         training_consent=data.get("training_consent") is True)
    return JsonResponse(session_json(s), status=201)


@require_GET
def session_detail(request, session_id):
    s = get_session(session_id)
    return JsonResponse(session_json(s)) if s else error(404, "not_found")


@csrf_exempt
@require_POST
def session_state(request, session_id):
    s = get_session(session_id)
    if not s:
        return error(404, "not_found")
    dst = body(request).get("to")
    try:
        if dst not in CLIENT_STATES:
            raise InvalidTransition(f"'{dst}' cannot be requested here.")
        s.transition(dst)
    except InvalidTransition as e:
        return error(409, "invalid_transition", str(e))
    return JsonResponse(session_json(s))


@csrf_exempt
@require_POST
def begin_turn(request, session_id, index):
    s = get_session(session_id)
    if not s:
        return error(404, "not_found")
    if s.status != "active":
        return error(409, "not_active", f"Session is {s.status}.")
    step, err = answer_step(s, index)
    if err:
        return err
    missing = unanswered(s, index)
    if missing:
        return error(409, "out_of_order", f"Answer step {missing[0]} first.")
    turn, _ = Turn.objects.get_or_create(session=s, index=index)
    if turn.begun_at is None:
        turn.begun_at = timezone.now()
        turn.save(update_fields=["begun_at"])
    return JsonResponse({"index": index, "begun_at": iso(turn.begun_at)})


@csrf_exempt
@require_POST
def answer_turn(request, session_id, index):
    cfg = settings.SPEAKWE
    s = get_session(session_id)
    if not s:
        return error(404, "not_found")
    step, err = answer_step(s, index)
    if err:
        return err
    turn = s.turns.filter(index=index, begun_at__isnull=False).first()
    if not turn:
        return error(409, "not_begun", "Call begin first.")
    if turn.answered_at:
        return JsonResponse(turn_json(turn))  # retry after a lost response: keep the first recording
    if s.status != "active":
        return error(409, "not_active", f"Session is {s.status}.")
    upload = request.FILES.get("audio")
    if upload is None:
        return error(400, "missing_audio")
    mime = (upload.content_type or "").split(";")[0].strip().lower()
    if mime not in cfg["UPLOAD_MIME"]:
        return error(400, "bad_mime", f"{mime or 'unknown'} is not an accepted audio type.")
    if upload.size > cfg["UPLOAD_MAX_BYTES"]:
        return error(413, "too_large", f"Max {cfg['UPLOAD_MAX_BYTES']} bytes.")
    try:
        duration_ms = int(request.POST["duration_ms"])
    except (KeyError, ValueError):
        return error(400, "bad_duration", "duration_ms must be an integer.")
    tolerance_ms = cfg["DURATION_TOLERANCE_S"] * 1000
    elapsed_ms = (timezone.now() - turn.begun_at).total_seconds() * 1000
    if duration_ms < 0 or duration_ms > step["max_answer_s"] * 1000 + tolerance_ms or duration_ms > elapsed_ms + tolerance_ms:
        return error(400, "over_limit", f"Answer limit is {step['max_answer_s']} s.")
    digest = hashlib.sha256()
    for chunk in upload.chunks():
        digest.update(chunk)
    name = default_storage.save(turn.audio.field.generate_filename(turn, f"{s.id}-{index}.{mime.split('/')[1]}"), upload)
    # Claim the turn atomically: a concurrent upload for the same turn may have won while we were writing.
    claimed = Turn.objects.filter(pk=turn.pk, answered_at__isnull=True).update(
        audio=name, mime=mime, size_bytes=upload.size, duration_ms=duration_ms,
        sha256=digest.hexdigest(), answered_at=timezone.now())
    turn.refresh_from_db()
    if not claimed:
        default_storage.delete(name)
        return JsonResponse(turn_json(turn))
    return JsonResponse(turn_json(turn), status=201)


def checkin_json(s):
    """The check-in this completed session counts toward; created=True only if this session made it."""
    total_ms = sum(t.duration_ms or 0 for t in s.turns.all())
    if total_ms < settings.SPEAKWE["CHECKIN_MIN_SPEECH_S"] * 1000:
        return None
    day = local_date(s.completed_at, s.practice_tz)
    checkin, _ = CheckIn.objects.get_or_create(local_date=day, defaults={"session": s, "practice_tz": s.practice_tz})
    return {"local_date": day.isoformat(), "created": checkin.session_id == s.id}


@csrf_exempt
@require_POST
def complete_session(request, session_id):
    with transaction.atomic():
        s = PracticeSession.objects.select_for_update().filter(pk=session_id).first()
        if not s:
            return error(404, "not_found")
        if s.status != "completed":
            if s.status != "active":
                return error(409, "invalid_transition", f"Cannot complete a {s.status} session.")
            missing = unanswered(s)
            if missing:
                return error(409, "unanswered_turns", "Unanswered steps: " + ", ".join(map(str, missing)))
            s.transition("finalizing")
            s.transition("completed")
        checkin = checkin_json(s)
        job, _ = AssessmentJob.objects.get_or_create(session=s, version=settings.SPEAKWE["ASSESSMENT_VERSION"])
    return JsonResponse({"session": session_json(s), "checkin": checkin,
                         "assessment": {"version": job.version, "status": job.status}})


@require_GET
def checkins(request):
    tz = settings.SPEAKWE["PRACTICE_TZ"]
    today = local_date(timezone.now(), tz)
    dates = list(CheckIn.objects.order_by("-local_date").values_list("local_date", flat=True))
    return JsonResponse({"dates": [d.isoformat() for d in dates], "streak": current_streak(dates, today),
                         "today": today.isoformat()})


def _job(session_id):
    return AssessmentJob.objects.filter(session_id=session_id, version=settings.SPEAKWE["ASSESSMENT_VERSION"]).first()


@require_GET
def session_report(request, session_id):
    job = _job(session_id)
    if not job:
        return error(404, "not_found", "No assessment for this session.")
    a = Assessment.objects.filter(job=job).first()
    return JsonResponse({
        "job": {"status": job.status, "error_code": job.error_code},
        "assessment": a and {"status": a.status, "scope": a.scope, "overall": float(a.overall) if a.overall is not None else None,
                             "report": a.report, "provenance": a.provenance},
    })


@csrf_exempt
@require_POST
def reassess(request, session_id):
    job = _job(session_id)
    if not job:
        return error(404, "not_found")
    if job.status != "failed":
        return error(409, "not_failed", f"Job is {job.status}.")
    job.status, job.error_code = "queued", ""
    job.save(update_fields=["status", "error_code", "updated_at"])
    return JsonResponse({"status": job.status})


@require_GET
def turn_audio(request, session_id, index):
    # shortcut: no ownership check because there is no login yet; must be added with accounts
    turn = Turn.objects.filter(session_id=session_id, index=index, answered_at__isnull=False).first()
    if not turn or not turn.audio:
        return error(404, "not_found")
    # MediaRecorder webm has no seek index, so playing "from the quoted moment" needs a re-encoded mp3
    try:
        return HttpResponse(to_mp3(turn.audio.path), content_type="audio/mpeg")
    except Exception:
        return FileResponse(turn.audio.open("rb"), content_type=turn.mime or "application/octet-stream")
