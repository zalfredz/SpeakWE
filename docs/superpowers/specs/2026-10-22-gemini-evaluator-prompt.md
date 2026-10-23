# Prompt evaluator Gemini — SpeakWE IELTS Speaking

Versi: `prompt_version = ielts-eval-v2`, `criteria_pack_version = speakwe-criteria-v1`. Status: **draf**. Perubahan dari v1 ada di §8.
Bagian dari [desain tahap 1](2026-10-22-ielts-mvp-design.md) §6.5.

Dokumen ini berisi:

1. pembagian tugas antara Gemini dan server;
2. system prompt lengkap;
3. template input per sesi;
4. schema output JSON;
5. contoh lengkap: input → output Gemini → laporan akhir yang dilihat pengguna;
6. aturan validasi server;
7. yang masih harus diisi sebelum dipakai.

Model target: `gemini-3.5-flash-lite` (pilihan pengguna). Uji manual pertama dilakukan pengguna di Google AI Studio memakai paket lokal di `data/private/gemini-manual-test/`.

Prompt ditulis dalam bahasa Inggris karena model lebih konsisten menilai dengan rubrik berbahasa Inggris. Semua teks yang dibaca pengguna diminta keluar dalam bahasa Indonesia.

---

## 1. Pembagian tugas

| Dikerjakan Gemini | Dikerjakan server (bukan Gemini) |
| --- | --- |
| Mendengarkan audio dan membaca transkrip | Gerbang kualitas audio sebelum memanggil Gemini |
| Band **per kriteria** (bilangan bulat 0–9) beserta bukti | **Menghitung overall** dan pembulatannya |
| Alasan kenapa band itu, bukan satu di atas atau di bawahnya | Memvalidasi kutipan dan timestamp terhadap transkrip |
| Menandai bagian yang kemungkinan salah transkripsi (ASR) | Menerapkan offset kalibrasi (kalau ada) |
| Ringkasan, 1–3 prioritas, dan latihan ulang, dalam bahasa Indonesia | Mencari alternatif ungkapan di bank vocabulary/idiom |
| Menandai bagian yang layak di-upgrade (span + maksud) | Menyimpan hasil sebagai label silver untuk ML |

Alasan overall tidak dihitung Gemini: aritmetika dan aturan pembulatan harus pasti dan berversi, sedangkan model bisa salah hitung.

**Aturan overall (server):** rata-rata empat kriteria. Pecahan .25 dibulatkan ke atas menjadi .5, pecahan .75 dibulatkan ke atas menjadi bilangan bulat berikutnya, sesuai konvensi IELTS. Contoh: 6, 6, 6, 7 → 6,25 → **6,5**. Overall hanya dihitung untuk full test dengan keempat kriteria terisi.

---

## 2. System prompt

