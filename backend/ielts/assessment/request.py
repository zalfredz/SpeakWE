"""Builds the Gemini generateContent body for one session (prompt doc ielts-eval-v2 §2–3)."""
import base64
import json
from pathlib import Path

PROMPT_VERSION = "ielts-eval-v2"
CRITERIA_PACK_VERSION = "speakwe-criteria-v1"
PROMPT_DIR = Path(__file__).resolve().parent / "prompts" / PROMPT_VERSION
LOW_CONF = 0.6

# Same fill-ins as the manual test pack; descriptors and anchors are not available yet.
FILL = {
    "{{OFFICIAL_DESCRIPTORS}}   <- full public IELTS Speaking band descriptors text": "(Not attached. Use the key distinctions below.)",
    "{{ANCHORS}}": "(Not available yet. Skip step 4 of 'How to assess'.)",
    "{{MIN_TOTAL_SPEECH_S}}": "60",
    "{{MIN_TURNS}}": "3",
}


def system_text() -> str:
    pack = (PROMPT_DIR / "criteria.txt").read_text(encoding="utf-8")
    for placeholder, value in FILL.items():
        pack = pack.replace(placeholder, value)
    return ((PROMPT_DIR / "system.txt").read_text(encoding="utf-8") + "\n" + pack
            + "\n## RESPONSE SCHEMA (return JSON matching this)\n" + (PROMPT_DIR / "schema.json").read_text(encoding="utf-8"))


def segment_text(words: list[dict]) -> str:
    return "".join(w["w"] + ("[?]" if w.get("p", 1) < LOW_CONF else "") for w in words).strip()


def segment_map(turns: list[dict]) -> dict:
    return {s["id"]: {"turn_id": t["turn_id"], "start_ms": s["start_ms"], "end_ms": s["end_ms"], "text": segment_text(s["words"])}
            for t in turns for s in t["segments"]}


def _fmt(features: dict) -> str:
    return ", ".join(f"{k} {v}" for k, v in features.items())


def build(*, mode: str, scope: str, parts: list[int], turns: list[dict], session_features: dict) -> dict:
    """turns: [{turn_id, part, kind, task_text, segments: [{id, start_ms, end_ms, words}], features, audio: mp3 bytes}]"""
    tasks = [f'{t["turn_id"]} part{t["part"]} ' + (f'cue_card: "{t["task_text"]}"' if t["kind"] == "long_turn" else f'"{t["task_text"]}"')
             for t in turns]
    transcript = [f'segment_id={s["id"]} start_ms={s["start_ms"]} end_ms={s["end_ms"]}: "{segment_text(s["words"])}"'
                  for t in turns for s in t["segments"]] or ["(no speech recognised)"]
    text = "\n".join([
        "SESSION", f"mode: {mode}",
        f"scope: {scope} (use exactly \"{scope}\" as the output scope; score only the parts listed)",
        f"parts_completed: {parts}", "",
        "TASKS", *tasks, "",
        "TRANSCRIPT (verbatim ASR per turn; start_ms/end_ms are relative to that turn's audio clip)", *transcript, "",
        "FEATURES", f"session: {_fmt(session_features)}", *[f'{t["turn_id"]}: {_fmt(t["features"])}' for t in turns], "",
        "AUDIO", "(one clip per turn follows, in turn order, each preceded by a text part 'turn tN')",
    ])
    audio_parts = []
    for t in turns:
        audio_parts += [{"text": f'turn {t["turn_id"]}'},
                        {"inlineData": {"mimeType": "audio/mp3", "data": base64.b64encode(t["audio"]).decode()}}]
    return {
        "systemInstruction": {"parts": [{"text": system_text()}]},
        "contents": [{"role": "user", "parts": [{"text": text}, *audio_parts]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2,
                             "responseJsonSchema": json.loads((PROMPT_DIR / "schema.json").read_text(encoding="utf-8"))},
    }
