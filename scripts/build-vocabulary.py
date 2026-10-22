"""Build a provenance-preserving vocabulary dataset from pinned, licensed sources.

Standard-library only. Wordlist CEFR is never promoted to a verified sense label.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import unicodedata
import zipfile
from urllib.parse import quote
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
POS_TO_WN = {"noun": "n", "verb": "v", "adjective": "a", "adverb": "r"}
WN_TO_POS = {v: k for k, v in POS_TO_WN.items()}
SOURCE_FILES = (
    ("cefrj-vocabulary-profile-1.5.csv", "cefrj-wordlist-1-5"),
    ("octanove-vocabulary-profile-c1c2-1.0.csv", "octanove-c1c2-1-0"),
)
VALID_POS = set(POS_TO_WN) | {
    "determiner", "preposition", "conjunction", "pronoun", "be-verb",
    "modal auxiliary", "interjection", "do-verb", "number", "have-verb", "infinitive-to",
}


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def entry_id(word: str, pos: str) -> str:
    return "vocab-" + hashlib.sha256((normalize(word) + "\0" + pos).encode()).hexdigest()[:20]


def json_write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def jsonl_write(path: Path, values) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for value in values:
            stream.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    return count


def verify_sources(source_dir: Path) -> dict:
    manifest = json.loads((source_dir / "sources.lock.json").read_text(encoding="utf-8"))
    for source in manifest["sources"]:
        path = source_dir / source["file"]
        if path.parent.resolve() != source_dir.resolve():
            raise ValueError("Source file must be a direct child of the sources directory")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != source["sha256"]:
            raise ValueError(f"Source checksum mismatch: {source['file']}")
    return manifest


def parse_wordnet(source_dir: Path):
    concepts = {}
    index = defaultdict(set)
    forms = defaultdict(set)
    with zipfile.ZipFile(source_dir / "wordnet.zip") as archive:
        lexnames = {}
        for line in archive.read("wordnet/lexnames").decode().splitlines():
            number, name, _ = line.split()
            lexnames[int(number)] = name
        for filename in ("noun", "verb", "adj", "adv"):
            for line in archive.read("wordnet/data." + filename).decode("utf-8").splitlines():
                if not line[:1].isdigit():
                    continue
                metadata, gloss = line.split("|", 1)
                fields = metadata.split()
                offset, lexfile, raw_pos, count = fields[:4]
                pos = "a" if raw_pos == "s" else raw_pos
                concept_id = offset + "-" + pos
                if concept_id in concepts:
                    raise ValueError("Duplicate WordNet concept: " + concept_id)
                words = []
                for i in range(int(count, 16)):
                    word = re.sub(r"\((?:a|p|ip)\)$", "", fields[4 + 2 * i]).replace("_", " ")
                    words.append(word)
                    key = (normalize(word), WN_TO_POS[pos])
                    index[key].add(concept_id)
                    forms[key].add(word)
                gloss = gloss.strip()
                examples = re.findall(r'(?:^|;\s*)"([^"\n]*)"(?=;|$)', gloss)
                definition = re.split(r';\s*"', gloss, maxsplit=1)[0]
                concepts[concept_id] = {
                    "concept_id": concept_id,
                    "pos": WN_TO_POS[pos],
                    "wordnet_pos": raw_pos,
                    "lexical_domain": lexnames[int(lexfile)],
                    "english_lemmas": sorted(set(words), key=lambda w: (normalize(w), w)),
                    "definition_en": definition,
                    "gloss_en": gloss,
                    "examples_en": examples,
                    "indonesian_terms": [],
                    "definitions_id": [],
                }
    return concepts, index, forms


def attach_indonesian(source_dir: Path, concepts: dict):
    orphan_rows = []
    counts = Counter()
    with (source_dir / "wn-data-ind.tab").open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\r\n").split("\t")
            if len(parts) < 3:
                raise ValueError(f"Malformed Indonesian row {line_number}")
            concept_id, tag = parts[:2]
            counts[tag] += 1
            if concept_id not in concepts:
                orphan_rows.append({"source_line": line_number, "concept_id": concept_id, "tag": tag})
                continue
            if tag == "ind:lemma":
                if len(parts) != 3:
                    raise ValueError(f"Unexpected lemma field count at {line_number}")
                concepts[concept_id]["indonesian_terms"].append(parts[2])
            elif tag == "ind:def":
                concepts[concept_id]["definitions_id"].append(parts[-1])
            else:
                raise ValueError("Unknown Indonesian data tag: " + tag)
    for concept in concepts.values():
        concept["indonesian_terms"] = sorted(set(concept["indonesian_terms"]), key=lambda w: (normalize(w), w))
        concept["definitions_id"] = sorted(set(concept["definitions_id"]))
    return dict(counts), orphan_rows


def parse_profiles(source_dir: Path, wn_index: dict):
    entries = {}
    raw_rows = []
    source_counts = Counter()
    source_level_counts = Counter()
    for filename, source_id in SOURCE_FILES:
        with (source_dir / filename).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            for row_number, row in enumerate(reader, 2):
                if row.get(None) or set(row) - {"headword", "pos", "CEFR", "notes", "CoreInventory 1", "CoreInventory 2", "Threshold"}:
                    raise ValueError(f"Malformed source row {filename}:{row_number}")
                if row["CEFR"] not in LEVELS or not row["headword"].strip():
                    raise ValueError(f"Invalid word/level {filename}:{row_number}")
                source_counts[source_id] += 1
                source_level_counts[row["CEFR"]] += 1
                claim = {
                    "claim_id": f"{source_id}:row-{row_number}",
                    "source_id": source_id,
                    "source_row": row_number,
                    "source_headword": row["headword"],
                    "source_pos": row["pos"],
                    "level": row["CEFR"],
                    "note": row.get("notes", "").strip(),
                    "source_record": row,
                }
                raw_rows.append(claim)
                # Every slash alternative is retained as a source-listed alias.
                # No stemming, inferred inflection, or machine translation is used.
                for alias in dict.fromkeys(row["headword"].split("/")):
                    alias = alias.strip()
                    if not alias:
                        raise ValueError(f"Empty source alias {filename}:{row_number}")
                    key = (normalize(alias), row["pos"].strip())
                    if key not in entries:
                        entries[key] = {
                            "entry_id": entry_id(*key), "word": key[0], "forms": set(),
                            "pos": key[1] or None, "cefr_level": None, "cefr_levels_claimed": [],
                            "level_scope": "source_headword_pos_not_verified_sense",
                            "claims": [], "sense_ids": [], "quality_flags": [],
                            "review_status": "source_import_not_human_reviewed",
                            "recommendation_approved": False,
                            "primary_reference": "cambridge_dictionary",
                            "cambridge_review_status": "not_checked",
                            "cambridge_lookup_url": "https://dictionary.cambridge.org/dictionary/english/" + quote(key[0].replace(" ", "-"), safe="-"),
                            "cambridge_url_status": "generated_lookup_target_not_checked_for_existence",
                        }
                    entries[key]["forms"].add(alias)
                    if not any(c["claim_id"] == claim["claim_id"] for c in entries[key]["claims"]):
                        entries[key]["claims"].append(claim)
    for key, entry in entries.items():
        entry["forms"] = sorted(entry["forms"])
        entry["cefr_levels_claimed"] = [level for level in LEVELS if any(c["level"] == level for c in entry["claims"])]
        flags = entry["quality_flags"]
        if len(entry["cefr_levels_claimed"]) > 1:
            flags.append("conflicting_wordlist_levels")
        if entry["pos"] not in VALID_POS:
            flags.append("missing_or_invalid_source_pos")
        if entry["pos"] in POS_TO_WN:
            entry["sense_ids"] = sorted(wn_index.get(key, set()))
            if not entry["sense_ids"]:
                other_pos = [pos for pos in POS_TO_WN if (key[0], pos) in wn_index]
                if other_pos:
                    flags.append("source_pos_not_found_in_wordnet_other_pos_exists")
        blocking = {"conflicting_wordlist_levels", "missing_or_invalid_source_pos", "source_pos_not_found_in_wordnet_other_pos_exists"}
        if not blocking.intersection(flags):
            entry["cefr_level"] = entry["cefr_levels_claimed"][0]
        if flags:
            entry["review_status"] = "needs_review"
        entry["sense_link_status"] = "lemma_pos_join_only" if entry["sense_ids"] else "no_exact_wordnet_link"
    return entries, raw_rows, dict(source_counts), dict(source_level_counts)


def make_concept_matrix(concept: dict, entries: dict):
    levels = {level: [] for level in LEVELS}
    unresolved = []
    seen = set()
    for word in concept["english_lemmas"]:
        key = (normalize(word), concept["pos"])
        entry = entries.get(key)
        if not entry or entry["entry_id"] in seen:
            continue
        seen.add(entry["entry_id"])
        candidate = {
            "entry_id": entry["entry_id"], "word": word,
            "level_scope": entry["level_scope"],
            "sense_level_verified": False,
        }
        if entry["cefr_level"]:
            levels[entry["cefr_level"]].append(candidate)
        else:
            unresolved.append({**candidate, "levels_claimed": entry["cefr_levels_claimed"], "quality_flags": entry["quality_flags"]})
    if not seen:
        return None
    return {
        **concept,
        "levels": levels,
        "unresolved_level_candidates": unresolved,
        "relation": "same_wordnet_synset_not_universal_substitutes",
        "level_scope": "candidate_headword_pos_levels_not_verified_for_this_sense",
        "translation_status": "source_aligned_not_human_reviewed",
        "recommendation_approved": False,
    }


def create_database(path: Path, entries: dict, raw_rows: list, concepts: dict, wn_index: dict):
    temp = path.with_suffix(".sqlite.building")
    if temp.exists():
        temp.unlink()
    connection = sqlite3.connect(temp)
    connection.executescript("""
      PRAGMA foreign_keys=ON;
      CREATE TABLE entries(entry_id TEXT PRIMARY KEY,word TEXT NOT NULL,pos TEXT,cefr_level TEXT,payload TEXT NOT NULL);
      CREATE INDEX entries_word ON entries(word);
      CREATE INDEX entries_level ON entries(cefr_level);
      CREATE TABLE claims(claim_id TEXT PRIMARY KEY,source_id TEXT,source_row INTEGER,payload TEXT NOT NULL);
      CREATE TABLE entry_claims(entry_id TEXT REFERENCES entries(entry_id),claim_id TEXT REFERENCES claims(claim_id),PRIMARY KEY(entry_id,claim_id));
      CREATE TABLE concepts(concept_id TEXT PRIMARY KEY,pos TEXT,definition_en TEXT,payload TEXT NOT NULL);
      CREATE TABLE entry_senses(entry_id TEXT REFERENCES entries(entry_id),concept_id TEXT REFERENCES concepts(concept_id),PRIMARY KEY(entry_id,concept_id));
      CREATE TABLE english_terms(term TEXT,pos TEXT,concept_id TEXT REFERENCES concepts(concept_id),PRIMARY KEY(term,pos,concept_id));
      CREATE INDEX english_lookup ON english_terms(term);
      CREATE TABLE indonesian_terms(term TEXT,display_term TEXT,concept_id TEXT REFERENCES concepts(concept_id),PRIMARY KEY(term,display_term,concept_id));
      CREATE INDEX indonesian_lookup ON indonesian_terms(term);
    """)
    encode = lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    connection.executemany("INSERT INTO entries VALUES(?,?,?,?,?)", (
        (e["entry_id"], e["word"], e["pos"], e["cefr_level"], encode(e)) for e in entries.values()))
    connection.executemany("INSERT INTO claims VALUES(?,?,?,?)", (
        (r["claim_id"], r["source_id"], r["source_row"], encode(r)) for r in raw_rows))
    connection.executemany("INSERT INTO entry_claims VALUES(?,?)", (
        (e["entry_id"], c["claim_id"]) for e in entries.values() for c in e["claims"]))
    connection.executemany("INSERT INTO concepts VALUES(?,?,?,?)", (
        (c["concept_id"], c["pos"], c["definition_en"], encode(c)) for c in concepts.values()))
    connection.executemany("INSERT INTO entry_senses VALUES(?,?)", (
        (e["entry_id"], concept_id) for e in entries.values() for concept_id in e["sense_ids"]))
    connection.executemany("INSERT INTO english_terms VALUES(?,?,?)", (
        (word, pos, concept_id) for (word, pos), concept_ids in wn_index.items() for concept_id in sorted(concept_ids)))
    connection.executemany("INSERT INTO indonesian_terms VALUES(?,?,?)", (
        (normalize(term), term, c["concept_id"]) for c in concepts.values() for term in c["indonesian_terms"]))
    connection.commit()
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign_keys:
        raise ValueError(f"SQLite integrity failure: {integrity}, {foreign_keys[:3]}")
    connection.close()
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=ROOT / "data/vocabulary/sources")
    parser.add_argument("--output", type=Path, default=ROOT / "data/vocabulary/v1")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source_manifest = verify_sources(args.sources)
    licenses = args.output.parent / "licenses"
    licenses.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.sources / "wordnet.zip") as archive:
        (licenses / "Princeton-WordNet-3.0.txt").write_bytes(archive.read("wordnet/LICENSE"))
        (licenses / "Princeton-WordNet-citation.bib").write_bytes(archive.read("wordnet/citation.bib"))
    (licenses / "Wordnet-Bahasa-MIT.txt").write_bytes((args.sources / "wordnet-bahasa-LICENSE.txt").read_bytes())
    (licenses / "CEFR-J-and-Octanove-terms.md").write_bytes((args.sources / "openlanguageprofiles-README.md").read_bytes())
    concepts, wn_index, forms = parse_wordnet(args.sources)
    ind_counts, orphan_rows = attach_indonesian(args.sources, concepts)
    entries, raw_rows, source_counts, raw_level_counts = parse_profiles(args.sources, wn_index)
    entries = dict(sorted(entries.items()))
    ordered_entries = list(entries.values())
    matrices = [matrix for c in concepts.values() if (matrix := make_concept_matrix(c, entries)) is not None]
    matrices.sort(key=lambda m: m["concept_id"])
    matrix_index = {m["concept_id"]: m for m in matrices}
    ind_index = defaultdict(set)
    for matrix in matrices:
        for term in matrix["indonesian_terms"]:
            ind_index[normalize(term)].add(matrix["concept_id"])

    jsonl_write(args.output / "vocabulary.jsonl", ordered_entries)
    jsonl_write(args.output / "source-claims.jsonl", raw_rows)
    jsonl_write(args.output / "candidates" / "concepts-by-level.jsonl", matrices)
    jsonl_write(args.output / "candidates" / "indonesian-index.jsonl", (
        {"term_id": term, "concept_ids": sorted(ids), "mapping_status": "source_aligned_not_human_reviewed"}
        for term, ids in sorted(ind_index.items())))
    jsonl_write(args.output / "review-queue.jsonl", (e for e in ordered_entries if e["quality_flags"]))
    jsonl_write(args.output / "cambridge-review-queue.jsonl", (
        {"entry_id": e["entry_id"], "word": e["word"], "pos": e["pos"],
         "source_levels": e["cefr_levels_claimed"], "lookup_url": e["cambridge_lookup_url"],
         "lookup_url_status": e["cambridge_url_status"], "status": "not_checked"}
        for e in ordered_entries))
    level_counts = {}
    for level in LEVELS:
        level_counts[level] = jsonl_write(args.output / "by-level" / (level + ".jsonl"),
            (e for e in ordered_entries if e["cefr_level"] == level))

    def inventory():
        for (word, pos), ids in sorted(wn_index.items()):
            e = entries.get((word, pos))
            yield {"word": word, "pos": pos, "forms": sorted(forms[(word, pos)]),
                "cefr_entry_id": e["entry_id"] if e else None,
                "cefr_level": e["cefr_level"] if e else None,
                "sense_ids": sorted(ids), "label_status": "source_wordlist" if e else "cefr_unknown"}
    inventory_count = jsonl_write(args.output / "english-inventory.jsonl", inventory())
    create_database(args.output / "vocabulary.sqlite", entries, raw_rows, concepts, wn_index)

    examples = {}
    for term in ("makan", "minum", "berjalan", "berbicara", "melihat", "bekerja", "belajar", "senang", "sedih", "penting"):
        records = [matrix_index[c] for c in sorted(ind_index.get(term, set()))]
        examples[term] = {"query_id": term, "concepts": records,
            "note_id": "Pisahkan arti menurut concept_id. Level milik headword/POS sumber, bukan level sense yang diverifikasi. Slot kosong berarti sumber belum mendukung padanan pada level itu."}
        json_write(args.output / "candidates" / "examples" / (term + ".json"), examples[term])

    ids = [e["entry_id"] for e in ordered_entries]
    if len(ids) != len(set(ids)):
        raise ValueError("Entry ID collision")
    if sum(source_counts.values()) != len(raw_rows):
        raise ValueError("Lost source rows")
    if len(concepts) != 117659:
        raise ValueError("Unexpected WordNet 3.0 concept count")
    for entry in ordered_entries:
        if entry["cefr_level"] and entry["cefr_level"] not in entry["cefr_levels_claimed"]:
            raise ValueError("Invented CEFR level")
        if "conflicting_wordlist_levels" in entry["quality_flags"] and entry["cefr_level"] is not None:
            raise ValueError("Conflicting level was promoted")
        if any(s not in concepts for s in entry["sense_ids"]):
            raise ValueError("Broken sense link")
    coverage = Counter()
    for e in ordered_entries:
        if e["sense_ids"]:
            coverage["entries_with_english_senses"] += 1
        if any(concepts[s]["indonesian_terms"] for s in e["sense_ids"]):
            coverage["entries_with_indonesian_candidates"] += 1
    flags = Counter(flag for e in ordered_entries for flag in e["quality_flags"])
    summary = {
        "schema_version": 1, "dataset_version": "1.0.0", "built_for": "SpeakWE",
        "source_rows": source_counts, "total_source_rows": len(raw_rows),
        "raw_source_level_counts": raw_level_counts,
        "unique_word_pos_entries_including_listed_variants": len(ordered_entries),
        "distinct_normalized_cefr_headwords": len({e["word"] for e in ordered_entries}),
        "single_uncontested_wordlist_level_counts": level_counts,
        "entries_without_single_usable_level": sum(e["cefr_level"] is None for e in ordered_entries),
        "quality_flag_counts": dict(flags), "coverage": dict(coverage),
        "wordnet_concepts": len(concepts), "wordnet_english_word_pos_inventory": inventory_count,
        "wordnet_distinct_normalized_english_lemmas": len({key[0] for key in wn_index}),
        "concept_matrices_with_cefr_candidates": len(matrices),
        "indonesian_lookup_terms_with_cefr_concepts": len(ind_index),
        "indonesian_source_row_counts": ind_counts,
        "indonesian_orphan_rows": len(orphan_rows),
        "human_reviewed_recommendation_entries": 0,
        "primary_check_reference": "Cambridge Dictionary (user preference)",
        "cambridge_fully_verified_entries": 0,
        "scope": "Broad source-imported vocabulary inventory; not all English and not sense-verified CEFR",
        "license": "CC-BY-SA-4.0 for SpeakWE's combined adaptation; underlying source notices retained",
        "source_lock_sha256": hashlib.sha256((args.sources / "sources.lock.json").read_bytes()).hexdigest(),
        "source_revisions": {x["source_id"]: x["revision"] for x in source_manifest["sources"]},
    }
    checks = {
        "source_hashes_match": True, "all_source_rows_preserved": True,
        "entry_ids_unique": True, "level_values_valid": True,
        "no_invented_cefr_levels": True, "conflicts_not_auto_resolved": True,
        "wordnet_expected_synsets": True, "sqlite_integrity": "ok",
        "sqlite_foreign_keys": "ok", "indonesian_orphan_rows": orphan_rows,
        "limitations": ["Checks validate import/structure, not every source claim or translation.",
            "No human review of the complete vocabulary has taken place.",
            "Source lemma/POS levels must not be treated as verified sense levels."],
    }
    json_write(args.output / "summary.json", summary)
    json_write(args.output / "qa-report.json", checks)
    json_write(args.output / "dataset-metadata.json", {
        "schema_version": 1, "levels": LEVELS,
        "vocabulary_fields": ["entry_id", "word", "forms", "pos", "cefr_level", "cefr_levels_claimed", "level_scope", "claims", "sense_ids", "quality_flags", "review_status", "recommendation_approved", "sense_link_status", "primary_reference", "cambridge_review_status", "cambridge_lookup_url", "cambridge_url_status"],
        "null_semantics": {"cefr_level": "Unresolved conflicting or invalid source data; not A1 or C2 by default", "pos": "Missing in original source"},
        "empty_level_array": "No supported candidate from the selected sources for this concept and level",
        "recommendation_gate": "All imported candidates are unapproved; review sense, translation, register and context before live recommendations.",
    })
    outputs = sorted(p for p in args.output.rglob("*") if p.is_file() and p.name != "checksums.json" and not p.name.endswith(".building"))
    json_write(args.output / "checksums.json", {
        "algorithm": "sha256",
        "files": {p.relative_to(args.output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs},
    })
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
