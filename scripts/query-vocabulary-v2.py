"""Query reviewed sense levels or source-checked Indonesian mappings in v2.

By default, a level query uses reviewed sense records. --wordlist explicitly
requests the larger source wordlist, whose levels do not certify every meaning.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def visible_concept(payload):
    concept = json.loads(payload)
    # Automatic/old translations remain in the archive, not default query output.
    for field in ("indonesian_terms_source_candidates", "definitions_id_source_candidates"):
        concept.pop(field, None)
    return concept


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    query = parser.add_mutually_exclusive_group(required=True)
    query.add_argument("--en")
    query.add_argument("--id")
    query.add_argument("--level", choices=LEVELS)
    parser.add_argument("--pos", choices=("noun", "verb", "adjective", "adverb", "phrase", "preposition", "pronoun", "determiner", "conjunction", "auxiliary verb", "be-verb", "do-verb", "have-verb", "modal auxiliary", "interjection", "number", "infinitive-to"))
    parser.add_argument("--wordlist", action="store_true", help="Use source headword/POS levels, not reviewed sense levels")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--database", type=Path, default=ROOT / "data/vocabulary/v2/vocabulary.sqlite")
    args = parser.parse_args()
    if not 1 <= args.limit <= 100 or args.offset < 0:
        parser.error("limit must be 1..100 and offset must be non-negative")
    if args.wordlist and args.id:
        parser.error("--wordlist supports --en or --level; Indonesian lookup returns reviewed senses and source-Y concepts separately")
    if not args.database.is_file():
        parser.error("v2 database not found; run build-vocabulary-v2.py first")
    db = sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True)
    result = {"dataset_version": "2.0.0", "level_scope": "reviewed_sense" if not args.wordlist else "source_wordlist_headword_pos"}
    conditions, params = [], []
    if args.en:
        conditions.append("word=?")
        params.append(normalize(args.en))
        result["query_en"] = args.en
    elif args.level:
        conditions.append("cefr_level=?")
        params.append(args.level)
        result["level"] = args.level
    if args.pos:
        conditions.append("pos=?")
        params.append(args.pos)
    if args.id:
        result["query_id"] = args.id
        key = normalize(args.id)
        sense_where = "s.sense_id IN (SELECT sense_id FROM sense_indonesian_terms WHERE term=?)"
        sense_params = [key]
        if args.pos:
            sense_where += " AND s.pos=?"
            sense_params.append(args.pos)
        rows = db.execute("SELECT s.payload FROM reviewed_senses s WHERE " + sense_where + " ORDER BY s.cefr_level,s.word LIMIT ? OFFSET ?", (*sense_params, args.limit, args.offset))
        reviewed = [json.loads(row[0]) for row in rows]
        result["reviewed_senses"] = reviewed
        result["levels"] = {level: [s for s in reviewed if s["cefr_level"] == level] for level in LEVELS}
        result["level_slots_scope"] = "This page of reviewed senses; use pagination. Empty does not prove no word exists."
        concept_where, concept_params = "i.term=?", [key]
        if args.pos:
            concept_where += " AND c.pos=?"
            concept_params.append(args.pos)
        result["source_checked_concept_total"] = db.execute("SELECT count(DISTINCT c.concept_id) FROM concepts c JOIN indonesian_terms i USING(concept_id) WHERE " + concept_where, concept_params).fetchone()[0]
        rows = db.execute("SELECT DISTINCT c.payload FROM concepts c JOIN indonesian_terms i USING(concept_id) WHERE " + concept_where + " ORDER BY c.concept_id LIMIT ? OFFSET ?", (*concept_params, args.limit, args.offset))
        result["source_checked_concepts"] = [visible_concept(row[0]) for row in rows]
        result["translation_scope"] = "Only source quality Y; source human check, not a SpeakWE human certification."
    else:
        table = "entries" if args.wordlist else "reviewed_senses"
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        result["total"] = db.execute("SELECT count(*) FROM " + table + where, params).fetchone()[0]
        result["records"] = [json.loads(row[0]) for row in db.execute("SELECT payload FROM " + table + where + " ORDER BY word,pos LIMIT ? OFFSET ?", (*params, args.limit, args.offset))]
        if args.en and not args.wordlist:
            result["source_wordlist_profiles"] = [json.loads(row[0]) for row in db.execute("SELECT payload FROM entries WHERE word=? ORDER BY pos", (normalize(args.en),))]
    result["pagination"] = {"limit": args.limit, "offset": args.offset}
    db.close()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
