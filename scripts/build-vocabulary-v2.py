"""Apply evidence-backed editorial corrections and preserve translation quality.

v1 stays available for audit. Cambridge facts are per sense, never copied to every
meaning of a headword. Source quality Y is distinct from a SpeakWE human review.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("vocabulary_v1", ROOT / "scripts/build-vocabulary.py")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
CURATION = ROOT / "data/vocabulary/curation"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def apply_pos_corrections(entries, wn_index, editorial):
    entries = deepcopy(entries)
    changes = []
    for edit in editorial["pos_corrections"]:
        old_key = (base.normalize(edit["word"]), edit["source_pos"] or "")
        if old_key not in entries:
            raise ValueError("Editorial POS correction does not match source: " + str(old_key))
        old = entries.pop(old_key)
        new_key = (old_key[0], edit["corrected_pos"])
        new_id = base.entry_id(*new_key)
        change = {**edit, "old_entry_id": old["entry_id"], "new_entry_id": new_id,
                  "claim_ids": [c["claim_id"] for c in old["claims"]], "reviewer_type": "AI_editor"}
        changes.append(change)
        if new_key in entries:
            target = entries[new_key]
            target["forms"] = sorted(set(target["forms"]) | set(old["forms"]))
            known = {c["claim_id"] for c in target["claims"]}
            target["claims"].extend(c for c in old["claims"] if c["claim_id"] not in known)
        else:
            target = old
            target["entry_id"], target["pos"] = new_id, edit["corrected_pos"]
            entries[new_key] = target
        target.setdefault("editorial_pos_corrections", []).append(change)
        target["sense_ids"] = sorted(wn_index.get(new_key, set()))
    for key, entry in entries.items():
        entry["quality_flags"] = []
        entry["coverage_notes"] = []
        levels = [level for level in base.LEVELS if any(c["level"] == level for c in entry["claims"])]
        entry["cefr_levels_claimed"] = levels
        entry["cefr_level"] = levels[0] if len(levels) == 1 else None
        if len(levels) > 1:
            entry["quality_flags"].append("multiple_source_level_profiles_require_sense_selection")
        if entry["pos"] not in base.VALID_POS:
            entry["quality_flags"].append("invalid_pos")
            entry["cefr_level"] = None
        if entry["pos"] in base.POS_TO_WN and not entry["sense_ids"]:
            # Dictionary coverage is not a grammatical validity test.
            entry["coverage_notes"].append("no_exact_wordnet_lemma_pos_link")
        entry["wordlist_level"] = entry["cefr_level"]
        entry["wordlist_level_scope"] = "source_headword_pos_only"
        entry["review_status"] = "source_profile_preserved_not_sense_approved"
        entry["recommendation_approved"] = False
    return dict(sorted(entries.items())), changes


def translation_quality(source_dir, concepts):
    shared_checked = {}
    ind_specific = {}
    counts = Counter()
    path = source_dir / "wn-msa-all-quality.tab"
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) != 4 or fields[1] not in ("B", "I"):
                continue
            concept_id, language, grade, term = fields
            if grade not in ("Y", "O", "M", "L", "X"):
                raise ValueError(f"Unknown source quality at line {number}: {grade}")
            record = {"grade": grade, "source_line": number, "language": language}
            if language == "I":
                ind_specific[(concept_id, term)] = record
            elif grade == "Y":
                shared_checked[(concept_id, term)] = record
            counts[language + "/" + grade] += 1
    accepted = defaultdict(list)
    declined = Counter()
    selected = dict(shared_checked)
    # An explicit Indonesian annotation overrides the shared-language annotation.
    selected.update(ind_specific)
    for (concept_id, term), record in selected.items():
        if concept_id not in concepts:
            declined["unknown_concept"] += 1
            continue
        if record["grade"] == "Y":
            accepted[concept_id].append({"term": term, **record,
                "source_id": "wordnet-bahasa-quality", "quality_meaning": "source_hand_checked_good"})
        else:
            declined[record["grade"]] += 1
    for concept_id, concept in concepts.items():
        concept["indonesian_terms_source_candidates"] = concept["indonesian_terms"]
        concept["definitions_id_source_candidates"] = concept.pop("definitions_id")
        records = sorted(accepted.get(concept_id, []), key=lambda r: (base.normalize(r["term"]), r["term"]))
        concept["indonesian_term_evidence"] = records
        concept["indonesian_terms"] = sorted({r["term"] for r in records})
        concept["indonesian_translation_status"] = "source_quality_Y_only" if records else "no_source_quality_Y_translation"
        concept["definitions_id"] = []
    return {"source_quality_row_counts": dict(counts), "excluded_selected_override_pairs": dict(declined),
            "source_Y_concepts": len(accepted), "source_Y_pairs": sum(len(v) for v in accepted.values())}


def checked_concept(concept):
    return {key: value for key, value in concept.items()
        if key not in ("indonesian_terms_source_candidates", "definitions_id_source_candidates")}


ALIASES = {
    "food": ["makan", "menyantap"], "food-drink": ["makan", "minum", "mengonsumsi"],
    "use-resources": ["menggunakan", "menghabiskan", "sumber daya"],
    "young-animal": ["anak sapi"], "lower-leg": ["betis"],
    "actors": ["pemeran", "aktor"], "choose-actors": ["memilih pemeran"],
    "electrical-device": ["baterai"], "business-representative": ["agen", "biro"],
    "government-organization": ["lembaga pemerintah"], "calendar-month": ["Maret", "bulan Maret"],
    "aircraft": ["pesawat", "pesawat terbang"], "wealthy": ["kaya"],
    "student": ["murid", "siswa"], "natural-world": ["alam"],
    "operate-vehicle": ["mengemudi", "menyetir"], "slow-run": ["joging", "berlari perlahan"],
    "cannot-manage-without": ["penting", "sangat penting"], "urgent-essential": ["penting", "mendesak"],
    "memory-event": ["ingatan", "kenangan"], "ability-to-remember": ["daya ingat"],
    "unnecessary": ["berlebihan", "tidak diperlukan"], "lost-job": ["PHK", "kehilangan pekerjaan"],
    "indefinite-singular": ["sebuah", "seorang"], "before-vowel-sound": ["sebuah", "seorang"],
    "particular-reference": ["penentu tertentu"], "addition": ["dan"], "reason": ["karena"],
    "move-on-foot": ["berjalan", "berjalan kaki"], "beverage": ["minuman"],
    "take-liquid": ["minum"], "alcohol": ["minum alkohol"],
    "say-words": ["bicara", "berbicara"], "utterance": ["bicara", "berbicara"],
    "language-ability": ["berbahasa"], "gain-knowledge-skill": ["belajar"],
    "learn-subject": ["belajar", "mempelajari"], "job-activity": ["pekerjaan", "kerja"],
    "workplace": ["tempat kerja", "kantor"], "produced-material": ["hasil kerja"],
    "pleased": ["senang", "bahagia"], "unhappy": ["sedih"],
    "necessary-valuable": ["penting"], "influential": ["penting", "berpengaruh"],
    "satisfactory-enjoyable": ["baik", "bagus"], "unpleasant-problematic": ["buruk", "jelek"],
    "opinion-belief": ["berpikir", "berpendapat"], "consider-decision": ["mempertimbangkan"],
    "have-information": ["tahu", "mengetahui"], "be-certain": ["yakin"],
    "wish-for": ["ingin", "mau"], "necessity": ["butuh", "perlu", "membutuhkan"],
    "beneficial-recommendation": ["butuh", "perlu"], "make-easier": ["membantu", "menolong"],
    "produce-create": ["membuat"], "force": ["memaksa"], "perform-action": ["melakukan"],
    "put-to-purpose": ["menggunakan", "memakai"], "comprehend-meaning": ["mengerti", "memahami"],
    "know-how-why": ["memahami"], "empathize": ["memahami perasaan"],
    "make-clear": ["menjelaskan"], "get-better": ["meningkatkan", "membaik"],
    "same-opinion": ["setuju"], "different-opinion": ["tidak setuju"],
}


def reviewed_senses(entries, checks):
    curation = read_json(CURATION / "reviewed-senses.json")
    lookup = {r["word"]: r for r in checks["levels"]}
    core_checks = read_json(CURATION / "cambridge-core-checks-2026-10-22.json")
    lookup.update({r["word"]: r for r in core_checks["core_vocabulary"]})
    lookup.update({r["word"]: r for r in core_checks["extra_targeted_lookups"]})
    result = []
    for values in curation["rows"]:
        if len(values) != len(curation["columns"]):
            raise ValueError("Invalid curated sense column count")
        row = dict(zip(curation["columns"], values))
        if row["cefr_level"] not in base.LEVELS:
            raise ValueError("Invalid curated CEFR")
        word = row["word"]
        url = lookup.get(base.normalize(word), {}).get("url")
        if word == "in retrospect":
            url = "https://dictionary.cambridge.org/dictionary/english/retrospect"
        if word == "talks":
            url = "https://dictionary.cambridge.org/dictionary/english/talk"
        if not url:
            url = "https://dictionary.cambridge.org/dictionary/english/" + base.quote(base.normalize(word).replace(" ", "-"), safe="-")
        row.update({
            "sense_id": "cambridge-" + base.entry_id(word, row["pos"])[6:] + "-" + row["sense_key"],
            "reference_url": url, "primary_reference": "Cambridge Dictionary",
            "reference_check_scope": "CEFR_POS_and_specific_meaning_in_indexed_excerpt",
            "checked_on": curation["reviewed_on"], "reviewer_type": "AI_editor",
            "text_origin": "SpeakWE_original_paraphrase_and_example",
            "register_status": "editorial_guidance", "case_sensitive": word == "March",
            "indonesian_lookup_terms": ALIASES.get(row["sense_key"], []),
            "pilot_ready": True, "production_approved": False,
        })
        if row["register"] == "UK":
            row["register"], row["region"] = "general", "UK"
        key = (base.normalize(word), "do-verb" if row["pos"] == "auxiliary verb" and word == "do" else row["pos"])
        row["wordlist_entry_id"] = entries[key]["entry_id"] if key in entries else None
        result.append(row)
    if len({r["sense_id"] for r in result}) != len(result):
        raise ValueError("Duplicate curated sense IDs")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=ROOT / "data/vocabulary/sources")
    parser.add_argument("--output", type=Path, default=ROOT / "data/vocabulary/v2")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source_lock = base.verify_sources(args.sources)
    concepts, wn_index, forms = base.parse_wordnet(args.sources)
    base.attach_indonesian(args.sources, concepts)
    originals, raw_rows, source_counts, raw_levels = base.parse_profiles(args.sources, wn_index)
    entries, changes = apply_pos_corrections(originals, wn_index, read_json(CURATION / "editorial-corrections.json"))
    quality_report = translation_quality(args.sources, concepts)
    checks = read_json(CURATION / "cambridge-checks-2026-10-22.json")
    core_checks = read_json(CURATION / "cambridge-core-checks-2026-10-22.json")
    indexed_checks = defaultdict(list)
    for kind, rows in (("level", checks["levels"]), ("pos", checks["parts_of_speech"])):
        for check in rows:
            indexed_checks[check["word"]].append({"kind": kind, **check})
    for kind, rows in (("core_vocabulary", core_checks["core_vocabulary"]), ("targeted_fact", core_checks["extra_targeted_lookups"])):
        for check in rows:
            indexed_checks[check["word"]].append({"kind": kind, **check})
    senses = reviewed_senses(entries, checks)
    sense_by_entry = defaultdict(list)
    for sense in senses:
        if sense["wordlist_entry_id"]:
            sense_by_entry[sense["wordlist_entry_id"]].append(sense["sense_id"])
    cleared_pos = []
    for key, entry in entries.items():
        observations = indexed_checks.get(key[0], [])
        positive_pos = any(entry["pos"] in c.get("pos_visible", []) for c in observations)
        entry["cambridge_reference_checks"] = observations
        entry["reviewed_sense_ids"] = sense_by_entry.get(entry["entry_id"], [])
        entry["cambridge_review_status"] = "specific_senses_checked" if entry["reviewed_sense_ids"] else (
            "indexed_metadata_checked" if observations else "not_checked")
        entry["source_Y_indonesian_sense_count"] = sum(bool(concepts[s]["indonesian_terms"]) for s in entry["sense_ids"])
        if positive_pos and "no_exact_wordnet_lemma_pos_link" in entry["coverage_notes"]:
            cleared_pos.append({"word": entry["word"], "pos": entry["pos"],
                "reason": "Cambridge positive POS evidence; WordNet coverage gap is not a source error"})
        entry["pos_evidence_status"] = "cambridge_POS_observed" if positive_pos else (
            "editorially_corrected" if entry.get("editorial_pos_corrections") else "source_POS_preserved")

    base.jsonl_write(args.output / "lexemes.jsonl", entries.values())
    base.jsonl_write(args.output / "reviewed-senses.jsonl", senses)
    base.jsonl_write(args.output / "source-claims.jsonl", raw_rows)
    base.jsonl_write(args.output / "pos-corrections.jsonl", changes)
    base.jsonl_write(args.output / "source-checked-translation-senses.jsonl", (
        checked_concept(c) for c in concepts.values() if c["indonesian_terms"]))
    # Broad automatic translations are retained separately and never indexed by default.
    base.jsonl_write(args.output / "drafts" / "source-translation-candidates.jsonl", (
        {"concept_id": c["concept_id"], "terms": c["indonesian_terms_source_candidates"],
         "definitions_id": c["definitions_id_source_candidates"], "status": "not_reviewed_not_default_lookup"}
        for c in concepts.values() if c["indonesian_terms_source_candidates"]))
    for level in base.LEVELS:
        base.jsonl_write(args.output / "sense-levels" / (level + ".jsonl"), (s for s in senses if s["cefr_level"] == level))
        base.jsonl_write(args.output / "wordlist-levels" / (level + ".jsonl"), (e for e in entries.values() if e["wordlist_level"] == level))
    aliases = defaultdict(list)
    for sense in senses:
        for term in sense["indonesian_lookup_terms"]:
            aliases[base.normalize(term)].append(sense)
    ind_matrices = [
        {"query_id": term,
         "levels": {level: [s for s in matching if s["cefr_level"] == level] for level in base.LEVELS},
         "relation": "shared_Indonesian_lookup_term_preserve_individual_senses",
         "empty_slot": "No reviewed candidate in this version; not proof that none exists",
         "production_approved": False}
        for term, matching in sorted(aliases.items())]
    base.jsonl_write(args.output / "indonesian-level-matrices.jsonl", ind_matrices)
    for matrix in ind_matrices:
        if matrix["query_id"] in ("makan", "minum", "penting", "berbicara", "belajar", "betis"):
            base.json_write(args.output / "examples" / (matrix["query_id"] + ".json"), matrix)
    base.jsonl_write(args.output / "remaining-level-review.jsonl", (
        e for e in entries.values() if e["quality_flags"]))
    matrices = []
    for c in concepts.values():
        matrix = base.make_concept_matrix(checked_concept(c), entries)
        if matrix and c["indonesian_terms"]:
            matrix["translation_status"] = "source_quality_Y_only_not_a_SpeakWE_human_review"
            matrix["level_scope"] = "source_wordlist_candidate_levels_not_verified_for_every_sense"
            matrices.append(matrix)
    base.jsonl_write(args.output / "source-checked-concept-matrices.jsonl", matrices)

    dbpath = args.output / "vocabulary.sqlite"
    base.create_database(dbpath, entries, raw_rows, concepts, wn_index)
    with closing(sqlite3.connect(dbpath)) as db, db:
        db.execute("CREATE TABLE reviewed_senses(sense_id TEXT PRIMARY KEY,word TEXT,pos TEXT,cefr_level TEXT,meaning_id TEXT,payload TEXT)")
        db.execute("CREATE INDEX reviewed_senses_word ON reviewed_senses(word)")
        db.execute("CREATE TABLE sense_indonesian_terms(term TEXT,sense_id TEXT REFERENCES reviewed_senses(sense_id),PRIMARY KEY(term,sense_id))")
        for sense in senses:
            db.execute("INSERT INTO reviewed_senses VALUES(?,?,?,?,?,?)", (sense["sense_id"], base.normalize(sense["word"]), sense["pos"], sense["cefr_level"], sense["meaning_id"], json.dumps(sense, ensure_ascii=False)))
            for term in set(base.normalize(t) for t in sense["indonesian_lookup_terms"]):
                db.execute("INSERT INTO sense_indonesian_terms VALUES(?,?)", (term, sense["sense_id"]))
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("v2 SQLite checks failed")

    before_translation_pairs = sum(len(c["indonesian_terms_source_candidates"]) for c in concepts.values())
    before_makan = sum("makan" in c["indonesian_terms_source_candidates"] for c in concepts.values())
    after_makan = sum("makan" in c["indonesian_terms"] for c in concepts.values())
    summary = {
        "dataset_version": "2.0.0", "built_on": "2026-10-22",
        "source_rows_preserved": len(raw_rows), "lexeme_count": len(entries),
        "original_lexeme_count": len(originals), "pos_corrections_applied": len(changes),
        "wordnet_gap_POS_confirmed_by_cambridge": len(cleared_pos),
        "cambridge_conflict_headwords_looked_up": len(checks["levels"]),
        "cambridge_POS_headwords_looked_up": len(checks["parts_of_speech"]),
        "cambridge_core_headwords_looked_up": len(core_checks["core_vocabulary"]),
        "cambridge_unique_headwords_with_lookup_attempts": len(indexed_checks),
        "reviewed_senses_with_original_indonesian_and_examples": len(senses),
        "reviewed_indonesian_lookup_groups": len(ind_matrices),
        "reviewed_sense_level_counts": dict(Counter(s["cefr_level"] for s in senses)),
        "source_wordlist_level_counts": dict(Counter(e["wordlist_level"] for e in entries.values() if e["wordlist_level"])),
        "remaining_multi_level_lexemes": sum(len(e["cefr_levels_claimed"]) > 1 for e in entries.values()),
        "invalid_pos_remaining": sum(e["pos"] not in base.VALID_POS for e in entries.values()),
        "entries_with_source_Y_indonesian": sum(e["source_Y_indonesian_sense_count"] > 0 for e in entries.values()),
        "raw_translation_pairs_v1": before_translation_pairs,
        "default_translation_pairs_v2": sum(len(c["indonesian_terms"]) for c in concepts.values()),
        "makan_source_concepts_before": before_makan, "makan_source_concepts_after": after_makan,
        "makan_verb_concepts_after": sum("makan" in c["indonesian_terms"] and c["pos"] == "verb" for c in concepts.values()),
        "source_translation_quality": quality_report,
        "human_reviewed_by_SpeakWE": 0,
        "limitations": ["Cambridge checks use indexed excerpts, not every dictionary sense or every word.",
            "Source quality Y means checked by the source project, not certified infallible.",
            "Unknown levels and translations remain unknown; no blanket guessing or auto-approval.",
            "Unreviewed wordlist levels do not become sense labels.",
            "Pilot senses were checked by an AI editor; production_approved remains false."],
    }
    migration = {"schema_version": 1, "changes": changes, "cleared_false_positive_POS_flags": cleared_pos,
        "policy_corrections": ["WordNet absence is a coverage note, not an invalid POS decision.",
            "Only source quality Y Indonesian links enter default lookup; I-specific annotations override shared B annotations.",
            "Cambridge levels are attached to reviewed senses; not overwritten across all headword meanings."],
        "remaining": {"multi_level_lexemes": summary["remaining_multi_level_lexemes"],
            "note": "Multiple source profiles remain preserved; use reviewed senses when selecting a meaning."}}
    changed_ids = {change["old_entry_id"]: change["new_entry_id"] for change in changes}
    new_by_id = {entry["entry_id"]: entry for entry in entries.values()}
    original_audit = []
    for old in originals.values():
        if not old["quality_flags"]:
            continue
        new_id = changed_ids.get(old["entry_id"], old["entry_id"])
        new = new_by_id[new_id]
        original_audit.append({"old_entry_id": old["entry_id"], "new_entry_id": new_id,
            "word": old["word"], "original_pos": old["pos"], "current_pos": new["pos"],
            "original_flags": old["quality_flags"], "pos_changed": old["entry_id"] in changed_ids,
            "POS_reference_status": new["pos_evidence_status"],
            "cambridge_reference_checks": new["cambridge_reference_checks"],
            "reviewed_sense_ids": new["reviewed_sense_ids"],
            "remaining_level_profiles": new["cefr_levels_claimed"],
            "fully_resolved": bool(new["reviewed_sense_ids"]) and not new["quality_flags"],
            "note": "A lookup without a visible CEFR label is not a verified CEFR level."})
    if len(original_audit) != 196:
        raise ValueError("Unexpected original review case count")
    base.jsonl_write(args.output / "audit-original-196.jsonl", original_audit)
    base.json_write(args.output / "summary.json", summary)
    base.json_write(args.output / "migration-report.json", migration)
    base.json_write(args.output / "sources.lock.json", source_lock)
    base.json_write(args.output / "curation-checksums.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(CURATION.glob("*.json"))})
    base.json_write(args.output / "checksums.json", {p.relative_to(args.output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(args.output.rglob("*")) if p.is_file() and p.name != "checksums.json"})
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
