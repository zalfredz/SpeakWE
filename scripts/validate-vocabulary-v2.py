"""Verify built artifacts and run vocabulary regressions; write a local QA report."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/vocabulary"
VERSION = DATA / "v2"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    counts = {}
    for path in sorted(VERSION.rglob("*.jsonl")):
        count = 0
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                assert isinstance(json.loads(line), dict), path
                count += 1
        counts[path.relative_to(VERSION).as_posix()] = count
    for path in VERSION.rglob("*.json"):
        read(path)
    hashes = read(VERSION / "checksums.json")
    for name, expected in hashes.items():
        assert hashlib.sha256((VERSION / name).read_bytes()).hexdigest() == expected, name
    actual_files = {p.relative_to(VERSION).as_posix() for p in VERSION.rglob("*") if p.is_file() and p.name != "checksums.json"}
    assert actual_files == set(hashes), "Untracked/missing build outputs"
    for source in read(DATA / "sources/sources.lock.json")["sources"]:
        assert hashlib.sha256((DATA / "sources" / source["file"]).read_bytes()).hexdigest() == source["sha256"], source["file"]
    for name, expected in read(VERSION / "curation-checksums.json").items():
        assert hashlib.sha256((DATA / "curation" / name).read_bytes()).hexdigest() == expected, name
    summary = read(VERSION / "summary.json")
    assert counts["lexemes.jsonl"] == summary["lexeme_count"] == 9977
    assert counts["source-claims.jsonl"] == summary["source_rows_preserved"] == 9935
    assert counts["reviewed-senses.jsonl"] == 132
    assert counts["indonesian-level-matrices.jsonl"] == summary["reviewed_indonesian_lookup_groups"]
    assert counts["remaining-level-review.jsonl"] == summary["remaining_multi_level_lexemes"] == 127
    for level, count in summary["reviewed_sense_level_counts"].items():
        assert counts[f"sense-levels/{level}.jsonl"] == count
    checked_pairs = 0
    with (VERSION / "source-checked-translation-senses.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            concept = json.loads(line)
            assert "indonesian_terms_source_candidates" not in concept
            for record in concept["indonesian_term_evidence"]:
                assert record["grade"] == "Y" and record["language"] in ("B", "I")
                checked_pairs += 1
    assert checked_pairs == 12265
    with closing(sqlite3.connect((VERSION / "vocabulary.sqlite").resolve().as_uri() + "?mode=ro", uri=True)) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("SELECT count(*) FROM entries").fetchone()[0] == 9977
        assert db.execute("SELECT count(*) FROM reviewed_senses").fetchone()[0] == 132
        assert db.execute("SELECT count(*) FROM claims").fetchone()[0] == 9935
    cli_cases = [
        ["--id", "makan", "--pos", "verb"], ["--id", "penting"],
        ["--en", "consume"], ["--en", "calf"], ["--level", "A1"],
        ["--wordlist", "--level", "C2"], ["--en", "no_such_word_speakwe"],
    ]
    outputs = []
    for args in cli_cases:
        result = subprocess.run([sys.executable, str(ROOT / "scripts/query-vocabulary-v2.py"), *args], cwd=ROOT, capture_output=True, encoding="utf-8", check=True)
        outputs.append(json.loads(result.stdout))
    assert [s["word"] for s in outputs[0]["levels"]["A1"]] == ["eat"]
    assert [s["word"] for s in outputs[0]["levels"]["B2"]] == ["consume"]
    assert outputs[0]["levels"]["C1"] == []
    assert outputs[0]["source_checked_concept_total"] == 3
    assert outputs[-1]["total"] == 0
    for name in ("makan", "minum", "penting", "berbicara", "belajar", "betis"):
        example = read(VERSION / "examples" / (name + ".json"))
        assert example["query_id"] == name
        assert set(example["levels"]) == {"A1", "A2", "B1", "B2", "C1", "C2"}
    suite = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_vocabulary*.py", "-v"], cwd=ROOT, capture_output=True, encoding="utf-8")
    if suite.returncode:
        print(suite.stdout + suite.stderr)
        raise RuntimeError("Vocabulary tests failed")
    assert "Ran 14 tests" in suite.stderr
    assert "ResourceWarning" not in suite.stderr, suite.stderr
    report = {
        "dataset_version": "2.0.0", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed", "unit_and_integration_tests_passed": 14,
        "test_output": suite.stderr, "jsonl_file_count": len(counts), "jsonl_row_counts": counts,
        "output_hashes_verified": len(hashes), "source_hashes_verified": 9,
        "curation_hashes_verified": len(read(VERSION / "curation-checksums.json")),
        "sqlite_integrity": "ok", "foreign_key_violations": 0,
        "checked_translation_pairs_Y_B_or_I": checked_pairs,
        "cli_smoke_cases_passed": cli_cases,
        "limitations": ["Technical QA and concrete regressions do not establish linguistic accuracy of every source claim.", "132 sense records were checked by an AI editor, not a SpeakWE human reviewer.", "127 multi-level source profiles remain preserved; not silently resolved."]
    }
    (DATA / "v2-validation-run.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("test_output", "jsonl_row_counts")}, indent=2))


if __name__ == "__main__":
    main()
