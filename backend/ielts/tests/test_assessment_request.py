import base64
import re
from pathlib import Path
from unittest import TestCase

from ielts.assessment.request import PROMPT_DIR, build, segment_map

DOC = Path(__file__).resolve().parents[3] / "docs" / "superpowers" / "specs" / "2026-10-22-gemini-evaluator-prompt.md"


def turn(idx, part=1, kind="question", text="Where is your hometown?"):
    return {"turn_id": f"t{idx}", "part": part, "kind": kind, "task_text": text, "audio": b"mp3-" + str(idx).encode(),
            "features": {"speech_s": 5.0}, "segments": [
                {"id": f"t{idx}-1", "start_ms": 0, "end_ms": 4200,
                 "words": [{"w": " I", "s": 0.0, "e": 0.2, "p": 0.95}, {"w": " live", "s": 0.2, "e": 0.5, "p": 0.4},
                           {"w": " in", "s": 0.5, "e": 0.6, "p": 0.9}, {"w": " Bandung.", "s": 0.6, "e": 1.2, "p": 0.9}]}]}


class PromptFileTests(TestCase):
    def test_prompt_files_match_the_prompt_doc(self):
        blocks = re.findall(r"```(?:text|json)\n(.*?)```", DOC.read_text(encoding="utf-8"), re.S)
        self.assertEqual((PROMPT_DIR / "system.txt").read_text(encoding="utf-8"), blocks[0])
        self.assertEqual((PROMPT_DIR / "criteria.txt").read_text(encoding="utf-8"), blocks[1])
        self.assertEqual((PROMPT_DIR / "schema.json").read_text(encoding="utf-8"), blocks[4])


class BuildTests(TestCase):
    def setUp(self):
        self.body = build(mode="part1", scope="part1_only", parts=[1], turns=[turn(1), turn(2, text="Do you like it?")],
                          session_features={"speech_s": 10.0})
        self.user_parts = self.body["contents"][0]["parts"]
        self.text = self.user_parts[0]["text"]

    def test_system_instruction_has_prompt_criteria_and_schema_with_placeholders_filled(self):
        system = self.body["systemInstruction"]["parts"][0]["text"]
        self.assertTrue(system.startswith("You are the SpeakWE IELTS Speaking evaluator"))
        self.assertIn("CRITERIA PACK", system)
        self.assertIn('"criteria"', system)
        self.assertNotIn("{{", system)
        self.assertIn("at least 60", system)

    def test_user_text_sections_in_order(self):
        positions = [self.text.index(h) for h in ("SESSION", "TASKS", "TRANSCRIPT", "FEATURES", "AUDIO")]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('mode: part1', self.text)
        self.assertIn('t2 part1 "Do you like it?"', self.text)

    def test_transcript_line_format_and_asr_markers(self):
        self.assertIn('segment_id=t1-1 start_ms=0 end_ms=4200: "I live[?] in Bandung."', self.text)

    def test_one_labelled_audio_part_per_turn_in_order(self):
        rest = self.user_parts[1:]
        self.assertEqual([p.get("text") for p in rest[0::2]], ["turn t1", "turn t2"])
        self.assertEqual(base64.b64decode(rest[1]["inlineData"]["data"]), b"mp3-1")
        self.assertEqual(rest[1]["inlineData"]["mimeType"], "audio/mp3")

    def test_json_output_requested_with_the_schema(self):
        import json
        cfg = self.body["generationConfig"]
        self.assertEqual(cfg["responseMimeType"], "application/json")
        self.assertEqual(cfg["responseJsonSchema"], json.loads((PROMPT_DIR / "schema.json").read_text(encoding="utf-8")))

    def test_segment_map_for_validation(self):
        m = segment_map([turn(1)])
        self.assertEqual(m["t1-1"], {"turn_id": "t1", "start_ms": 0, "end_ms": 4200, "text": "I live[?] in Bandung."})