```text
You are the SpeakWE IELTS Speaking evaluator. You assess a candidate's recorded
answers the way a trained, strict, fair IELTS Speaking examiner would, using ONLY
the SpeakWE criteria pack provided below. You are not a tutor during the test and
you are not trying to encourage the candidate. Accuracy matters more than kindness.

## What you receive
- SESSION: mode (part1 | part2 | part3 | full), the parts actually completed.
- TASKS: every question / cue card the examiner asked, keyed by turn_id.
- AUDIO: one audio clip per candidate turn, labelled with its turn_id. Only the
  candidate speaks in these clips.
- TRANSCRIPT: verbatim ASR of each turn. Each line starts with
  segment_id=<id> start_ms=<n> end_ms=<n>. It keeps fillers (um, uh),
  repetitions and self-corrections. It may contain ASR errors. Words the ASR
  was unsure about are marked with [?] right after the word, e.g. "finger[?]".
  A [?] word is a guess by the ASR, not proof of what was said.
- FEATURES: fluency measurements computed by SpeakWE from the audio timing
  (pause ratio, mean length of run, speech rate, fillers per minute,
  repetitions, self-corrections). These are signals, not scores.
- CRITERIA PACK: official band descriptors, SpeakWE key distinctions, scoring
  rules, and per-band reference anchors taken from rated mock tests.

## How to assess
1. Listen to ALL audio before deciding any band. Pronunciation and Fluency &
   Coherence must be judged from the audio, never from the transcript alone.
2. Assess the four criteria independently:
   FC  = Fluency and Coherence
   LR  = Lexical Resource
   GRA = Grammatical Range and Accuracy
   P   = Pronunciation
   A strong criterion must not lift a weak one, and a friendly tone or
   confident delivery must not lift LR or GRA.
3. For each criterion, use best fit, as IELTS examiners do. Compare the two
   neighbouring bands in BOTH directions: which key features of band N, and
   of band N+1, does the evidence show? Choose the band that matches the
   performance as a whole. One missing feature does not block a band that
   otherwise fits, and one strong moment does not earn a band the rest of the
   performance does not support. Do not lean low or high by default.
4. Compare the performance with the REFERENCE ANCHORS. The anchors show what
   rated candidates at each band actually sounded like. If your band disagrees
   with the anchors, re-check before answering.
5. Treat FEATURES as supporting evidence. Do not convert a feature into a band
   by itself (fast speech is not automatically fluent; few pauses can mean
   memorised speech). Distinguish pauses for planning ideas from pauses to
   search for words.
6. The transcript is NOT evidence of pronunciation. Before treating any word
   as a mistake, listen to it in the audio.
   - A [?] word may only be used as evidence of a mistake if you clearly hear
     the problem in the audio. If the ASR simply misheard, list it in
     asr_suspected and do not penalise the candidate.
   - For a Pronunciation limitation, write in heard_as what you actually hear
     (approximate spelling, e.g. "ford", "jubailiss"). State the intended
     word only if the context makes it certain; otherwise say it is unclear.
     Never invent an intended word.
   - One problem counts under ONE criterion only: a correct word said
     unclearly is P; a wrong word chosen is LR; a wrong form is GRA.
   - Asking the examiner to repeat or explain a question is normal test
     behaviour, not a limitation, unless it happens repeatedly.
7. Evidence rules:
   - Every band needs at least 2 evidence items, including at least one
     limitation unless the band is 9.
   - Each evidence quote must be copied EXACTLY from ONE segment (at most
     about 20 words: the shortest span that shows the point), with that
     segment's segment_id, start_ms and end_ms. Write the id only, e.g. "s016".
     Do not copy the [?] markers into quotes.
   - Never invent quotes, timestamps or turns.
8. Penalise what real examiners penalise (see SCORING RULES). Never reward
   quantity: no credit for the number of idioms, rare words, connectors or
   for long answers as such. Reward only appropriate and accurate use.
9. If there is not enough candidate speech to judge a criterion (see SCORING
   RULES for minimums), return band null for that criterion with
   status "insufficient_evidence". Never guess.

## Writing the feedback
- All user-facing text (fields ending in _id) is in natural, direct Indonesian
  and addresses the learner as "kamu". Quotes and English examples stay in
  English.
- Be specific and honest. No empty praise ("bagus sekali!"). Mention a
  strength only if it is backed by evidence.
- priorities: 1 to 3 items, ordered by how much they hold the score back.
  If FC is the lowest or tied for lowest band, the FIRST priority must be FC.
- Each priority has one SPEAKING drill of at most 2 sentences that the learner
  can do in their next SpeakWE session (answer a question again, retell the
  Part 2 story, etc.). No writing tasks, lists or tables.
- upgrade_opportunities: mark spans where a more precise or natural expression
  would help. intended_meaning_en describes the meaning in at most 8 words; it
  is NOT a rewritten sentence. Do NOT write replacement vocabulary yourself;
  SpeakWE selects it from a reviewed bank. Only grammar_fix may contain a
  corrected version of the original span.

## Output
Return ONLY JSON that matches the provided response schema. No markdown.
Do not compute an overall band.
```

### 2.1 Paket kriteria (disisipkan setelah system prompt)

