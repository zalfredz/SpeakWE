# IELTS Backend Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Django backend that serves an IELTS Speaking session end to end: picks approved questions, builds the Part 1/2/3 or full-test flow, enforces session state and turn timing, stores one answer recording per turn, records the daily check-in once, and queues an assessment job.

**Architecture:** One Django project in `backend/` with one app, `ielts`. Pure domain logic (flow builder, state machine, check-in rules) lives in plain Python modules with no ORM imports, so it is tested without a database. Models and JSON views are thin layers on top. No login: one local user. Frontend, TTS, transcription and Gemini are later plans; this plan only creates the `AssessmentJob` row they will consume.

**Tech Stack:** Python 3.13, Django 5.2 (plain views + `JsonResponse`, no DRF), SQLite for development, Django's built-in test runner (`unittest` style, same as `tests/` at the repo root).

**Spec:** [docs/superpowers/specs/2026-10-22-ielts-mvp-design.md](../specs/2026-10-22-ielts-mvp-design.md) (§6.1 bank, §6.3 flow, §6.4 recording, §6.5 job queue). Parent: [docs/rancangan-produk.md](../../rancangan-produk.md) §3.3–3.4 (session states, check-in), §11.3 (endpoints).

## Global Constraints

- **Do not run `git commit` or `git push`.** The user commits. Each task ends with a "stop for review" step instead.
- Commands run from `backend/` with the repo venv: `..\.venv\Scripts\python.exe manage.py test ielts -v 2`.
- `backend/requirements.txt` pins `Django>=5.2,<5.3`. No other new dependency.
- `TIME_ZONE = "UTC"`, `USE_TZ = True`. Practice timezone constant: `"Asia/Jakarta"`.
- Only bank items with `status == "approved"` may appear in a session.
- Part 2: preparation 60 s, long turn max 120 s. Part 1 and Part 3: max answer 60 s. Tolerance on durations: 2 s.
- Check-in: one per local date (Asia/Jakarta), only for a `completed` session whose total answered speech is ≥ 60 s.
- Upload: max 10 000 000 bytes; allowed MIME types: `audio/webm`, `audio/ogg`, `audio/mp4`, `audio/mpeg`, `audio/wav`, `audio/x-wav` (parameters such as `;codecs=opus` are ignored when matching).
- Media files go under `backend/media/` (add `backend/media/` and `backend/db.sqlite3` to the root `.gitignore`).
- The assessment version string for jobs created in this plan: `"ielts-eval-v2"`.
- No user-facing scores, no fake data in API responses.

## Review Focus

- Retry after a network blip: the same answer upload or `complete` sent twice must not create a second turn recording, a second check-in, or a second job → Task 6 (`test_answer_upload_is_idempotent`), Task 7 (`test_complete_twice_returns_same_result`).
- Session finished at 23:59 vs 00:01 Jakarta time (16:59 vs 17:01 UTC) must land on different local dates → Task 5 (`test_local_date_crosses_midnight_jakarta`).
- Answer uploaded for a turn the user has not reached, for an instruction step, or longer than the turn's limit must be rejected, not stored → Task 6 (`test_answer_rejected_out_of_order`, `test_answer_rejected_for_instruction_step`, `test_answer_rejected_over_limit`).
- Bank with too few approved items for the chosen mode must give a clear 409 error, not a crash or a session with missing parts → Task 3 (`test_bank_too_small_raises`), Task 6 (`test_create_session_409_when_bank_too_small`).
- Wrong file type or oversized file must be rejected before it is saved → Task 6 (`test_answer_rejected_bad_mime`, `test_answer_rejected_too_large`).

---

## File Structure

```text
backend/
  manage.py
  requirements.txt
  speakwe/            settings.py, urls.py, wsgi.py   (project; SPEAKWE config dict lives in settings)
  ielts/
    models.py         bank models + PracticeSession, Turn, CheckIn, AssessmentJob
    admin.py          bank admin with "approve" action
    bank.py           load_bank() -> Bank (ORM → plain dataclasses, approved only)
    flow.py           pure: Bank dataclasses, Step, build_plan(), INSTRUCTIONS, BankTooSmall
    states.py         pure: session status transition table
    checkins.py       pure: local_date(), current_streak()
    views.py          JSON endpoints
    urls.py
    migrations/
    tests/            test_flow.py, test_states.py, test_checkins.py, test_bank_admin.py, test_api_session.py, test_api_complete.py
```

