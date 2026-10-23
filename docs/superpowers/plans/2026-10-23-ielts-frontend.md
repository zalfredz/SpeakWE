# IELTS Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A React web app that runs an IELTS Speaking practice session end to end against the existing Django API: Home → choose mode → mic check → practice room (Mimo speaks, user answers, 3 s silence ends the answer) → Part 2 prep → complete → result page. Plus a seeded draft question bank.

**Architecture:** Vite + React + TypeScript in `frontend/`. Pure logic (silence detector, session step runner, API client) lives in plain TS modules with Vitest tests. Browser-only pieces (mic, MediaRecorder, Web Audio, speechSynthesis, canvas) are thin wrappers. Mimo is the existing canvas engine, moved to `frontend/src/mimo/` as the single source (demo build scripts point at it). Dev server proxies `/api` to Django on 127.0.0.1:8010.

**Tech Stack:** Vite 5, React 18, TypeScript 5, Vitest, react-router-dom 6. No UI library.

**Spec:** [docs/superpowers/specs/2026-10-22-ielts-mvp-design.md](../specs/2026-10-22-ielts-mvp-design.md) (§6.3 flow + silence rule, §6.4 recording, §6.6 report, §6.7 screens). Visual design: the private SpeakWE IELTS Screens canvas (link shared separately). Backend contract: [2026-10-22-ielts-backend-core.md](2026-10-22-ielts-backend-core.md) Tasks 6–7.

## Global Constraints

- **No `git commit` / `git push`.** Each task ends at a review stop.
- Colors: ground `#FBF8F4`, ink `#1F1B2E`, muted `#5E5873`, lilac `#6B4FC4`, lilac soft `#EFEAFB`, peach soft `#FCE9DD`, line `#E7E2EC`. Font DM Sans. Phone-first, works at 360 px, no horizontal scroll.
- UI copy Indonesian; questions/captions English.
- Practice room shows only Mimo, an icon-only "Akhiri sesi" button, the Part 2 cue card, and a caption only while Mimo speaks.
- Silence: answer ends after **3000 ms** below threshold, counted only after speech started (≥ 300 ms above threshold). **Part 2 long turn never ends on silence.** Every answer also stops at the step's `max_answer_s`. Tapping Mimo ends the current answer.
- Recorder MIME preference: `audio/webm;codecs=opus`, `audio/mp4`, `audio/webm`, chosen with `MediaRecorder.isTypeSupported`. Works in Chrome and Safari.
- Mic and audio playback only start from a user gesture.
- `prefers-reduced-motion` respected (Mimo engine already handles a static frame when the wrapper passes it).
- Mimo voice: `speechSynthesis` (`lang: en-GB`, rate 0.95) behind a `speak(text): Promise<void>` interface. `# shortcut: browser TTS until B3 pre-generated OpenAI audio`.
- No fake scores anywhere. Result page shows session facts and assessment status only.

## Review Focus

- Mic permission denied or no mic → a clear message with Chrome/Safari help, never a stuck spinner → Task 5 (`MicCheck` handles `NotAllowedError`/`NotFoundError`; unit test on `micErrorMessage`).
- User pauses 2.5 s mid-answer (thinking) → answer must continue; only ≥ 3 s ends it → Task 3 (`test: 2.9 s pause does not end`).
- Silence before the user starts speaking → must not end the turn → Task 3 (`test: initial silence never ends`).
- Network error on answer upload → session must not silently skip the answer; retry once, then show an error with retry → Task 6 (`runner` tests `upload_failed`).
- Part 2 long turn with long pauses → never cut by silence; stops at 120 s → Task 3 (`test: silence disabled`) and Task 6.

---

## File Structure

```text
frontend/
  package.json, vite.config.ts, tsconfig.json, index.html
  src/
    main.tsx, App.tsx, styles.css
    api.ts                  typed client for the Django API
    mimo/mimo-fullbody-engine.js   (moved from output/speakwe-mimo-demo/)
    mimo/Mimo.tsx           canvas wrapper: <Mimo state size onTap label/>
    audio/silence.ts        pure silence detector
    audio/mic.ts            getUserMedia, level meter, recorder, mime pick, error messages
    audio/speak.ts          speak(text) via speechSynthesis
    session/runner.ts       pure step runner (state machine over the plan)
    screens/Home.tsx, Choose.tsx, MicCheck.tsx, Room.tsx, Result.tsx
    *.test.ts               Vitest
backend/ielts/management/commands/seed_bank.py
data/question-bank/ielts-v1.json
```

---

### Task 1: Scaffold, proxy, engine move, design tokens

**Files:** create `frontend/` via `npm create vite@5 frontend -- --template react-ts`; add `react-router-dom@6`, `vitest@1`; `vite.config.ts` proxy `{'/api': 'http://127.0.0.1:8010'}`; move `output/speakwe-mimo-demo/mimo-fullbody-engine.js` → `frontend/src/mimo/mimo-fullbody-engine.js` and repoint `build-fullbody.cjs` and `render-fullbody.cjs`; `styles.css` with the tokens above; `.gitignore` adds `frontend/node_modules/`, `frontend/dist/`.

- [ ] Scaffold, install, `npm run build` passes, `npx vitest run` passes with one smoke test.
- [ ] `node output/speakwe-mimo-demo/build-fullbody.cjs` still writes the demo (engine read from the new path).

### Task 2: API client