```text
## CRITERIA PACK: speakwe-criteria-v1

### Official band descriptors
{{OFFICIAL_DESCRIPTORS}}   <- full public IELTS Speaking band descriptors text

### SpeakWE key distinctions (paraphrased; official text above prevails)
FC
 9 fluent; only rare repetition or self-correction; hesitation is about ideas,
   not words; fully coherent, cohesion fully appropriate; topics fully developed.
 8 fluent; occasional repetition/self-correction; hesitation usually about
   content, rarely about finding words; develops topics coherently.
 7 speaks at length without noticeable effort or loss of coherence; some
   language-related hesitation, repetition or self-correction; uses a range
   of connectives and discourse markers with some flexibility.
 6 willing to speak at length but loses coherence at times through repetition,
   self-correction or hesitation; uses a range of connectives, not always
   appropriately.
 5 usually keeps going but relies on repetition, self-correction or slow speech;
   over-uses some connectives; simple speech is fluent, complex ideas cause
   fluency problems.
 4 cannot respond without noticeable pauses; slow, frequent repetition and
   self-correction; basic, repetitive linking; coherence sometimes breaks down.
LR
 9 full flexibility and precision on all topics; idiomatic language natural
   and accurate.
 8 wide resource used readily and flexibly for precise meaning; less common
   and idiomatic items used skilfully with occasional inaccuracy; paraphrases
   effectively.
 7 flexible across topics; some less common and idiomatic items; awareness of
   style and collocation with some inappropriate choices; paraphrases well.
 6 wide enough to speak at length and make meaning clear despite
   inappropriacies; generally paraphrases successfully.
 5 manages familiar and unfamiliar topics with limited flexibility; paraphrase
   attempts have mixed success.
 4 basic meaning on familiar topics only; frequent inappropriate word choice;
   rarely paraphrases.
GRA
 9 full range used naturally; consistently accurate apart from native-like slips.
 8 wide range used flexibly; most sentences error-free; occasional
   inappropriacy or non-systematic error.
 7 range of complex structures with some flexibility; frequently error-free
   sentences, though some errors persist.
 6 mix of simple and complex structures with limited flexibility; frequent
   errors in complex structures that rarely block understanding.
 5 basic forms reasonably accurate; few complex structures and these usually
   contain errors that may cause some misunderstanding.
 4 basic forms only, subordinate clauses rare; frequent errors that can cause
   misunderstanding.
P
 9 full range of features with precision and subtlety; effortless to understand.
 8 wide range of features, flexible use with occasional lapses; easy to
   understand throughout; accent has minimal effect.
 7 all positive features of 6 and some, not all, of 8.
 6 range of features with mixed control; some effective stress and intonation
   not sustained; generally understood, though some words or sounds reduce
   clarity at times.
 5 all positive features of 4 and some, not all, of 6.
 4 limited range of features; frequent lapses; mispronunciations cause some
   difficulty for the listener.

### SCORING RULES (from SpeakWE design and observed examiner feedback)
- Memorised or rehearsed-sounding answers: do not use them as evidence of LR or
  GRA range; note them as a limitation under FC (unnatural delivery) and LR.
- Very short answers that do not develop the topic limit FC to 6 or lower,
  even when the language is accurate.
- Monotone delivery or flat intonation throughout limits P to 6 or lower.
- Accent alone is never a reason to lower P; intelligibility and control are.
- Band 9 requires near-flawless performance on that criterion across all
  parts. It is rare; do not award it by default to strong candidates.
- Minimum candidate speech to score a criterion: at least {{MIN_TOTAL_SPEECH_S}}
  seconds in total and at least {{MIN_TURNS}} answered turns. Below this,
  band = null.
- Part-only sessions: score from that part only and set scope accordingly.
  Do not assume performance in parts that were not taken.

### REFERENCE ANCHORS (from rated mock tests, candidate speech only)
{{ANCHORS}}
```

### 2.2 Format `{{ANCHORS}}`

Dibuat otomatis dari 172 video **setelah** suara kandidat dipisah (desain §7 langkah 1). Video yang dipakai sebagai jangkar dicatat dan dikeluarkan dari evaluasi kalibrasi.

```text
band_group 6 (n=39 videos)
  typical FC signals (median [p25–p75]): pause_ratio 0.24 [0.19–0.29],
    mean_length_of_run 6.1 words [4.8–7.3], fillers_per_min 7.9 [5.2–10.4]
  anchor excerpt A (video ZRXJuk_jHXo, examiner: FC 6 LR 7 GRA 6 P 7):
    "<= 60 words of candidate speech, verbatim>"
  anchor excerpt B (...)
band_group 7 (n=38 videos)
  ...
```

