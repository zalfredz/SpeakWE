"""Normalize user-supplied references for local review; does not train or score a model."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pymupdf


CRITERIA = [
    "fluency_and_coherence",
    "lexical_resource",
    "grammatical_range_and_accuracy",
    "pronunciation",
]

# Pages 4 and 5 contain raster images. These questions were transcribed from
# rendered pages, rather than inferred from the almost-empty text layer.
TOPICS = [
    ("work-study", "Work and study", 2, 1, ["Do you work or are you a student?"]),
    ("travel", "Travel", 2, 1, ["Do you enjoy travelling?"]),
    ("neighbourhood", "Neighbourhood", 2, 1, ["What do you like about your neighborhood?"]),
    ("communication", "Communication: past and present", 2, None, [
        "In your country, did people in the past contact others in the same ways as they do today?"
    ]),
    ("favourite-place", "Your favourite place", 4, 1, [
        "What place do you most like to visit?",
        "How often do you visit this place?",
        "Why do you like it so much?",
        "Is it popular with many other people?",
        "Has it changed very much since you first went there? In what way?",
    ]),
    ("food-cooking", "Food and cooking", 4, 1, [
        "What kinds of food do you like to eat?",
        "What kind of new food would you like to try? Why?",
        "Do you like cooking? Why or why not?",
        "What was the last meal you cooked?",
        "Do you prefer home-cooked food or food from restaurants? Why?",
    ]),
    ("friends", "Friends", 4, 1, [
        "Are your friends mostly your age or different ages? Why?",
        "Do you usually see your friends during the week or at weekends? Why?",
        "The last time you saw your friends, what did you do together?",
        "In what ways are your friends important to you?",
    ]),
    ("cold-weather", "Cold weather", 4, 1, [
        "Have you ever been in very cold weather? When?",
        "How often is the weather cold where you come from?",
        "Are some parts of your country colder than others? Why?",
        "Would you prefer to live in a hot place or a cold place? Why?",
    ]),
    ("flowers", "Flowers", 4, 1, [
        "Do you like to have flowers in your home? Why or why not?",
        "Where would you go to buy flowers? Why?",
        "On what occasions would you give someone flowers?",
        "Are flowers important in your culture? Why or why not?",
    ]),
    ("clothes", "Clothes", 5, 1, [
        "How important are clothes and fashion to you? Why or why not?",
        "What kinds of clothes do you dislike? Why?",
        "How different are the clothes you wear now from those you wore 10 years ago?",
        "What do you think the clothes we wear say about us?",
    ]),
    ("entertainment", "Entertainment", 5, 1, [
        "Do you prefer relaxing at home or going out in the evening? Why?",
        "When you go out for an evening, what do you like to do?",
        "How popular is this with other people in your country?",
        "Is there any kind of entertainment you do not like? Why or why not?",
    ]),
    ("colour", "Colour", 5, 1, [
        "What's your favourite colour? Why?",
        "Do you like the same colours now as you did when you were younger? Why or why not?",
        "What can you learn about a person from the colours they like?",
        "Do any colours have a special meaning in your culture?",
    ]),
    ("school", "School", 5, 1, [
        "Did you go to secondary/high school near to where you lived? Why or why not?",
        "What did you like about your secondary/high school? Why?",
        "Tell me about anything you didn't like at your school.",
        "How do you think your school could be improved? Why or why not?",
    ]),
    ("gifts", "Giving gifts", 5, 1, [
        "When do people give gifts or presents in your country?",
        "Do you ever take a gift when you visit someone in their home? Why or why not?",
        "When did you last receive a gift? What was it?",
        "Do you enjoy looking for gifts for people? Why or why not?",
    ]),
]

OBSERVATIONS = [
    ("willingness_to_extend", CRITERIA[0], "Mengembangkan jawaban", "context_dependent", ["audio", "transcript", "question"]),
    ("hesitation", CRITERIA[0], "Jeda dan keraguan saat berbicara", "context_dependent", ["audio", "timestamps"]),
    ("fillers_and_connectors", CRITERIA[0], "Pemakaian fillers dan connectors", "context_dependent", ["audio", "transcript", "question"]),
    ("self_correction", CRITERIA[0], "Koreksi diri dan dampaknya pada alur", "context_dependent", ["audio", "transcript", "timestamps"]),
    ("vocabulary_variety", CRITERIA[1], "Variasi kosakata", "context_dependent", ["transcript", "question"]),
    ("question_repetition", CRITERIA[1], "Pengulangan pertanyaan pemeriksa", "context_dependent", ["transcript", "question"]),
    ("vocabulary_collocation_accuracy", CRITERIA[1], "Ketepatan kata dan collocations", "context_dependent", ["transcript", "question"]),
    ("grammatical_range", CRITERIA[2], "Variasi struktur sederhana dan kompleks", "context_dependent", ["transcript"]),
    ("grammar_comprehension_impact", CRITERIA[2], "Dampak kesalahan grammar pada pemahaman", "context_dependent", ["audio", "transcript", "question"]),
    ("intelligibility", CRITERIA[3], "Keterpahaman ujaran", "context_dependent", ["audio"]),
    ("word_pronunciation", CRITERIA[3], "Ketepatan pengucapan kata", "context_dependent", ["audio", "timestamps"]),
    ("word_sentence_stress", CRITERIA[3], "Tekanan kata dan kalimat", "context_dependent", ["audio", "timestamps"]),
]


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def descriptor_bullets(value: str) -> list[str]:
    return [normalize(s) for s in value.split("\u2022") if normalize(s)]


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rubric", type=Path, required=True)
    parser.add_argument("--material", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sources = []
    for source_id, filename, role in [
        ("user-speaking-descriptors", args.rubric, "rubric_reference"),
        ("user-inggo-speaking", args.material, "teaching_and_practice_reference"),
    ]:
        with pymupdf.open(filename) as doc:
            sources.append({"id": source_id, "filename": filename.name,
                            "original_path": str(filename.resolve()),
                            "sha256": hashlib.sha256(filename.read_bytes()).hexdigest(),
                            "page_count": len(doc), "role": role,
                            "printed_publication_date": None if role == "rubric_reference" else "2026",
                            "redistribution_rights": "not_assessed",
                            "human_scored_audio_examples": 0})

    with pymupdf.open(args.rubric) as doc:
        p = doc[0]
        table = p.find_tables().tables[0]
        headers = table.rows[0].cells
        bands = []
        for row_index, row in enumerate(table.rows[1:]):
            band = 9 - row_index
            _, y0, _, y1 = row.cells[0]
            if band <= 1:
                text = p.get_text("text", clip=pymupdf.Rect(headers[1][0], y0, table.bbox[2], y1), sort=True)
                bands.append({"band": band, "source_page": 1,
                              "global_descriptor": descriptor_bullets(text),
                              "applies_to": "whole_response"})
                continue
            criteria = {}
            for criterion, header in zip(CRITERIA, headers[1:]):
                text = p.get_text("text", clip=pymupdf.Rect(header[0], y0, header[2], y1), sort=True)
                criteria[criterion] = descriptor_bullets(text)
            if not all(criteria.values()):
                raise ValueError(f"Missing descriptor for band {band}")
            bands.append({"band": band, "source_page": 1, "criteria": criteria})

    write_json(args.output / "rubric-reference.json", {
        "schema_version": 1, "id": "ielts-speaking-user-public-v1",
        "source_id": sources[0]["id"], "status": "candidate_pending_scoring_review",
        "edition": "Public version; no edition date printed in source",
        "extraction": "PDF table row geometry and header-defined column clipping",
        "bands": bands,
        "implementation_rules": [
            "Source descriptors are preserved as references, not converted to word-count thresholds.",
            "Missing audio or failed transcription is not automatically band 0.",
            "Evaluate all four criteria; store supporting evidence and uncertainty.",
            "Fluency coaching priority does not change IELTS criterion weights.",
            "Use of fillers, connectors, idioms or C2 words has no automatic bonus.",
        ],
    })

    questions = []
    topic_records = []
    for topic_id, label, page, part, prompts in TOPICS:
        topic_records.append({"id": topic_id, "label": label, "source_page": page, "question_count": len(prompts)})
        for index, prompt in enumerate(prompts, 1):
            questions.append({"id": f"inggo-{topic_id}-{index:02d}", "topic_id": topic_id,
                              "prompt": prompt, "source_id": sources[1]["id"], "source_page": page,
                              "extraction": "manual_visual" if page >= 4 else "embedded_text",
                              "suggested_part": part,
                              "part_assignment": "material_context" if part else "requires_review",
                              "status": "reference_imported", "gold_band_score": None,
                              "cefr_level": None})
    assert len(topic_records) == 14 and len(questions) == 46
    assert len({q["id"] for q in questions}) == len(questions)
    write_json(args.output / "practice-reference.json", {
        "schema_version": 1, "source_id": sources[1]["id"],
        "scope": "Predominantly introductory/Part 1 practice; not a complete Part 1-3 test bank",
        "topics": topic_records, "questions": questions,
        "excluded": "Sample answers are not imported as gold-scored responses.",
    })

    write_json(args.output / "observation-checklist.json", {
        "schema_version": 1, "source_id": sources[1]["id"], "source_page": 3,
        "scoring_semantics": "diagnostic_only_not_additive",
        "allowed_observations": ["observed", "not_observed", "uncertain", "insufficient_evidence"],
        "evidence_fields": ["question_id", "audio_start_seconds", "audio_end_seconds", "transcript_quote", "explanation"],
        "items": [{"id": key, "criterion": criterion, "label_id": label,
                   "interpretation": polarity, "evidence_required": evidence}
                  for key, criterion, label, polarity, evidence in OBSERVATIONS],
        "fluency_notes": [
            "Distinguish planning pauses from lexical-search hesitation.",
            "Keep disfluencies in the analysis transcript rather than relying on a cleaned transcript.",
            "Self-correction and fillers must be interpreted in context.",
        ],
    })

    write_json(args.output / "coaching-reference.json", {
        "schema_version": 1, "source_id": sources[1]["id"], "source_pages": [1, 2],
        "response_patterns": ["answer_then_reason", "answer_then_reason_and_example", "conditional_answer_then_reason", "two_or_three_relevant_points", "past_present_contrast"],
        "expression_candidates": [
            {"expression": "recharge one's batteries", "category": "idiom", "source_page": 2,
             "meaning_id": "beristirahat atau melakukan aktivitas yang memulihkan energi", "cefr_level": None, "status": "needs_lexical_verification"},
            {"expression": "be into something", "category": "conversational_expression", "source_page": 2,
             "meaning_id": "menyukai atau tertarik pada sesuatu", "cefr_level": None, "status": "needs_lexical_verification"},
            {"expression": "not a big fan of something", "category": "conversational_expression", "source_page": 2,
             "meaning_id": "tidak terlalu menyukai sesuatu", "cefr_level": None, "status": "needs_lexical_verification"},
        ],
        "discourse_marker_candidates": ["well", "yeah", "you know", "like", "in fact", "right", "okay", "so", "I guess", "I suppose", "actually", "basically"],
        "curation_notes": [
            "Do not assign CEFR levels from these PDFs: neither supplies verified lexical levels.",
            "Sample answers are teaching examples and have no examiner score attached.",
            "Page 2 contains 'First thing first'; review it rather than teaching that form unchanged.",
            "Each discourse marker can serve different functions depending on context.",
        ],
    })

    manifest = {
        "schema_version": 1, "imported_at": datetime.now(timezone.utc).isoformat(),
        "storage": "Local reference preparation; not included in the public web build",
        "sources": sources, "counts": {"rubric_bands": len(bands), "criteria": len(CRITERIA),
            "observation_items": len(OBSERVATIONS), "topic_groups": len(topic_records),
            "practice_questions": len(questions), "human_scored_audio_examples": 0},
        "remaining_inputs": [
            "Human-reviewed audio/transcript pairs with scores for each criterion for ML calibration.",
            "Additional Part 2 cue cards and Part 3 question sets.",
            "Verified lexical entries and CEFR senses for the B2-C2 recommendation bank.",
            "Confirm the scoring rubric edition before activating band estimation.",
        ],
    }
    write_json(args.output / "source-manifest.json", manifest)
    print(json.dumps(manifest["counts"], indent=2))


if __name__ == "__main__":
    main()