**Interfaces — Produces** (`src/api.ts`): types `Step`, `Turn`, `Session`, `CompleteResult`, `Checkins` matching backend JSON; `class ApiError extends Error { status: number; code: string }`; functions `createSession(mode)`, `getSession(id)`, `setState(id, to)`, `beginTurn(id, index)`, `uploadAnswer(id, index, blob, durationMs)` (multipart, filename from blob type), `completeSession(id)`, `getCheckins()`. Non-2xx → `ApiError` with backend `error` code.

- [ ] Tests with a stubbed `fetch`: correct URL/method/body; multipart fields `audio`, `duration_ms`; error JSON becomes `ApiError{status, code}`.

### Task 3: Silence detector (pure)

**Produces** (`src/audio/silence.ts`): `createSilenceDetector(opts: {threshold: number; startMs?: 300; silenceMs?: 3000; enabled: boolean}) → { push(level: number, nowMs: number): 'none' | 'speech_started' | 'silence_end' }`. Emits `speech_started` once after `startMs` continuously above threshold; afterwards emits `silence_end` once when below threshold for `silenceMs`. Never emits `silence_end` when `enabled` is false or before speech started.
Also `thresholdFromNoise(noiseRms: number): number = max(0.015, noiseRms * 3)`.

- [ ] Tests: initial silence never ends; 2.9 s pause does not end, 3.0 s does; brief blip < 300 ms is not speech; disabled never ends; `thresholdFromNoise` floor.

### Task 4: Mimo component + speak

**Produces:** `Mimo({state, width, onTap?, label})` — renders `<button>` (if `onTap`) wrapping a 1200×1000 canvas at `width × width*5/6`, runs the engine with rAF, honors reduced motion, cancels on unmount. `speak(text): Promise<void>` resolves on utterance end (or after `text.length*60 ms` fallback if `speechSynthesis` missing), `cancelSpeech()`.

- [ ] Typecheck/build passes (browser-only code; no unit test). Visual check in Task 9.

### Task 5: Home, Choose, MicCheck screens

- Home: Mimo `ready` 300 px; check-in card from `getCheckins()` (today done? streak); primary "Mulai IELTS Speaking" → `/choose`; disabled "Daily Conversation · segera hadir"; bottom nav (Beranda active; Riwayat, Pengaturan disabled "segera").
- Choose: radio cards Full/Part 1/2/3 with durations; "Lanjut ke cek mikrofon" → `/mic?mode=…`.
- MicCheck: button "Izinkan mikrofon" (user gesture) → permission state; live level meter (10 bars); device select (enumerateDevices after permission); 5 s test record + playback; measures noise floor (first 1 s quiet) → threshold saved in sessionStorage-free React state passed via router state; Chrome/Safari help tabs; "Mikrofon oke, mulai tes" creates the session (`createSession`, `setState mic_check`, `setState active`) → `/room/:id`. `micErrorMessage(err)` maps `NotAllowedError`, `NotFoundError`, `NotReadableError`, `SecurityError` (needs HTTPS/localhost) to Indonesian text; unit-tested. `409 bank_too_small` shows "Bank soal belum siap — approve soal di admin".

### Task 6: Session runner + Room + Part 2 prep

**Produces** (`src/session/runner.ts`, pure): `nextAction(plan, answeredIndexes, cursor) → {type: 'speak'|'prep'|'answer'|'complete', step}`; and Room drives it:
- `instruction`/`question`/`long_turn` text: `mimo=speaking`, caption shown, `await speak(text)`, caption hidden.
- `prep`: show cue-card prep view (CueCard design: Mimo `thinking` small, countdown from `prep_s`, card, notes textarea, "Siap, mulai bicara").
- answer steps: `beginTurn` → start recorder → `mimo=listening` → stop on `silence_end` (if not long_turn) or `max_answer_s` or tap Mimo → `mimo=thinking` → `uploadAnswer` (retry once on network/5xx; on failure show error with "Coba kirim lagi") → next.
- After the last step: `completeSession` → `/result/:id` with the response in router state.
- "Akhiri sesi" (icon ✕, confirm dialog) → `setState abandoned` → Home.
- Runner tests: order of actions for a full plan; prep before long_turn; resumes after already-answered indexes; `upload_failed` path keeps the cursor.

### Task 7: Result screen

Shows mode, date, parts completed, total speaking time (sum `duration_ms`), check-in outcome ("Check-in hari ini tercatat" / "Belum memenuhi syarat (min 60 detik bicara)"), assessment status card: `queued` → "Penilaian sedang disiapkan. Penilai otomatis belum aktif di versi ini." No scores. Buttons: "Kembali ke beranda", "Latihan lagi".

### Task 8: Question bank seed

`data/question-bank/ielts-v1.json`: `{"version":1,"part1_topics":[{"title","questions":[4]}×10],"cue_cards":[{"title","bullets":[3],"closing","theme","rounding_off":[2],"part3":[4–5]}×10]}` — original wording. `manage.py seed_bank [--approve]` imports idempotently by title (skips existing), status `draft` unless `--approve`, `source=original`. Tests: imports counts, second run adds nothing, `--approve` sets status.

### Task 9: Smoke run

Run Django (8010) + `npm run dev`; seed with `--approve` into the dev DB; headless Chrome with `--use-fake-ui-for-media-stream --use-fake-device-for-media-stream` screenshots Home, Choose, MicCheck; record results honestly (fake mic has no silence semantics — full session flow verified by runner tests, not end to end).
