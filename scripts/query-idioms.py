"""Search the offline IELTS idiom pilot bank by phrase, Indonesian meaning or topic."""
import argparse
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "data/language-bank/idioms-v1"


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().replace("’", "'").split())


def search(entries, query=None, topic=None, part=None, idioms_only=False, starter=False):
    words = normalize(query or "").split()
    matches = []
    for e in entries:
        if topic and topic not in e["topics"]:
            continue
        if part and part not in e["ielts_parts"]:
            continue
        if idioms_only and e["expression_type"] != "idiom":
            continue
        if starter and e["learning_priority"] != "starter":
            continue
        # Search meaning and phrase, not warnings that may mention other expressions.
        haystack = normalize(" ".join([e["phrase"], e["meaning_id"], e["variant"] or "", " ".join(e["topics"])]))
        if all(word in haystack for word in words):
            matches.append(e)
    return sorted(matches, key=lambda e: (e["learning_priority"] != "starter", e["phrase"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--search")
    parser.add_argument("--topic")
    parser.add_argument("--part", type=int, choices=[1, 2, 3])
    parser.add_argument("--idioms-only", action="store_true")
    parser.add_argument("--starter", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()
    if not 1 <= args.limit <= 100 or args.offset < 0:
        parser.error("limit must be 1..100 and offset must be non-negative")
    if not (BANK / "expressions.jsonl").is_file():
        parser.error("Run python scripts/build-idiom-bank.py first")
    topics = json.loads((BANK / "topics.json").read_text(encoding="utf-8"))
    aliases = json.loads((BANK / "search-aliases.json").read_text(encoding="utf-8"))
    topic = aliases.get(normalize(args.topic or ""), args.topic)
    if topic and topic not in topics:
        parser.error("Unknown topic; choose " + ", ".join(topics))
    entries = [json.loads(line) for line in (BANK / "expressions.jsonl").read_text(encoding="utf-8").splitlines()]
    matches = search(entries, args.search, topic, args.part, args.idioms_only, args.starter)
    result = {"dataset_version": "1.0.0", "total": len(matches), "query": {"search": args.search, "topic": topic, "part": args.part}, "scope": "Lexical lookup only; results are optional candidates requiring meaning/context checks, not automatic replacements or score evidence.", "records": matches[args.offset:args.offset + args.limit], "pagination": {"limit": args.limit, "offset": args.offset}}
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
