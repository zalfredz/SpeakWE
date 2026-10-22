"""Regression tests for pilot status, meaning boundaries and lexical lookup."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "data/language-bank/idioms-v1"
spec = importlib.util.spec_from_file_location("query_idioms", ROOT / "scripts/query-idioms.py")
query = importlib.util.module_from_spec(spec)
spec.loader.exec_module(query)


class IdiomBankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = [json.loads(line) for line in (BANK / "expressions.jsonl").read_text(encoding="utf-8").splitlines()]
        cls.by_phrase = {e["phrase"]: e for e in cls.entries}

    def test_source_checked_count_and_unique_ids(self):
        self.assertEqual(len(self.entries), 68)
        self.assertEqual(len({e["entry_id"] for e in self.entries}), 68)
        self.assertEqual(sum(e["expression_type"] == "idiom" for e in self.entries), 60)
        self.assertTrue(all(e["reference"]["reference_url"].startswith("https://dictionary.cambridge.org/") for e in self.entries))

    def test_no_band_bonus_or_human_approval_inferred(self):
        for entry in self.entries:
            self.assertFalse(entry["scoring"]["automatic_band_bonus"])
            self.assertIsNone(entry["scoring"]["target_ielts_band"])
            self.assertFalse(entry["review"]["human_reviewed"])
            self.assertFalse(entry["review"]["production_approved"])

    def test_levels_are_nullable_and_sense_specific(self):
        self.assertEqual(self.by_phrase["recharge your batteries"]["cefr_level"], "C2")
        self.assertEqual(self.by_phrase["under the weather"]["cefr_level"], "C2")
        self.assertIsNone(self.by_phrase["rain cats and dogs"]["cefr_level"])
        self.assertIsNone(self.by_phrase["lose track of time"]["cefr_level"])
        self.assertEqual(self.by_phrase["lose track of time"]["reference"]["reference_cefr_level"], "B2")

    def test_related_expressions_are_not_counted_as_idioms(self):
        self.assertEqual(self.by_phrase["lend a hand"]["expression_type"], "collocation")
        self.assertEqual(self.by_phrase["a double-edged sword"]["expression_type"], "figurative_noun")
        self.assertEqual(self.by_phrase["down to earth"]["expression_type"], "adjective")
        core = query.search(self.entries, idioms_only=True)
        self.assertEqual(len(core), 60)
        self.assertNotIn("lend a hand", [e["phrase"] for e in core])

    def test_search_does_not_match_warning_mentions_of_other_phrases(self):
        matches = query.search(self.entries, "under the weather")
        self.assertEqual([e["phrase"] for e in matches], ["under the weather"])
        self.assertEqual([e["phrase"] for e in query.search(self.entries, "kurang sehat")], ["under the weather"])
        self.assertEqual(query.search(self.entries, "zzzz-no-such-idiom"), [])

    def test_topic_part_and_starter_filters_work_together(self):
        matches = query.search(self.entries, topic="money", part=3, starter=True)
        self.assertEqual([e["phrase"] for e in matches], ["make ends meet"])

    def test_cli_indonesian_topic_alias_and_invalid_args(self):
        script = str(ROOT / "scripts/query-idioms.py")
        run = subprocess.run([sys.executable, script, "--topic", "uang", "--part", "3", "--idioms-only"], capture_output=True, encoding="utf-8", check=True)
        result = json.loads(run.stdout)
        self.assertEqual(result["query"]["topic"], "money")
        self.assertTrue(result["records"])
        self.assertTrue(all("money" in e["topics"] and 3 in e["ielts_parts"] for e in result["records"]))
        self.assertNotEqual(subprocess.run([sys.executable, script, "--limit", "0"], capture_output=True).returncode, 0)

    def test_generated_artifact_and_curation_hashes(self):
        manifest = json.loads((BANK / "checksums.json").read_text(encoding="utf-8"))
        actual_files = {p.relative_to(BANK).as_posix() for p in BANK.rglob("*") if p.is_file() and p.name != "checksums.json"}
        self.assertEqual(set(manifest), actual_files)
        for name, expected in manifest.items():
            self.assertEqual(hashlib.sha256((BANK / name).read_bytes()).hexdigest(), expected, name)
        for name, expected in json.loads((BANK / "curation-checksums.json").read_text(encoding="utf-8")).items():
            self.assertEqual(hashlib.sha256((BANK.parent / "curation" / name).read_bytes()).hexdigest(), expected, name)


if __name__ == "__main__":
    unittest.main()