---

### Task 1: Project scaffold and settings

**Files:**
- Create: `backend/requirements.txt`, `backend/manage.py`, `backend/speakwe/{__init__,settings,urls,wsgi}.py`, `backend/ielts/{__init__,apps}.py`, `backend/ielts/tests/__init__.py`, `backend/ielts/tests/test_settings.py`
- Modify: `.gitignore` (add `backend/media/`, `backend/db.sqlite3`)

**Interfaces:**
- Produces: `settings.SPEAKWE` dict with exactly these keys and values, read by every later task:
  `{"PRACTICE_TZ": "Asia/Jakarta", "PART1_TOPICS": 3, "PART1_QUESTIONS_PER_TOPIC": 4, "PART2_PREP_S": 60, "PART2_TALK_S": 120, "MAX_ANSWER_S": {1: 60, 3: 60}, "ROUNDING_OFF_MAX": 2, "DURATION_TOLERANCE_S": 2, "CHECKIN_MIN_SPEECH_S": 60, "UPLOAD_MAX_BYTES": 10_000_000, "UPLOAD_MIME": ["audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "audio/x-wav"], "ASSESSMENT_VERSION": "ielts-eval-v2"}`

- [ ] **Step 1:** Install Django into the repo venv: `..\.venv\Scripts\python.exe -m pip install "Django>=5.2,<5.3"` and write `backend/requirements.txt` with that one line.
- [ ] **Step 2:** Create the project with `django-admin startproject speakwe .` inside `backend/` and the app with `manage.py startapp ielts`; add `ielts` to `INSTALLED_APPS`, set `TIME_ZONE="UTC"`, `USE_TZ=True`, `MEDIA_ROOT=BASE_DIR/"media"`, and the `SPEAKWE` dict above.
- [ ] **Step 3: Write the failing test** `test_settings.py::test_speakwe_config` asserting `settings.SPEAKWE["PART2_TALK_S"] == 120`, `settings.SPEAKWE["MAX_ANSWER_S"][3] == 60`, `settings.TIME_ZONE == "UTC"`, `settings.USE_TZ is True`. Run it before Step 2's dict exists if you scaffold first; it must fail, then pass.
- [ ] **Step 4:** Run `..\.venv\Scripts\python.exe manage.py test ielts -v 2` → expected: 1 test, OK.
- [ ] **Step 5:** Add the two `.gitignore` lines. Stop for review.

---

### Task 2: Question bank models and admin

**Files:**
- Create: `backend/ielts/models.py` (bank part), `backend/ielts/admin.py`, `backend/ielts/bank.py`, `backend/ielts/tests/test_bank_admin.py`, first migration

**Interfaces:**
- Consumes: nothing.
- Produces (models, all with `created_at`/`updated_at` auto fields):
  - `Status` = `TextChoices`: `DRAFT="draft"`, `APPROVED="approved"`. `Source` = `TextChoices`: `ORIGINAL="original"`, `INSPIRED="inspired_by"`.
  - `Part1Topic(title: CharField(120), status, source, source_ref: CharField(64, blank=True))`; `Part1Question(topic FK related_name="questions", order: PositiveSmallIntegerField, text: TextField)`, ordering `["order"]`.
  - `CueCard(title: TextField  # "Describe a time you helped someone."`, `bullets: JSONField(list[str], 3–4 items)`, `closing: TextField  # "and explain how you felt about it."`, `theme: CharField(80)  # used in the Part 3 intro`, `status, source, source_ref)`; `RoundingOffQuestion(card FK related_name="rounding_off", order, text)`; `Part3Question(card FK related_name="part3", order, text)`.
  - `bank.load_bank() -> flow.Bank` returning only approved topics/cards, children in `order`.
  - Admin: all three parents registered with inlines for their children, `list_filter=("status","source")`, and an action `approve_selected` that sets `status="approved"`.