> **Catatan:** angka di blok contoh ini **ilustrasi format**, belum dihitung dari data. Angka yang sebenarnya diisi oleh script.

---

## 3. Template input per sesi

```text
SESSION
mode: full
parts_completed: [1, 2, 3]
session_id: s_01HZY...

TASKS
t01 part1 "Let's talk about your hometown. Where is your hometown?"
t02 part1 "What do you like most about living there?"
...
t09 part2 cue_card: "Describe a time you helped someone. You should say: who you
    helped, why they needed help, how you helped them, and explain how you felt
    about it."
t10 part3 "Why do some people find it hard to ask for help?"
...

TRANSCRIPT
segment_id=t02-1 start_ms=12400 end_ms=19850: "Um, I think the thing I like most is,
      uh, the food, because there is many street food[?] near my house."
...

FEATURES
session: speech_s 512, pause_ratio 0.27, mean_length_of_run 5.4,
         speech_rate_wpm 118, fillers_per_min 9.6, repetitions 14, self_corrections 6
per_turn: t02 speech_s 7.1 pause_ratio 0.31 ...; t09 speech_s 104.0 ...

AUDIO
(one attached clip per turn, in turn order, each preceded by a text part "turn t02")
```

---

## 4. Schema output Gemini

Dikirim sebagai `responseSchema` (structured output). Server tetap memvalidasi ulang.

```json
{
  "type": "object",
  "required": ["status", "scope", "criteria", "asr_suspected", "feedback"],
  "properties": {
    "status": {"enum": ["ready", "partial", "insufficient_evidence"]},
    "scope": {"enum": ["full_test", "part1_only", "part2_only", "part3_only"]},
    "criteria": {
      "type": "object",
      "required": ["fc", "lr", "gra", "p"],
      "properties": {
        "fc":  {"$ref": "#/$defs/criterion"},
        "lr":  {"$ref": "#/$defs/criterion"},
        "gra": {"$ref": "#/$defs/criterion"},
        "p":   {"$ref": "#/$defs/criterion"}
      }
    },
    "asr_suspected": {
      "type": "array",
      "items": {"type": "object",
        "required": ["segment_id", "transcript_text", "likely_said"],
        "properties": {"segment_id": {"type": "string"}, "transcript_text": {"type": "string"},
                       "likely_said": {"type": "string"}}}
    },
    "feedback": {
      "type": "object",
      "required": ["summary_id", "priorities", "upgrade_opportunities"],
      "properties": {
        "summary_id": {"type": "string"},
        "priorities": {"type": "array", "minItems": 1, "maxItems": 3,
          "items": {"type": "object",
            "required": ["criterion", "title_id", "explanation_id", "evidence_segment_ids", "drill_id"],
            "properties": {"criterion": {"enum": ["fc", "lr", "gra", "p"]},
              "title_id": {"type": "string"}, "explanation_id": {"type": "string"},
              "evidence_segment_ids": {"type": "array", "items": {"type": "string"}},
              "drill_id": {"type": "string"}}}},
        "upgrade_opportunities": {"type": "array",
          "items": {"type": "object",
            "required": ["segment_id", "original", "kind", "intended_meaning_en"],
            "properties": {"segment_id": {"type": "string"}, "original": {"type": "string"},
              "kind": {"enum": ["grammar_fix", "more_precise_word", "collocation",
                                "connector", "idiomatic_option"]},
              "intended_meaning_en": {"type": "string"},
              "grammar_fix": {"type": "string"},
              "note_id": {"type": "string"}}}}
      }
    }
  },
  "$defs": {
    "criterion": {
      "type": "object",
      "required": ["band", "descriptor_fit_id", "evidence",
                   "why_not_higher_id", "why_not_lower_id"],
      "properties": {
        "band": {"type": ["integer", "null"], "minimum": 0, "maximum": 9},
        "descriptor_fit_id": {"type": "string"},
        "evidence": {"type": "array",
          "items": {"type": "object",
            "required": ["type", "turn_id", "segment_id", "start_ms", "end_ms", "quote", "observation_id"],
            "properties": {"type": {"enum": ["strength", "limitation"]},
              "turn_id": {"type": "string"}, "segment_id": {"type": "string"},
              "start_ms": {"type": "integer"}, "end_ms": {"type": "integer"},
              "quote": {"type": "string"}, "observation_id": {"type": "string"},
              "heard_as": {"type": "string"}}}},
        "why_not_higher_id": {"type": "string"},
        "why_not_lower_id": {"type": "string"}
      }
    }
  }
}
```

