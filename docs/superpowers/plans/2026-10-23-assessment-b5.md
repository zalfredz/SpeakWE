# Assessment (B5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completed sessions get an evidence-based IELTS estimate: a worker transcribes every answer (faster-whisper), computes fluency features, asks Gemini with the `ielts-eval-v2` prompt, validates the output, computes the overall on the server, stores everything (silver label), and the Result page shows it.

**Architecture:** New package `backend/ielts/assessment/` with pure modules (`features.py`, `scoring.py`, `validate.py`, `request.py`) and thin adapters (`transcribe.py` faster-whisper, `audio.py` ffmpeg → mp3, `gemini.py` HTTPS client). `pipeline.assess(job, transcriber, convert, client)` takes the adapters as arguments so it is tested with fakes. A management command `run_assessments` polls queued jobs. Frontend Result polls `GET /api/sessions/<id>/report`.

**Tech Stack:** Django 5.2, faster-whisper (already in `.venv`), `imageio-ffmpeg` (ffmpeg binary), Gemini REST `v1beta/models/{model}:generateContent` via `urllib` (no SDK), React.

**Spec:** [ielts-mvp-design §6.5–6.6](../specs/2026-10-22-ielts-mvp-design.md) and [gemini-evaluator-prompt (ielts-eval-v2)](../specs/2026-10-22-gemini-evaluator-prompt.md) §1–7.

## Global Constraints