- [ ] **Step 1: Write failing tests** in `test_bank_admin.py`:
  - `test_load_bank_returns_only_approved`: create 1 approved + 1 draft topic and 1 approved + 1 draft cue card → `load_bank()` has 1 topic and 1 card, with the approved titles.
  - `test_load_bank_keeps_child_order`: questions created with order 2, 1 → `[q.text for q in bank.part1_topics[0].questions]` is in order 1, 2.
  - `test_approve_action_sets_status`: call the admin action on a draft queryset → status `"approved"`.
  - `test_cue_card_requires_3_to_4_bullets`: `CueCard(bullets=["a","b"]).full_clean()` raises `ValidationError`; 3 and 4 bullets pass. Implement as a model `clean()`.
- [ ] **Step 2:** Run → fail (models missing).
- [ ] **Step 3:** Implement the models, `clean()`, admin, `makemigrations ielts`, and `load_bank()` (it builds the `flow` dataclasses from Task 3; define those dataclasses first in `flow.py` if you do this task before Task 3).
- [ ] **Step 4:** Run `manage.py test ielts` → all pass.
- [ ] **Step 5:** Stop for review.

---

### Task 3: Flow builder (pure)

**Files:**
- Create: `backend/ielts/flow.py`, `backend/ielts/tests/test_flow.py`

**Interfaces:**
- Produces:
  - Frozen dataclasses: `Item(id: str, text: str)`; `Topic(id: str, title: str, questions: list[Item])`; `Card(id: str, title: str, bullets: list[str], closing: str, theme: str, rounding_off: list[Item], part3: list[Item])`; `Bank(part1_topics: list[Topic], cue_cards: list[Card])`. Ids are strings like `"p1t:12"`, `"p1q:40"`, `"card:7"`, `"ro:3"`, `"p3q:21"` (prefix + DB pk), so plans stay readable after DB changes.
  - `Step = TypedDict("Step", {"index": int, "part": int, "kind": Literal["instruction","question","prep","long_turn"], "text": str, "item_id": str | None, "max_answer_s": int | None, "prep_s": int | None})`
  - `class BankTooSmall(Exception)`.
  - `MODES = ("part1", "part2", "part3", "full")`.
  - `build_plan(mode: str, bank: Bank, seed: int, cfg: dict) -> list[Step]` where `cfg` is `settings.SPEAKWE`.
  - `INSTRUCTIONS` dict with this exact copy (original wording, spoken by Mimo):
    - `"part1_intro"`: `"Let's begin with Part 1. I'm going to ask you some questions about yourself and familiar topics."`
    - `"part2_intro"`: `"Now let's move on to Part 2. I'm going to give you a topic. You'll have one minute to prepare, and then I'd like you to talk about it for one to two minutes."`
    - `"part2_start"`: `"Your preparation time is over. Please start speaking now."`
    - `"part3_intro"`: `"We've been talking about {theme}. Now I'd like to ask you some more general questions related to this."`
    - `"end"`: `"Thank you. That is the end of the speaking test."`
- Plan shape rules:
  - Part 1 block: `part1_intro`, then `PART1_TOPICS` distinct topics chosen with `random.Random(seed)`, each contributing its first `PART1_QUESTIONS_PER_TOPIC` questions as `question` steps (`max_answer_s = MAX_ANSWER_S[1]`). A topic with fewer questions contributes all of them.
  - Part 2 block: one card chosen with the same RNG; `part2_intro` (instruction), `prep` step (text = card rendered as `title + "\nYou should say:\n" + bullets joined by "\n" + "\n" + closing`, `prep_s = PART2_PREP_S`), `part2_start` (instruction), `long_turn` (same card text, `max_answer_s = PART2_TALK_S`), then up to `ROUNDING_OFF_MAX` rounding-off `question` steps (`max_answer_s = MAX_ANSWER_S[1]`).
  - Part 3 block: `part3_intro` formatted with the card's `theme`, then every Part 3 question of that same card (`max_answer_s = MAX_ANSWER_S[3]`).
  - Modes: `part1` = Part 1 block + `end`; `part2` = Part 2 block + `end`; `part3` = picks a card, Part 3 block + `end`; `full` = Part 1 + Part 2 + Part 3 (Part 3 uses the Part 2 card) + `end`.
  - `index` is 0-based and continuous across the whole plan.
  - Raise `BankTooSmall` when Part 1 needs more topics than exist, a card is needed and none exists, or the chosen card has no Part 3 questions in a mode that needs Part 3 (choose only among cards that have Part 3 questions in those modes).