`heard_as` wajib diisi untuk bukti `limitation` kriteria P. `self_confidence` dihapus di v2, karena di uji v1 nilainya selalu "high" sehingga tidak berguna.

---

## 5. Contoh lengkap (ilustrasi, bukan data pengguna asli)

### 5.1 Potongan transkrip input

```text
[t02] seg t02-1 (12400–19850): "Um, I think the thing I like most is, uh, the food,
      because there is many street food near my house."
[t03] seg t03-1 (31200–40100): "Yes, I- I go there every weekend with my friends
      and we, um, we usually try new place."
[t09] seg t09-1 (95000–121300): "So I want to talk about the time when I helped my
      neighbour, she is an old lady and she, uh, she didn't know how to use the
      online banking."
[t09] seg t09-2 (121300–152800): "It was quite challenging because, um, she was
      very worried that she will lose her money, so I explained it step by step."
[t09] seg t09-3 (152800–181000): "After that I felt really, um, satisfied, because
      I could make her life a little bit easier."
[t10] seg t10-1 (205000–226400): "I think some people feel, uh, ashamed to ask help
      because they don't want to look weak in front of others."
[t11] seg t11-1 (240000–268500): "On the other hand, um, in my country, family is
      very close, so, uh, people usually ask their family first rather than
      strangers."
```

Fitur sesi: `pause_ratio 0.27`, `mean_length_of_run 5.4`, `fillers_per_min 9.6`, `repetitions 14`.

### 5.2 Contoh output Gemini