- No `git commit` / `git push`.
- Gemini model from `GEMINI_MODEL` env, default `gemini-3.5-flash-lite`; key from `GEMINI_API_KEY` (env or `backend/.env`, git-ignored). The key is never logged or returned by the API.
- Free tier may use submitted data: dev/test recordings only. Log a one-line warning per job: `Gemini free tier: do not use with real users' recordings`.
- Prompt text comes verbatim from the prompt doc blocks (system, criteria pack, schema); a test fails if the copies drift. Placeholders: official descriptors and anchors → the "not attached / not available yet" lines used in the manual test pack; `MIN_TOTAL_SPEECH_S=60`, `MIN_TURNS=3`.
- Transcript lines: `segment_id=t{turn}-{n} start_ms=.. end_ms=..: "..."`, words with ASR probability < 0.6 marked `[?]`. `start_ms/end_ms` are relative to that turn's audio file.
- Audio to Gemini: each turn converted to mono 16 kHz MP3 (32 kbps), sent inline in turn order, each preceded by a text part `turn t{index}`.
- Overall (server only): full test + four non-null bands; mean with .25 → .5 and .75 → next whole band.
- Validation rules = prompt doc §6 exactly. Invalid → one retry → job `failed` with `error_code`. Session and check-in untouched.
- Insufficient evidence gate before calling Gemini: per Part with answers, total speech < 60 s or < 3 answers (Part 2: < 60 s only) → that whole assessment is `insufficient_evidence` when no Part qualifies; otherwise only qualifying Parts' turns are sent.
- Report JSON stored verbatim with provenance: model, prompt_version `ielts-eval-v2`, criteria_pack_version `speakwe-criteria-v1`, rubric_version `ielts-public-key-distinctions`, calibration `none`, features.
- No scores shown when status ≠ ready/partial. Label "Estimasi latihan SpeakWE, bukan nilai resmi IELTS".
- Out of scope (later): phrase upgrades from the vocabulary/idiom bank (report shows Gemini's spans + grammar fixes only), calibration offset, ML shadow model.

## Review Focus

- Gemini returns a quote that is not in the transcript, or a band without a limitation → rejected and retried, never shown → Task 1.
- Whisper splits a sentence across two segments and Gemini quotes across them → accepted when the quote is inside one segment only; otherwise rejected (prompt asks for one segment) → Task 1.
- A session with only 2 short answers → `insufficient_evidence`, no Gemini call, no bands → Task 5.
- Gemini/network down → job `failed` with `error_code`, Result shows a retry button; re-assess requeues → Tasks 5, 7, 8.
- Worker crashes mid-job → job stuck `processing`; the command resets jobs `processing` for > 15 min back to `queued` → Task 6.

---

### Task 1: scoring + validation (pure)

`scoring.overall(bands: dict, scope: str) -> float | None`; `validate.validate(output: dict, segments: dict[str, dict], scope: str) -> list[str]` (empty = valid; segment dict has `text`, `start_ms`, `end_ms`, `turn_id`). Quote match: lower-case, collapse whitespace, strip `[?]`; segment id accepted with or without a leading `seg `.
Tests: rounding (6,6,6,7→6.5; 6,6,7,7→6.5; 6,7,7,7→7.0; 5,5,5,6→5.5; part-only → None; any null → None); each §6 rule rejects; a valid sample (from the prompt doc §5.2 adapted to ids) passes.

### Task 2: features (pure)

`features.turn_features(words: list[{w,s,e,p}], duration_s) -> dict` and `session_features(list) -> dict`: `speech_s`, `pause_ratio` (gaps ≥ 0.3 s / duration), `mean_length_of_run` (words between pauses ≥ 0.3 s), `speech_rate_wpm`, `fillers_per_min` (um, uh, er, erm, hmm, mm), `repetitions` (same word twice in a row, ignoring fillers), `self_corrections` (word ending in `-`). Tests on a hand-built word list.

### Task 3: prompt files + request builder

`assessment/prompts/ielts-eval-v2/{system.txt,criteria.txt,schema.json}` copied from the doc; `test_prompt_matches_doc` re-extracts the doc blocks and compares. `request.build(session, turns_with_transcripts, features, audio_parts) -> dict` (Gemini `contents` + `systemInstruction` + `generationConfig{responseMimeType: application/json, temperature: 0.2}`). Tests: system text contains criteria + schema; user text has SESSION/TASKS/TRANSCRIPT/FEATURES in that order; `[?]` marking; one inline audio part per turn after its `turn tN` label.

### Task 4: models

`Turn.transcript = JSONField(null)` (segments with words). `Assessment(job OneToOne, status, scope, overall: Decimal(3,1) null, report: JSON, features: JSON, provenance: JSON, error_code, created_at)`. Migration.

### Task 5: pipeline

`pipeline.assess(job, *, transcribe, convert, client) -> None` sets job `processing`, attempts+1; transcribes turns lacking `transcript`; gate; builds request; calls client; validates (retry once); computes overall; saves `Assessment`; job `ready` (or `partial` when Gemini says partial / some Parts were excluded); on exception job `failed` + `error_code` (`gemini_http_<code>`, `invalid_output`, `transcribe_error`, `audio_error`). Tests with fakes: ready path stores overall for full test; part-only → overall null; gate → insufficient_evidence without calling client; invalid twice → failed `invalid_output`; client error → failed; second run on a ready job is a no-op.

### Task 6: adapters + worker command

`transcribe.WhisperTranscriber` (lazy import, `medium.en`, batched 8, word timestamps, filler prompt — same as the dataset pipeline; CUDA DLL dirs added on Windows), `audio.to_mp3(path) -> bytes` via `imageio_ffmpeg.get_ffmpeg_exe()`, `gemini.GeminiClient(key, model).generate(body) -> dict` (POST with `x-goog-api-key`, 120 s timeout, parses `candidates[0].content.parts[0].text` as JSON; non-2xx → `GeminiError(status)`). Settings: tiny `.env` loader, `GEMINI_MODEL`, `GEMINI_API_KEY`. `manage.py run_assessments [--once]`: resets stale `processing` (> 15 min), processes queued oldest-first, sleeps 3 s between polls; missing key → logs and exits 1. Tests: client request shape with patched `urlopen`; stale reset; missing-key exit.

### Task 7: API

`GET /api/sessions/<id>/report` → `{"job": {"status", "error_code"}, "assessment": {status, scope, overall, report, provenance} | null}`; `POST /api/sessions/<id>/assess` → requeue a `failed` job (409 otherwise); `GET /api/sessions/<id>/turns/<index>/audio` → the recording (404 if none). Tests for each, including that the API key never appears in responses.

### Task 8: Result page

Polls `/report` every 3 s while job is queued/processing. Ready/partial: overall (full test only) + four criteria with bands, summary, 1–3 priorities each with first evidence quote + `m:ss` + play button (audio element seeking to `start_ms`), upgrade spans (original → grammar_fix or intended meaning), "Kenapa bukan band lebih tinggi?" per criterion (details element), label + provenance line. insufficient_evidence: explanation. failed: message + "Coba nilai ulang". Pure helpers tested: `formatMs`, `bandsFromReport`.

### Task 9: smoke

Run `run_assessments --once` on the user's real completed Part 1 session: transcription must succeed on GPU; with `GEMINI_API_KEY` set → report ready and visible on Result; without key → command reports the missing key (documented in README).
