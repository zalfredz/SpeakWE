import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("vocabulary_v2", ROOT / "scripts/build-vocabulary-v2.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class TranslationQualityTests(unittest.TestCase):
    def test_indonesian_specific_bad_label_overrides_shared_good(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / "wn-msa-all-quality.tab").write_text(
                "00000001-v\tB\tY\tmakan\n"
                "00000001-v\tI\tX\tmakan\n"
                "00000002-v\tB\tY\tminum\n"
                "00000003-v\tB\tO\tberjalan\n"
                "00000004-v\tM\tY\tbahasa-melayu-saja\n", encoding="utf-8")
            concepts = {f"0000000{i}-v": {"indonesian_terms": ["raw candidate"], "definitions_id": ["raw definition"]} for i in range(1, 5)}
            builder.translation_quality(path, concepts)
            self.assertEqual(concepts["00000001-v"]["indonesian_terms"], [])
            self.assertEqual(concepts["00000002-v"]["indonesian_terms"], ["minum"])
            self.assertEqual(concepts["00000003-v"]["indonesian_terms"], [])
            self.assertEqual(concepts["00000004-v"]["indonesian_terms"], [])

    def test_checked_export_does_not_expose_raw_translation_candidates(self):
        result = builder.checked_concept({"concept_id": "test", "indonesian_terms": ["makan"],
            "indonesian_terms_source_candidates": ["incorrect"], "definitions_id_source_candidates": ["unreviewed"]})
        self.assertNotIn("indonesian_terms_source_candidates", result)
        self.assertNotIn("definitions_id_source_candidates", result)
        self.assertEqual(result["indonesian_terms"], ["makan"])


class V2IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "data/vocabulary/v2/vocabulary.sqlite"
        cls.db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_pos_corrections_keep_original_source_claims(self):
        row = self.db.execute("SELECT payload FROM entries WHERE word='remonstrate' AND pos='verb'").fetchone()
        self.assertIsNotNone(row)
        entry = json.loads(row[0])
        self.assertIn("vern", [c["source_pos"] for c in entry["claims"]])
        self.assertTrue(entry["editorial_pos_corrections"])
        self.assertIsNone(self.db.execute("SELECT payload FROM entries WHERE word='enviable' AND pos='adverb'").fetchone())
        self.assertIsNotNone(self.db.execute("SELECT payload FROM entries WHERE word='enviable' AND pos='adjective'").fetchone())

    def test_dictionary_coverage_is_not_a_pos_error(self):
        entry = json.loads(self.db.execute("SELECT payload FROM entries WHERE word='audio' AND pos='adjective'").fetchone()[0])
        self.assertEqual(entry["pos_evidence_status"], "cambridge_POS_observed")
        self.assertEqual(entry["quality_flags"], [])
        self.assertTrue(entry["wordlist_level"])

    def test_makan_default_index_excludes_unrelated_study(self):
        ids = {r[0] for r in self.db.execute("SELECT concept_id FROM indonesian_terms WHERE term='makan'")}
        self.assertNotIn("00599992-v", ids)
        self.assertIn("01168468-v", ids)
        verb_count = self.db.execute("SELECT count(DISTINCT c.concept_id) FROM concepts c JOIN indonesian_terms i USING(concept_id) WHERE i.term='makan' AND c.pos='verb'").fetchone()[0]
        self.assertEqual(verb_count, 3)

    def test_sense_specific_levels_do_not_leak(self):
        rows = [json.loads(row[0]) for row in self.db.execute("SELECT payload FROM reviewed_senses WHERE word='consume'")]
        mapping = {r["sense_key"]: r["cefr_level"] for r in rows}
        self.assertEqual(mapping["food-drink"], "B2")
        self.assertEqual(mapping["use-resources"], "C1")
        calf = [json.loads(row[0]) for row in self.db.execute("SELECT payload FROM reviewed_senses WHERE word='calf'")]
        self.assertEqual({r["sense_key"]: r["cefr_level"] for r in calf}, {"young-animal": "B1", "lower-leg": "C2"})

    def test_raw_sources_and_foreign_keys_preserved(self):
        self.assertEqual(self.db.execute("SELECT count(*) FROM claims").fetchone()[0], 9935)
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(), [])
        audit = [json.loads(line) for line in (ROOT / "data/vocabulary/v2/audit-original-196.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(audit), 196)

    def test_cli_makan_uses_reviewed_levels_without_raw_drafts(self):
        result = subprocess.run(["python", str(ROOT / "scripts/query-vocabulary-v2.py"), "--id", "makan", "--pos", "verb"], capture_output=True, encoding="utf-8", check=True)
        data = json.loads(result.stdout)
        self.assertEqual([s["word"] for s in data["levels"]["A1"]], ["eat"])
        self.assertEqual([s["word"] for s in data["levels"]["B2"]], ["consume"])
        self.assertEqual(data["levels"]["C1"], [])
        self.assertTrue(all("indonesian_terms_source_candidates" not in c for c in data["source_checked_concepts"]))


if __name__ == "__main__":
    unittest.main()
