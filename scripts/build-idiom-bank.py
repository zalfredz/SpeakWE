"""Build the original SpeakWE IELTS idiom pilot bank from reviewed input.

Offline, standard library only. No model calls, dictionary scraping or band bonus.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "data/language-bank"
CURATION = BANK / "curation"
OUTPUT = BANK / "idioms-v1"
VERSION = "1.0.0"
IELTS_URL = "https://ielts.org/news-and-insights/how-to-use-idioms-in-the-ielts-speaking-test"
CRITERIA_URL = "https://ielts.org/cdn/ielts-guides/ielts-speaking-key-assessment-criteria.pdf"

TOPICS = {
    "relationships": ("Hubungan dan pertemanan", "Describe someone who has helped you."),
    "work": ("Pekerjaan", "Describe a challenging task you completed at work or in a group."),
    "education": ("Pendidikan", "Describe a learning experience that was important to you."),
    "health": ("Kesehatan dan istirahat", "What do you do when you need a rest?"),
    "daily_life": ("Kehidupan sehari-hari", "What do you usually do in the evening?"),
    "technology": ("Teknologi", "How has technology changed the way people work?"),
    "hobbies": ("Hobi", "What do you enjoy doing in your free time?"),
    "habits": ("Kebiasaan", "Is there a habit you would like to change?"),
    "food": ("Makanan", "Do you prefer eating at home or eating out?"),
    "entertainment": ("Hiburan", "What kinds of films do you enjoy?"),
    "emotions": ("Perasaan", "Describe a time when you felt nervous or excited."),
    "achievements": ("Pencapaian", "Describe an achievement you are proud of."),
    "sport": ("Olahraga", "Do you enjoy taking part in sports?"),
    "experiences": ("Pengalaman", "Describe an unexpected event in your life."),
    "decisions": ("Keputusan", "What helps people make difficult decisions?"),
    "money": ("Uang dan pengeluaran", "Why is saving money important for young people?"),
    "society": ("Masyarakat", "What challenges do people face in large cities?"),
    "travel": ("Perjalanan", "Describe a place you enjoyed visiting."),
    "future": ("Masa depan", "What would you like to achieve in the future?"),
    "shopping": ("Belanja", "How do you decide whether something is worth buying?"),
    "skills": ("Keterampilan", "Describe a skill that took you time to learn."),
    "problems": ("Masalah dan solusi", "Describe a difficult problem you managed to solve."),
    "home": ("Rumah dan tempat tinggal", "What do you like about the area where you live?"),
    "community": ("Komunitas", "How can neighbours help each other?"),
    "family": ("Keluarga", "Who in your family has influenced you?"),
    "communication": ("Komunikasi", "Why do misunderstandings happen between people?"),
    "media": ("Media dan informasi", "How do you decide whether information online is reliable?"),
    "environment": ("Lingkungan", "What can individuals do to reduce waste?"),
    "opinions": ("Pendapat", "What should people consider when choosing a course?"),
    "places": ("Tempat", "Do you prefer busy places or quiet places?"),
    "nature": ("Alam", "Do you enjoy spending time in the countryside?"),
    "weather": ("Cuaca", "Does the weather affect your plans?"),
    "people": ("Deskripsi orang", "Describe a person you admire."),
}

POLICY = {
    "scoring_rule": "No points or band bonus from idiom presence, count, CEFR label or phrase length.",
    "recommendation_mode": "optional_post_session_candidate_requires_context_check",
    "semantic_checks_required": ["same_intended_meaning", "intensity_preserved", "speaker_attitude_preserved", "tense_and_pronouns_correct", "register_and_topic_fit", "no_new_facts_added"],
    "fluency_priority": "Do not interrupt speaking or require a target idiom. A clear natural plain answer is acceptable.",
    "ranking": "Filter by meaning and local context before topic relevance; topic match alone does not justify a rewrite.",
    "display_limit": "As a product design choice, show at most 1-2 optional idiom suggestions per completed session; this is not an IELTS rule.",
    "automatic_replacement": False,
    "frequency_claim": "Priority is an editorial learning order, not measured native-speaker frequency.",
}

# Editorial learning order, independent of dictionary CEFR and IELTS band.
STARTER = {"break the ice", "under the weather", "a piece of cake", "over the moon", "out of the blue", "make ends meet", "learn the ropes", "go the extra mile", "see eye to eye", "keep an eye on", "lose track of time", "have a lot on your plate", "in the long run", "the best of both worlds", "not my cup of tea"}
GLOSSARY_SEARCH = {
    "hubungan": "relationships", "kerja": "work", "pekerjaan": "work", "pendidikan": "education",
    "sekolah": "education", "uang": "money", "kesehatan": "health", "keluarga": "family",
    "perjalanan": "travel", "liburan": "travel", "cuaca": "weather", "hobi": "hobbies",
    "teknologi": "technology", "lingkungan": "environment", "perasaan": "emotions",
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_entries():
    source = json.loads((CURATION / "ielts-idioms.json").read_text(encoding="utf-8"))
    refs = json.loads((CURATION / "idiom-reference-checks.json").read_text(encoding="utf-8"))
    references = {r["phrase"]: r for r in refs["observations"]}
    if len(references) != len(refs["observations"]):
        raise ValueError("Duplicate reference phrases")
    entries = []
    seen = set()
    for row in source["rows"]:
        if len(row) != len(source["columns"]):
            raise ValueError("Unexpected column count")
        entry = dict(zip(source["columns"], row))
        phrase = entry["phrase"]
        if phrase in seen or phrase not in references:
            raise ValueError("Duplicate phrase or missing reference: " + phrase)
        seen.add(phrase)
        for topic in entry["topics"]:
            if topic not in TOPICS:
                raise ValueError("Unknown topic: " + topic)
        if not set(entry["ielts_parts"]) <= {1, 2, 3}:
            raise ValueError("Invalid IELTS part")
        ref = references[phrase]
        entry["entry_id"] = "expression-" + hashlib.sha256(phrase.casefold().encode()).hexdigest()[:20]
        entry["expression_type"] = ref["expression_type"]
        entry["cefr_level"] = ref["cefr_level"]
        entry["cefr_scope"] = ref["cefr_scope"]
        entry["reference"] = ref
        entry["learning_priority"] = "starter" if phrase in STARTER else "context_specific"
        entry["ielts_part_scope"] = "editorial_context_suitability_not_an_official_phrase_list"
        entry["register_scope"] = "editorial_usage_guidance_not_all_labels_verbatim_from_dictionary"
        entry["example_pair_scope"] = "original_written_examples_not_real_learner_transcripts_or_band_scored_answers"
        entry["review"] = {"reviewer_type": "AI_editor", "checked_on": "2026-10-22", "status": "reference_checked_pilot", "human_reviewed": False, "pilot_ready": True, "production_approved": False}
        entry["scoring"] = {"automatic_band_bonus": False, "target_ielts_band": None}
        entry["text_origin"] = source["text_origin"]
        entry["license"] = "CC-BY-4.0_for_SpeakWE_original_content_only"
        entries.append(entry)
    if seen != set(references):
        raise ValueError("Unused reference record")
    return entries


def render_catalog(entries):
    lines = ["# Bank idiom dan ungkapan IELTS Speaking", "", "Versi 1.0.0 — contoh dan penjelasan asli SpeakWE. Ini bahan latihan, bukan daftar resmi IELTS atau jawaban berband tertentu.", "", "Level kosong berarti label CEFR tidak terlihat pada arti/ungkapan yang diperiksa. Level tidak ditebak. Konteks, register dan kelancaran tetap lebih penting daripada jumlah idiom.", "", "## Indeks", "", "| Ungkapan | Jenis | CEFR referensi | Arti Indonesia |", "| --- | --- | --- | --- |"]
    for e in entries:
        lines.append(f"| [{e['phrase']}](#{e['entry_id']}) | {e['expression_type']} | {e['cefr_level'] or '—'} | {e['meaning_id']} |")
    for e in entries:
        lines.extend(["", f"<a id=\"{e['entry_id']}\"></a>", f"## {e['phrase']}", "", e["meaning_id"] + ".", "", f"Topik: {', '.join(TOPICS[t][0] for t in e['topics'])}. Cocok dipertimbangkan pada Part {', '.join(map(str, e['ielts_parts']))}; ini penilaian editorial.", "", f"Jenis: `{e['expression_type']}`. Register: `{e['register']}`. Level referensi: **{e['cefr_level'] or 'belum tersedia'}**.", "", f"Pola: `{e['pattern']}`.", "", f"- Kalimat biasa: {e['plain_en']}", f"- Pilihan idiomatis: {e['idiomatic_en']}", "", "**Kapan cocok:** " + e["when_to_use_id"], "", "**Perhatikan:** " + e["avoid_id"], "", f"[Rujukan Cambridge]({e['reference']['reference_url']}); pemeriksaan cuplikan terindeks, 22 Oktober 2026. Status: editor AI, belum review manusia."])
        if e["variant"]:
            lines.extend(["", "Varian: " + e["variant"] + "."])
    return "\n".join(lines) + "\n"


def main():
    entries = load_entries()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUTPUT / "expressions.jsonl", entries)
    write_jsonl(OUTPUT / "idioms.jsonl", [e for e in entries if e["expression_type"] == "idiom"])
    write_jsonl(OUTPUT / "related-expressions.jsonl", [e for e in entries if e["expression_type"] != "idiom"])
    topics = {t: {"label_id": TOPICS[t][0], "practice_question_en": TOPICS[t][1], "question_origin": "SpeakWE_original_practice_not_a_claim_about_current_test_questions", "entry_ids": [e["entry_id"] for e in entries if t in e["topics"]]} for t in sorted(TOPICS)}
    write_json(OUTPUT / "topics.json", topics)
    write_json(OUTPUT / "search-aliases.json", GLOSSARY_SEARCH)
    write_json(OUTPUT / "recommendation-policy.json", POLICY)
    write_jsonl(OUTPUT / "starter-pack.jsonl", [e for e in entries if e["learning_priority"] == "starter"])
    write_json(OUTPUT / "sources.json", {"primary_lexical_reference": "Cambridge Dictionary", "lookup_method": "indexed_excerpts_of_official_pages", "direct_page_access": "403 on a checked direct fetch; no bypass", "checked_on": "2026-10-22", "references": [e["reference"] for e in entries], "scoring_guidance": [{"url": IELTS_URL, "role": "natural idiomatic language; do not force or overuse"}, {"url": CRITERIA_URL, "role": "precision, style, collocation and paraphrase in lexical resource"}], "text_policy": "Only factual reference metadata retained; explanations and examples original to SpeakWE; no dictionary dump"})
    (OUTPUT / "CATALOG.md").write_text(render_catalog(entries), encoding="utf-8")
    summary = {"dataset_version": VERSION, "built_on": "2026-10-22", "entries": len(entries), "types": dict(Counter(e["expression_type"] for e in entries)), "idioms": sum(e["expression_type"] == "idiom" for e in entries), "related_expressions": sum(e["expression_type"] != "idiom" for e in entries), "starter_pack": sum(e["learning_priority"] == "starter" for e in entries), "topics": len(topics), "entries_with_observed_expression_CEFR": sum(bool(e["cefr_level"]) for e in entries), "CEFR_counts": dict(Counter(e["cefr_level"] or "unknown" for e in entries)), "original_example_pairs": len(entries), "human_reviewed": 0, "production_approved": 0, "automatic_band_bonus": False}
    write_json(OUTPUT / "summary.json", summary)
    write_json(OUTPUT / "curation-checksums.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(CURATION.glob("*.json"))})
    write_json(OUTPUT / "checksums.json", {p.relative_to(OUTPUT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUTPUT.rglob("*")) if p.is_file() and p.name != "checksums.json"})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
