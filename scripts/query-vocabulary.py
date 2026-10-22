"""Search the local vocabulary without network/API keys.

An Indonesian match is an unreviewed source candidate, never an approved synonym.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--en", help="Exact English headword, e.g. eat")
    group.add_argument("--id", help="Exact Indonesian source term, e.g. makan")
    group.add_argument("--level", choices=LEVELS, help="Source wordlist level; not sense-verified CEFR")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--database", type=Path, default=ROOT / "data/vocabulary/v1/vocabulary.sqlite")
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 100 or args.offset < 0:
        parser.error("limit must be 1..100; offset must be non-negative")
    if not args.database.is_file():
        parser.error("Database not found. Run build-vocabulary.py first.")
    db = sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True)
    data = {"note_id": "Level dari wordlist sumber, belum verifikasi level per arti Cambridge. Terjemahan otomatis dari sumber dapat salah; bukan rekomendasi siap pakai."}
    if args.en:
        key = normalize(args.en)
        data["query_en"] = key
        data["entries"] = [json.loads(row[0]) for row in db.execute(
            "SELECT payload FROM entries WHERE word=? ORDER BY pos", (key,))]
        data["total_senses"] = db.execute("SELECT count(DISTINCT concept_id) FROM english_terms WHERE term=?", (key,)).fetchone()[0]
        rows = db.execute("SELECT c.payload FROM concepts c JOIN english_terms e USING(concept_id) WHERE e.term=? ORDER BY c.concept_id LIMIT ? OFFSET ?", (key, args.limit, args.offset))
        data["senses"] = [json.loads(row[0]) for row in rows]
        data["sense_translation_status"] = "source_candidates_not_reviewed"
    elif args.id:
        key = normalize(args.id)
        data["query_id"] = key
        data["status"] = "unreviewed_translation_candidates"
        data["total_source_concepts"] = db.execute("SELECT count(DISTINCT concept_id) FROM indonesian_terms WHERE term=?", (key,)).fetchone()[0]
        rows = db.execute("SELECT DISTINCT c.payload FROM concepts c JOIN indonesian_terms i USING(concept_id) WHERE i.term=? ORDER BY c.concept_id LIMIT ? OFFSET ?", (key, args.limit, args.offset))
        results = []
        for row in rows:
            concept = json.loads(row[0])
            groups = {level: [] for level in LEVELS}
            unresolved = []
            for word in concept["english_lemmas"]:
                result = db.execute("SELECT payload FROM entries WHERE word=? AND pos=?", (normalize(word), concept["pos"])).fetchone()
                if result:
                    entry = json.loads(result[0])
                    candidate = {"word": word, "entry_id": entry["entry_id"], "sense_level_verified": False}
                    if entry["cefr_level"]:
                        groups[entry["cefr_level"]].append(candidate)
                    else:
                        unresolved.append({**candidate, "levels_claimed": entry["cefr_levels_claimed"]})
            results.append({**concept, "levels": groups, "unresolved_candidates": unresolved})
        data["source_concepts"] = results
    else:
        data["wordlist_level"] = args.level
        data["total_entries"] = db.execute("SELECT count(*) FROM entries WHERE cefr_level=?", (args.level,)).fetchone()[0]
        data["entries"] = [json.loads(row[0]) for row in db.execute(
            "SELECT payload FROM entries WHERE cefr_level=? ORDER BY word,pos LIMIT ? OFFSET ?", (args.level, args.limit, args.offset))]
    data["pagination"] = {"limit": args.limit, "offset": args.offset}
    db.close()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