- [ ] **Step 1: Write failing tests** in `test_flow.py` with an in-memory `Bank` fixture (4 topics × 5 questions, 2 cards with 4 bullets, 2 rounding-off, 5 Part 3 each), `cfg` = the Task 1 dict:
  - `test_full_plan_shape`: kinds in order are `instruction`, 12×`question`, `instruction`, `prep`, `instruction`, `long_turn`, 2×`question`, `instruction`, 5×`question`, `instruction`; `index` runs 0..N-1.
  - `test_full_plan_part3_uses_part2_card`: every Part 3 `item_id` belongs to the card whose id is on the `long_turn` step.
  - `test_part3_intro_mentions_theme`: Part 3 intro text equals `INSTRUCTIONS["part3_intro"].format(theme=card.theme)`.
  - `test_limits_from_cfg`: Part 1 questions have `max_answer_s == 60`, `long_turn` has `120`, `prep` has `prep_s == 60`.
  - `test_same_seed_same_plan` / `test_different_seed_can_differ`: identical for seed 1 twice; for seeds 1..20 at least two distinct topic selections.
  - `test_part_only_modes`: `part1` contains no `long_turn`; `part2` contains no Part 1 questions; `part3` contains only Part 3 questions plus instructions.
  - `test_bank_too_small_raises`: 2 topics with `PART1_TOPICS=3` → `BankTooSmall` for `part1` and `full`; zero cards → `BankTooSmall` for `part2`, `part3`, `full`.
  - `test_unknown_mode_raises_value_error`.
- [ ] **Step 2:** Run → fail.
- [ ] **Step 3:** Implement `build_plan` in `flow.py`.
- [ ] **Step 4:** Run → pass.
- [ ] **Step 5:** Stop for review.

---

### Task 4: Session and turn models, state machine

**Files:**
- Create: `backend/ielts/states.py`, `backend/ielts/tests/test_states.py`
- Modify: `backend/ielts/models.py` (+ migration)

**Interfaces:**
- Produces:
  - `states.TRANSITIONS: dict[str, set[str]]` exactly: `created→{mic_check}`, `mic_check→{active}`, `active→{interrupted, finalizing, abandoned}`, `interrupted→{active, abandoned}`, `finalizing→{completed}`, `completed→{}`, `abandoned→{}`. (`active→abandoned` is the "Akhiri sesi" button; it is a design call, not in the parent diagram.)
  - `states.can_transition(src: str, dst: str) -> bool`; `class InvalidTransition(Exception)`; `states.check(src, dst) -> None` raises it.
  - `PracticeSession(id: UUIDField pk default uuid4, mode: CharField(choices=flow.MODES), status: CharField default "created", seed: IntegerField, plan: JSONField(list[Step]), practice_tz: CharField default "Asia/Jakarta", created_at, started_at: null, completed_at: null)`; method `transition(dst: str) -> None` calls `states.check`, sets `started_at` on first `active`, sets `completed_at` on `completed`, saves.
  - `Turn(session FK related_name="turns", index: PositiveSmallIntegerField, begun_at: DateTimeField null, answered_at: null, audio: FileField(upload_to="answers/%Y/%m/") blank, mime: CharField(64) blank, size_bytes: PositiveIntegerField null, duration_ms: PositiveIntegerField null, sha256: CharField(64) blank)`, `UniqueConstraint(session, index)`. Rows exist only for steps of kind `question`/`long_turn`, created lazily by the begin endpoint.

- [ ] **Step 1: Write failing tests** `test_states.py`: `test_allowed_transitions` (each pair in the table → True), `test_forbidden_examples` (`created→active`, `completed→active`, `abandoned→active`, `finalizing→interrupted` → False), `test_check_raises`; and a DB test `test_transition_sets_timestamps` (created→mic_check→active sets `started_at`; …→finalizing→completed sets `completed_at`).
- [ ] **Step 2:** Run → fail.
- [ ] **Step 3:** Implement `states.py`, the two models, migration.
- [ ] **Step 4:** Run → pass.
- [ ] **Step 5:** Stop for review.

---

### Task 5: Check-in rules (pure) and CheckIn / AssessmentJob models

**Files:**
- Create: `backend/ielts/checkins.py`, `backend/ielts/tests/test_checkins.py`
- Modify: `backend/ielts/models.py` (+ migration)