```json
{
  "status": "ready",
  "scope": "full_test",
  "criteria": {
    "fc": {
      "band": 6,
      "descriptor_fit_id": "Mau berbicara panjang dan ide tetap bisa diikuti, tetapi kelancaran sering terputus oleh pengulangan dan jeda untuk mencari kata.",
      "evidence": [
        {"type": "strength", "turn_id": "t09", "segment_id": "t09-2", "start_ms": 121300, "end_ms": 152800,
         "quote": "she was very worried that she will lose her money, so I explained it step by step",
         "observation_id": "Cerita Part 2 berkembang runtut: masalah, alasan, lalu tindakan."},
        {"type": "strength", "turn_id": "t11", "segment_id": "t11-1", "start_ms": 240000, "end_ms": 268500,
         "quote": "On the other hand", "observation_id": "Memakai penanda wacana untuk membandingkan sudut pandang."},
        {"type": "limitation", "turn_id": "t03", "segment_id": "t03-1", "start_ms": 31200, "end_ms": 40100,
         "quote": "I- I go there every weekend with my friends and we, um, we usually",
         "observation_id": "Pengulangan subjek ('I- I', 'we, um, we') sebelum melanjutkan kalimat; terjadi berkali-kali di Part 1."},
        {"type": "limitation", "turn_id": "t09", "segment_id": "t09-3", "start_ms": 152800, "end_ms": 181000,
         "quote": "I felt really, um, satisfied",
         "observation_id": "Jeda di tengah frasa untuk mencari kata, bukan untuk merencanakan ide."}
      ],
      "why_not_higher_id": "Band 7 menuntut bicara panjang tanpa usaha yang terdengar. Di sini jeda mencari kata dan pengulangan masih sering (rata-rata ±10 filler per menit) dan memutus alur di beberapa jawaban.",
      "why_not_lower_id": "Bukan band 5 karena kandidat tidak bergantung pada bicara lambat untuk bertahan, dan jawaban Part 2 tetap berkembang hampir 2 menit."
    },
    "lr": {
      "band": 6,
      "descriptor_fit_id": "Kosakata cukup untuk membahas topik dengan jelas, tetapi jarang memakai pilihan kata yang kurang umum atau kolokasi yang tepat.",
      "evidence": [
        {"type": "strength", "turn_id": "t10", "segment_id": "t10-1", "start_ms": 205000, "end_ms": 226400,
         "quote": "they don't want to look weak in front of others",
         "observation_id": "Ungkapan alami dan tepat untuk menjelaskan alasan sosial."},
        {"type": "limitation", "turn_id": "t03", "segment_id": "t03-1", "start_ms": 31200, "end_ms": 40100,
         "quote": "try new place", "observation_id": "Pilihan kata umum dan kurang tepat; maksudnya mencoba tempat makan baru."},
        {"type": "limitation", "turn_id": "t10", "segment_id": "t10-1", "start_ms": 205000, "end_ms": 226400,
         "quote": "ashamed to ask help", "observation_id": "Pola kolokasi kurang tepat: 'ask for help'."}
      ],
      "why_not_higher_id": "Band 7 membutuhkan beberapa kosakata kurang umum atau idiomatis yang dipakai dengan sadar gaya. Contoh seperti itu belum muncul.",
      "why_not_lower_id": "Bukan band 5: makna selalu jelas, dan kandidat bisa membahas topik abstrak Part 3 tanpa kehabisan kata."
    },
    "gra": {
      "band": 6,
      "descriptor_fit_id": "Campuran kalimat sederhana dan kompleks; kesalahan sering muncul tetapi jarang mengganggu pemahaman.",
      "evidence": [
        {"type": "strength", "turn_id": "t09", "segment_id": "t09-3", "start_ms": 152800, "end_ms": 181000,
         "quote": "because I could make her life a little bit easier",
         "observation_id": "Klausa sebab dengan modal lampau dipakai dengan benar."},
        {"type": "limitation", "turn_id": "t02", "segment_id": "t02-1", "start_ms": 12400, "end_ms": 19850,
         "quote": "there is many street food", "observation_id": "Kesalahan kesesuaian: 'there is many'."},
        {"type": "limitation", "turn_id": "t09", "segment_id": "t09-2", "start_ms": 121300, "end_ms": 152800,
         "quote": "she will lose her money", "observation_id": "Sequence of tenses: konteks lampau seharusnya 'would lose'."}
      ],
      "why_not_higher_id": "Band 7 menuntut banyak kalimat yang bebas kesalahan. Di sini kesalahan dasar (kesesuaian, tenses, artikel) masih muncul di hampir setiap Part.",
      "why_not_lower_id": "Bukan band 5 karena struktur kompleks (klausa sebab, relatif, perbandingan) dipakai cukup sering dan maknanya tetap jelas."
    },
    "p": {
      "band": 7,
      "descriptor_fit_id": "Mudah dipahami sepanjang tes; penekanan kata umumnya tepat; intonasi bervariasi tetapi belum konsisten di jawaban panjang.",
      "evidence": [
        {"type": "strength", "turn_id": "t09", "segment_id": "t09-2", "start_ms": 121300, "end_ms": 152800,
         "quote": "so I explained it step by step",
         "observation_id": "Penekanan dan pengelompokan kata alami; ritme jelas."},
        {"type": "limitation", "turn_id": "t11", "segment_id": "t11-1", "start_ms": 240000, "end_ms": 268500,
         "quote": "people usually ask their family first rather than strangers",
         "observation_id": "Intonasi mendatar di kalimat panjang Part 3, sehingga kontras ide kurang terdengar.",
         "heard_as": "intonasi datar di 'rather than strangers', tanpa penekanan kontras"}
      ],
      "why_not_higher_id": "Band 8 menuntut kontrol fitur pelafalan yang fleksibel sepanjang tes. Intonasi masih datar di beberapa jawaban panjang.",
      "why_not_lower_id": "Bukan band 6: tidak ada kata yang sulit dipahami, dan penekanan kalimat umumnya terkontrol."
    }
  },
  "asr_suspected": [],
  "feedback": {
    "summary_id": "Kamu sudah bisa berbicara panjang dan ceritamu di Part 2 runtut. Hambatan terbesar ada di kelancaran: kamu sering mengulang kata pertama kalimat dan berhenti di tengah frasa untuk mencari kata. Kesalahan grammar dasar juga masih muncul di setiap bagian.",
    "priorities": [
      {"criterion": "fc",
       "title_id": "Kurangi pengulangan di awal kalimat",
       "explanation_id": "Pola 'I- I' dan 'we, um, we' muncul berkali-kali dan membuat jawaban terdengar tersendat.",
       "evidence_segment_ids": ["t03-1", "t09-3"],
       "drill_id": "Jawab 3 pertanyaan Part 1 lagi. Sebelum bicara, tarik napas sekali lalu mulai langsung dengan subjek + kata kerja tanpa mengulang. Rekam dan hitung pengulanganmu."},
      {"criterion": "gra",
       "title_id": "Perbaiki 'there is/are' dan tenses dalam cerita lampau",
       "explanation_id": "Dua kesalahan ini muncul di jawaban yang berbeda, artinya polanya belum stabil.",
       "evidence_segment_ids": ["t02-1", "t09-2"],
       "drill_id": "Ulang cerita Part 2 kamu dalam 1 menit dan pastikan semua kata kerjanya bentuk lampau."},
      {"criterion": "lr",
       "title_id": "Pakai kolokasi yang lebih tepat",
       "explanation_id": "Beberapa ungkapan sudah jelas maknanya tetapi kurang natural.",
       "evidence_segment_ids": ["t03-1", "t10-1"],
       "drill_id": "Pelajari 3 saran ungkapan di bawah, lalu pakai masing-masing sekali saat menjawab ulang pertanyaan t03 dan t10."}
    ],
    "upgrade_opportunities": [
      {"segment_id": "t02-1", "original": "there is many street food", "kind": "grammar_fix",
       "intended_meaning_en": "a lot of street food is available", "grammar_fix": "there is a lot of street food"},
      {"segment_id": "t03-1", "original": "try new place", "kind": "collocation",
       "intended_meaning_en": "go to restaurants they have never visited"},
      {"segment_id": "t10-1", "original": "ashamed to ask help", "kind": "grammar_fix",
       "intended_meaning_en": "embarrassed to request help", "grammar_fix": "ashamed to ask for help"},
      {"segment_id": "t09-3", "original": "I felt really, um, satisfied", "kind": "more_precise_word",
       "intended_meaning_en": "felt good because they made a positive difference"}
    ]
  }
}
```

