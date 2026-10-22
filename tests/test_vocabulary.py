"""Regression tests for source provenance, level conflicts, and safe sense mapping."""
import csv
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("vocabulary_builder", ROOT / "scripts/build-vocabulary.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class VocabularyImportTests(unittest.TestCase):
    def fixture(self, directory, a_rows, c_rows):
        for (filename, _), rows in zip(builder.SOURCE_FILES, [a_rows, c_rows]):
            with (directory / filename).open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["headword", "pos", "CEFR", "notes"])
                writer.writeheader()
                writer.writerows(rows)

    def test_source_aliases_do_not_duplicate_a_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            self.fixture(path, [{"headword": "am/AM", "pos": "adverb", "CEFR": "A1"}], [])
            entries, rows, _, _ = builder.parse_profiles(path, {})
            self.assertEqual(len(rows), 1)
            self.assertEqual(len(entries), 1)
            self.assertEqual(len(entries[("am", "adverb")]["claims"]), 1)

    def test_conflicting_sources_do_not_choose_a_level(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            self.fixture(path, [{"headword": "abundance", "pos": "noun", "CEFR": "B1"}],
                [{"headword": "abundance", "pos": "noun", "CEFR": "C2"}])
            entries, rows, _, _ = builder.parse_profiles(path, {})
            entry = entries[("abundance", "noun")]
            self.assertIsNone(entry["cefr_level"])
            self.assertEqual(len(rows), 2)
            self.assertEqual(entry["cefr_levels_claimed"], ["B1", "C2"])
            self.assertIn("conflicting_wordlist_levels", entry["quality_flags"])

    def test_missing_pos_and_suspicious_pos_are_held(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            self.fixture(path, [], [
                {"headword": "batter", "pos": "", "CEFR": "C1"},
                {"headword": "enviable", "pos": "adverb", "CEFR": "C1"}])
            entries, _, _, _ = builder.parse_profiles(path, {("enviable", "adjective"): {"00000100-a"}})
            self.assertTrue(all(e["cefr_level"] is None for e in entries.values()))
            self.assertIsNone(entries[("batter", "")]["pos"])
            self.assertEqual(entries[("enviable", "adverb")]["claims"][0]["source_pos"], "adverb")

    def test_no_cefr_propagation_between_synonyms(self):
        entry = {"entry_id": "test-eat", "cefr_level": "A1", "level_scope": "source_headword_pos_not_verified_sense"}
        concept = {"concept_id": "00000001-v", "pos": "verb", "english_lemmas": ["eat", "unlabelled synonym"]}
        matrix = builder.make_concept_matrix(concept, {("eat", "verb"): entry})
        self.assertEqual([x["word"] for x in matrix["levels"]["A1"]], ["eat"])
        self.assertFalse(matrix["levels"]["A1"][0]["sense_level_verified"])
        self.assertTrue(all(not matrix["levels"][level] for level in builder.LEVELS if level != "A1"))

    def test_source_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / "sample").write_text("changed", encoding="utf-8")
            (path / "sources.lock.json").write_text(json.dumps({"sources": [{"file": "sample", "sha256": "0" * 64}]}))
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                builder.verify_sources(path)


class BuiltDatasetTests(unittest.TestCase):
    def test_database_preserves_source_rows_and_uncertainty(self):
        path = ROOT / "data/vocabulary/v1/vocabulary.sqlite"
        self.assertTrue(path.exists(), "Build vocabulary before running integration tests")
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM claims").fetchone()[0], 9935)
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
            abundance = json.loads(db.execute("SELECT payload FROM entries WHERE word='abundance' AND pos='noun'").fetchone()[0])
            self.assertIsNone(abundance["cefr_level"])
            eat = json.loads(db.execute("SELECT payload FROM entries WHERE word='eat' AND pos='verb'").fetchone()[0])
            self.assertEqual(eat["cefr_level"], "A1")
            self.assertEqual(eat["cambridge_review_status"], "not_checked")
            self.assertFalse(eat["recommendation_approved"])


if __name__ == "__main__":
    unittest.main()