**Interfaces:**
- Produces:
  - `checkins.local_date(at: datetime, tz_name: str) -> date` (aware UTC datetime in, date in that zone out, via `zoneinfo`).
  - `checkins.current_streak(dates: Iterable[date], today: date) -> int`: number of consecutive days ending at `today`, or ending at `today - 1` if `today` has no check-in yet; 0 otherwise. Calendar days, not 24-hour windows.
  - `CheckIn(local_date: DateField unique, practice_tz: CharField, session: OneToOneField(PracticeSession), created_at)`. `# shortcut: unique on local_date only because there is no login yet; becomes (user, local_date) when accounts arrive.`
  - `AssessmentJob(session FK, version: CharField(32), status: CharField choices queued/processing/ready/partial/failed default "queued", attempts: PositiveSmallIntegerField default 0, error_code: CharField blank, created_at, updated_at)`, `UniqueConstraint(session, version)`.

- [ ] **Step 1: Write failing tests** `test_checkins.py`:
  - `test_local_date_crosses_midnight_jakarta`: `2026-10-22T16:59Z` → `2026-10-22`; `2026-10-22T17:01Z` → `2026-10-23` for `"Asia/Jakarta"`.
  - `test_streak_counts_consecutive_days`: dates 20, 21, 22 Oct, today 22 → 3.
  - `test_streak_allows_today_missing`: dates 20, 21, today 22 → 2.
  - `test_streak_breaks_on_gap`: dates 19, 21, 22, today 22 → 2; dates 19, 20, today 22 → 0.
  - `test_streak_ignores_duplicates_and_order`: [22, 20, 21, 22], today 22 → 3.
- [ ] **Step 2:** Run → fail.
- [ ] **Step 3:** Implement `checkins.py`, the two models, migration.
- [ ] **Step 4:** Run → pass.
- [ ] **Step 5:** Stop for review.

---

### Task 6: Session API — create, read, state, begin turn, upload answer

**Files:**
- Create: `backend/ielts/views.py`, `backend/ielts/urls.py`, `backend/ielts/tests/test_api_session.py`
- Modify: `backend/speakwe/urls.py` (include `ielts.urls` under `api/`)

**Interfaces:**
- Consumes: `load_bank()` (Task 2), `build_plan`, `BankTooSmall`, `MODES` (Task 3), `PracticeSession.transition`, `InvalidTransition`, `Turn` (Task 4).
- Produces (all JSON; errors are `{"error": "<code>", "detail": "<text>"}`; CSRF exempt because there is no login or cookie session — `# shortcut: revisit CSRF when auth arrives`):
  - `POST /api/sessions` body `{"mode": "full"}` → 201 `session_json`; 400 `bad_mode`; 409 `bank_too_small`. Seed from `secrets.randbelow(2**31)`.
  - `GET /api/sessions/<uuid>` → 200 `session_json`; 404 `not_found`.
  - `POST /api/sessions/<uuid>/state` body `{"to": "mic_check"|"active"|"interrupted"|"abandoned"}` → 200 `session_json`; 409 `invalid_transition`. (`finalizing`/`completed` are not accepted here; only `complete` does that.)
  - `POST /api/sessions/<uuid>/turns/<index>/begin` → 200 `{"index", "begun_at"}`. Requires status `active`, step kind `question`/`long_turn` (else 400 `not_an_answer_step`), all earlier answer steps answered (else 409 `out_of_order`). Idempotent: a second call keeps the first `begun_at`.
  - `POST /api/sessions/<uuid>/turns/<index>/answer` multipart: `audio` file, `duration_ms` int → 201 `turn_json` first time, 200 same `turn_json` if already answered (file not replaced). Errors: 409 `not_begun`, 400 `bad_mime`, 413 `too_large`, 400 `over_limit` when `duration_ms > (max_answer_s + DURATION_TOLERANCE_S) * 1000` or `duration_ms > (now - begun_at) + DURATION_TOLERANCE_S*1000`. Store `mime` (without parameters), `size_bytes`, `sha256`, `answered_at`.
  - `session_json = {"id", "mode", "status", "plan": [Step...], "turns": [turn_json...], "created_at", "started_at", "completed_at"}`; `turn_json = {"index", "begun_at", "answered_at", "duration_ms", "mime"}` (no file path or URL in this plan).