### 5.3 Laporan akhir yang dilihat pengguna

Server menambahkan overall (6 + 6 + 6 + 7 = 25 → 6,25 → **6,5**), memvalidasi kutipan, dan mengisi saran dari bank bahasa.

```text
Estimasi latihan SpeakWE — Full test · 22 Okt 2026 · bukan nilai resmi IELTS

ESTIMASI OVERALL  6.5
  Fluency & Coherence        6
  Lexical Resource           6
  Grammatical Range & Acc.   6
  Pronunciation              7

RINGKASAN
Kamu sudah bisa berbicara panjang dan ceritamu di Part 2 runtut. Hambatan
terbesar ada di kelancaran: kamu sering mengulang kata pertama kalimat dan
berhenti di tengah frasa untuk mencari kata. Kesalahan grammar dasar juga
masih muncul di setiap bagian.

PRIORITAS
1. Kurangi pengulangan di awal kalimat (Fluency)
   ▶ 0:31  "I- I go there every weekend with my friends and we, um, we usually"
   Latihan: jawab 3 pertanyaan Part 1 lagi, mulai langsung dengan subjek +
   kata kerja tanpa mengulang. Rekam dan hitung pengulanganmu.
2. Perbaiki 'there is/are' dan tenses dalam cerita lampau (Grammar)
   ▶ 0:12  "there is many street food"  →  there is a lot of street food
   ▶ 2:01  "she will lose her money"     →  she would lose her money
3. Pakai kolokasi yang lebih tepat (Vocabulary)

SARAN UNGKAPAN (dari bank SpeakWE)
  "try new place"         →  try somewhere new · check out a new place
  "ashamed to ask help"   →  ashamed to ask for help
  "I felt really satisfied" → it felt rewarding — membantu dan terasa berarti
  (level CEFR ditampilkan hanya kalau bank punya level terverifikasi untuk arti itu)

KENAPA BUKAN BAND LEBIH TINGGI?   [buka per kriteria]
  Fluency 7 menuntut bicara panjang tanpa usaha yang terdengar; jeda mencari
  kata dan pengulangan masih sering (±10 filler/menit).
  ...

Versi penilai: gemini · ielts-eval-v1 · speakwe-criteria-v1 · rubrik IELTS publik
```

---

## 6. Validasi server terhadap output Gemini

Output **ditolak**, lalu dicoba ulang sekali, kalau:

- JSON tidak sesuai schema, atau `band` di luar 0–9 atau bukan bilangan bulat.
- Ada kriteria dengan band yang buktinya kurang dari 2, atau tidak punya `limitation` padahal band < 9.
- `quote` tidak ditemukan persis di teks `segment_id` yang disebut, atau `start_ms`/`end_ms` tidak sama dengan segmen tersebut.
- `turn_id`/`segment_id` tidak ada di sesi.
- Bukti `limitation` kriteria P tidak punya `heard_as`.
- FC adalah band terendah (atau seri terendah), tapi prioritas pertama bukan FC.
- Kata yang sama (segmen dan kutipan yang sama) dipakai sebagai `limitation` di lebih dari satu kriteria.
- `scope` tidak sesuai dengan mode sesi, atau overall disertakan.

Kalau percobaan ulang tetap gagal, status penilaian menjadi `failed`. Sesi dan check-in tidak terpengaruh.

Setiap output yang diterima disimpan **utuh** beserta `prompt_version`, `criteria_pack_version`, nama model, offset kalibrasi yang diterapkan, dan fitur input. Data ini menjadi label silver untuk ML (desain §6.5).

---

## 7. Yang masih harus diisi sebelum dipakai

| Placeholder | Diisi dari |
| --- | --- |
| `{{OFFICIAL_DESCRIPTORS}}` | Teks deskriptor band Speaking resmi IELTS (publik) |
| `{{ANCHORS}}` | Script dari 172 video, setelah suara kandidat dipisah |
| `{{MIN_TOTAL_SPEECH_S}}`, `{{MIN_TURNS}}` | Konfigurasi. Usulan awal: 60 detik dan 3 giliran per Part, lalu disesuaikan saat kalibrasi |

Prompt dianggap layak setelah kalibrasi pada video yang bukan jangkar (desain §7 langkah 5) menunjukkan selisih rata-rata dan kecenderungan murah/ketat yang dapat diterima. Setiap perubahan prompt atau paket kriteria **menaikkan versinya** dan diuji ulang pada set yang sama.

---

## 8. Riwayat versi

**v2 (22 Okt 2026)**, berdasarkan uji manual v1 pada 3 video. Hasil v1: 7/12 skor kriteria tepat, 11/12 dalam ±1 band. Tidak murah memberi nilai, tapi terlalu ketat di band tinggi (LR −2 di band 7,5). Pengguna mendengarkan 4 klaim pronunciation: 1 ternyata kesalahan ASR yang dihukum ("figure skaters"), 1 kata maksud dikarang ("weekends" untuk "the beggin"), 1 dihitung dua kali di P dan LR ("ford"), dan 1 benar ("jubailiss").

Perubahan:
- "Kalau ragu pilih yang lebih rendah" diganti dengan best fit dua arah.
- Kata yang tidak yakin bagi ASR diberi tanda `[?]` dan dilarang dijadikan bukti kesalahan tanpa konfirmasi audio.
- Ada field `heard_as` untuk bukti pronunciation, dan Gemini dilarang mengarang kata yang dimaksud.
- Satu masalah hanya dihitung di satu kriteria.
- Minta klarifikasi bukan kelemahan.
- Format ID segmen dibuat tegas, dengan kutipan maksimal sekitar 20 kata dari satu segmen.
- Prioritas FC wajib pertama kalau FC terendah, dan latihan wajib berupa latihan berbicara.
- `intended_meaning_en` maksimal 8 kata, bukan kalimat tulis ulang.
- `self_confidence` dihapus, dan sapaan memakai "kamu".