- [ ] **Step 1: Write failing tests** `test_api_session.py` (Django test client; `MEDIA_ROOT` overridden to a temp dir; a bank fixture with enough approved items; helper that creates a session and moves it to `active`):
  - `test_create_session_returns_plan`, `test_create_session_bad_mode_400`, `test_create_session_409_when_bank_too_small`, `test_get_session_404`.
  - `test_state_transition_ok_and_invalid` (created→active is 409; created→mic_check→active is 200).
  - `test_begin_is_idempotent`, `test_begin_rejects_instruction_step` (`not_an_answer_step`).
  - `test_answer_upload_stores_metadata` (sha256 of uploaded bytes matches; mime `audio/webm` from `audio/webm;codecs=opus`).
  - `test_answer_upload_is_idempotent` (second upload with different bytes → 200, sha256 unchanged, one file on disk).
  - `test_answer_rejected_out_of_order` (begin on the second question before answering the first → 409).
  - `test_answer_rejected_for_instruction_step`, `test_answer_rejected_not_begun`.
  - `test_answer_rejected_over_limit` (Part 1 question with `duration_ms=63000` → 400; `61000` is accepted when `begun_at` is set 70 s in the past).
  - `test_answer_rejected_bad_mime` (`text/plain`), `test_answer_rejected_too_large` (override `UPLOAD_MAX_BYTES` to 10 and send 11 bytes → 413, nothing stored).
- [ ] **Step 2:** Run → fail.
- [ ] **Step 3:** Implement views and urls.
- [ ] **Step 4:** Run → pass.
- [ ] **Step 5:** Stop for review.

---

### Task 7: Complete session, check-in, assessment job, check-in list

**Files:**
- Create: `backend/ielts/tests/test_api_complete.py`
- Modify: `backend/ielts/views.py`, `backend/ielts/urls.py`

**Interfaces:**
- Consumes: Task 4 models/transitions, Task 5 `local_date`, `current_streak`, `CheckIn`, `AssessmentJob`, `settings.SPEAKWE`.
- Produces:
  - `POST /api/sessions/<uuid>/complete` → 200 `{"session": session_json, "checkin": {"local_date", "created": bool} | null, "assessment": {"version", "status"}}`.
    - Requires every `question`/`long_turn` step answered, else 409 `unanswered_turns` with `detail` listing the missing indexes.
    - In one `transaction.atomic()`: `active→finalizing→completed`; if total `duration_ms` of the session ≥ `CHECKIN_MIN_SPEECH_S*1000`, `get_or_create` a `CheckIn` for `local_date(completed_at, practice_tz)` (a second completed session the same day returns `created: false` and does not change the existing row); `get_or_create` an `AssessmentJob(version=ASSESSMENT_VERSION)`.
    - Already `completed` → 200 with the same body, no new rows. Any other status → 409 `invalid_transition`.
  - `GET /api/checkins` → 200 `{"dates": ["2026-10-22", ...] newest first, "streak": int, "today": "YYYY-MM-DD"}` using `PRACTICE_TZ` for today.

- [ ] **Step 1: Write failing tests** `test_api_complete.py` (helper answers every answer step with small valid uploads and chosen `duration_ms`):
  - `test_complete_requires_all_turns` (409 `unanswered_turns`, status stays `active`).
  - `test_complete_creates_checkin_and_job`.
  - `test_complete_twice_returns_same_result` (one `CheckIn`, one `AssessmentJob`, same JSON).
  - `test_short_session_no_checkin` (total 30 000 ms → `checkin: null`, job still created).
  - `test_second_session_same_day_no_new_checkin` (`created: false`, `CheckIn.objects.count() == 1`).
  - `test_complete_from_abandoned_409`.
  - `test_checkins_endpoint_streak` (create CheckIn rows for yesterday and today in Jakarta time → `streak == 2`, dates newest first).
- [ ] **Step 2:** Run → fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the whole suite: `..\.venv\Scripts\python.exe manage.py test ielts -v 2` → all pass; also run the repo's existing tests `python -m unittest discover -s tests` from the repo root → still 22 OK.
- [ ] **Step 5:** Stop for review.

---

## Not in this plan (next plans)

Seeding the real question bank (B2), TTS audio generation and serving audio URLs (B3), React app (B4), worker + WAV 16 kHz normalisation (spec §6.4) + transcription + Gemini + report endpoints (B5), diarization and ML (A2–A6).
