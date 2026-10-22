# Sumber grammar, paraphrase dan bank pertanyaan SpeakWE

Diperiksa 22 Oktober 2026. Lingkup: data teks untuk koreksi, alternatif ungkapan, materi latihan dan pertanyaan. Audio/transkrip band 5–9 dikerjakan terpisah dan tidak diakuisisi dalam pekerjaan ini.

**Hasil pekerjaan ini adalah inventaris sumber dan rekomendasi penggunaan. Dataset eksternal pada dokumen ini belum diunduh, belum diimpor, dan belum melatih model.** Katalog terstruktur: [text-coaching-sources.json](../data/catalog/text-coaching-sources.json). Catatan lisensi adalah ketentuan yang terlihat pada sumber, bukan izin tambahan dari SpeakWE.

## 4. Kesalahan grammar → koreksi

| Kandidat | Yang tersedia dan kegunaan | Batas untuk SpeakWE | Lisensi/keputusan awal |
| --- | --- | --- | --- |
| [W&I+LOCNESS / BEA-2019](https://www.cl.cam.ac.uk/research/nl/bea2019st/) | Tulisan learner dan koreksi; format M2 mencatat span, jenis edit dan annotator. Terdapat 34.308 kalimat training. Berguna untuk koreksi minimal dan analisis kategori kesalahan | Data tulisan, bukan percakapan IELTS. Tingkat A/B/C dalam corpus tidak menjadi skor IELTS. Label error dalam rilis standar juga melibatkan anotasi otomatis ERRANT, sehingga bukan semua kategori ditetapkan manusia | Penggunaan nonkomersial menurut halaman penyelenggara. Kandidat riset/evaluasi dalam lingkup izin; tidak diasumsikan boleh masuk produk komersial |
| [JFLEG](https://github.com/keisks/jfleg) | 1.501 kalimat, dev 754 dan test 747, masing-masing memiliki empat berkas referensi koreksi. Berguna untuk membandingkan beberapa koreksi yang dapat diterima | Koreksi fluency/naturalness tulisan dapat lebih luas dari koreksi minimal. Kata “Fluency” pada namanya bukan pengukuran kelancaran speaking. Tidak menyediakan penjelasan Indonesia | CC BY-NC-SA 4.0. Kandidat benchmark riset; jangan dicampur ke bank produksi komersial |
| [CoEdIT — rilis data penulis](https://huggingface.co/datasets/grammarly/coedit) | Pasangan instruction/source/target untuk editing, termasuk GEC dan paraphrase. Repo penulis menyebut rilis publik sekitar 69 ribu instans, lebih kecil dari 82 ribu yang dipakai dalam paper | Dataset writing assistance. Tidak semua edit menjaga gaya personal atau mengubah sesedikit mungkin. Pilih task yang diperlukan; jangan mengambil formality transfer sebagai tujuan default conversation | Dataset card menyatakan Apache-2.0. Namun data berasal dari beberapa corpus; provenance komponen perlu diperiksa sebelum keputusan produksi. [Catatan rilis penulis](https://github.com/vipulraheja/coedit), [diskusi lisensi yang belum memuat klarifikasi pada pemeriksaan ini](https://huggingface.co/datasets/grammarly/coedit/discussions/2) |
| [CWEB](https://github.com/SimonHFL/CWEB) | Benchmark GEC pada teks website dengan tingkat kesalahan rendah. Relevan untuk menguji kecenderungan mengoreksi kalimat yang sudah baik | Domain web, bukan speaking. Tidak menyediakan penjelasan Indonesia atau label IELTS | CC BY-NC-SA 4.0; kandidat riset tambahan, bukan prioritas akuisisi produksi |
| [C4_200M synthetic GEC](https://github.com/google-research-datasets/C4_200M-synthetic-dataset-for-grammatical-error-correction) | Edit korupsi sintetis yang diterapkan ke kalimat C4 untuk membuat pasangan salah/benar | Sangat besar, sintetis dan belum tentu menyerupai kesalahan penutur Indonesia. Pasangan kalimat perlu direkonstruksi; bukan file kecil siap impor | CC BY 4.0 yang dinyatakan repo secara spesifik mencakup corruption edits. Teks C4 harus diperoleh dan ditinjau terpisah. Bukan prioritas awal |

**Rekomendasi teknis:** CoEdIT paling langsung sesuai bentuk instruction → edit untuk prototipe. W&I+LOCNESS berguna untuk mempelajari koreksi minimal; JFLEG membantu evaluasi variasi koreksi, dalam batas nonkomersialnya. Tidak ada yang otomatis menyediakan keseluruhan paket “spoken learner sentence → koreksi minimal → penjelasan Indonesia → alasan mempertahankan gaya”. Lapisan penjelasan dan konteks lisan tetap perlu ditulis serta ditinjau untuk SpeakWE.

[ERRANT](https://github.com/chrisjbryant/errant) adalah **tool, bukan dataset atau model koreksi**. Ia menerima kalimat asli dan kalimat terkoreksi, lalu menyelaraskan serta mengklasifikasikan edit. Lisensi software yang teramati: MIT ([distribusi pengelola](https://pypi.org/project/errant/)). Tool ini dapat membantu normalisasi label, tetapi tidak membuktikan target koreksi benar dan tidak menghasilkan penjelasan pedagogis Indonesia dengan sendirinya.

## 5. Paraphrase dan alternatif yang menjaga konteks

| Kandidat | Fungsi yang tepat | Batas dan keputusan |
| --- | --- | --- |
| [CoEdIT](https://huggingface.co/datasets/grammarly/coedit) | Belajar atau menguji instruction-based rewriting dan paraphrase; relevan untuk menghasilkan kandidat alternatif | Bukan jaminan makna, intensitas, register, fakta atau preferensi pembicara selalu sama. Filter task dan audit sumber komponen; lihat catatan di atas |
| [PAWS-Wiki Labeled Final](https://github.com/google-research-datasets/paws#paws-wiki) | Menguji apakah dua kalimat setara makna meskipun kata-katanya mirip. Berisi 49.401 train, 8.000 dev dan 8.000 test. Label 1 = paraphrase, 0 = berbeda makna | **Paraphrase identification, bukan daftar kalimat “buruk → lebih bagus”.** Jangan memasukkan pasangan label 0 sebagai target rewrite positif. Domain Wikipedia bukan dialog learner. Bagian noisy/unlabeled disimpan terpisah bila suatu saat dipakai |

Lisensi [repo PAWS](https://github.com/google-research-datasets/paws/blob/master/LICENSE) menyatakan dataset boleh digunakan untuk tujuan apa pun dan meminta pengakuan sumber Google. Catat ketentuan beserta asal Wikipedia pada snapshot yang akan diambil. **PAWS-QQP berbeda:** repo menyatakan raw data tidak didistribusikan langsung karena lisensi QQP; jangan menganggap keputusan PAWS-Wiki otomatis berlaku pada QQP.

**Rekomendasi:** CoEdIT untuk kandidat perubahan; PAWS-Wiki sebagai salah satu uji penjaga makna. PAWS tidak cukup untuk menguji nada sopan, register, intensitas atau kecocokan idiom. Tambahkan contoh asli SpeakWE yang menguji negasi, angka, waktu, siapa melakukan apa, sikap pembicara dan konteks pemakaian.

Contoh rancangan **asli SpeakWE, bukan baris yang diambil dari dataset**:

```text
Grammar:
  input: He go to campus every day.
  minimal correction: He goes to campus every day.
  alasan: Subjek he memerlukan goes pada present simple.

Paraphrase:
  input: The café is near my apartment.
  kandidat diterima: The café is close to my apartment.
  kandidat ditolak: The café is inside my apartment.
  alasan penolakan: Lokasi berubah dari dekat menjadi di dalam.

Pertahankan kalimat yang sudah tepat:
  question: Do you enjoy cooking?
  answer: Yes, I do.
  grammar action: no change
  coaching terpisah: Boleh ajak memberi alasan; jawaban singkat ini bukan
                    otomatis kesalahan grammar.
```

Record grammar usulan: `context`, `original`, `minimal_correction`, `edit_spans`, `error_type`, `explanation_id`, `acceptable_alternatives`, `no_change`, `source`, `license`, `review_status`.

Record paraphrase usulan: `context`, `original`, `candidate`, `meaning_preserved`, `changed_dimension`, `register`, `reason_id`, `recommendation_type`, `source`, `license`, `review_status`. Bedakan perbaikan grammar dari alternatif gaya; jangan menyebut semua kalimat asli salah. Sisihkan set uji berdasarkan sumber/kelompok kalimat sebelum membuat variasi, agar versi paraphrase dari kalimat sama tidak bocor ke train dan test.

## 1. Bank pertanyaan IELTS

### Sumber resmi yang dapat dibuka sekarang

1. **[IELTS.org — Speaking Sample Tasks, PDF Part 1–3](https://ielts.org/cdn/ielts-sample-tests/ielts-speaking-sample-tasks-2023.pdf)**. Acuan langsung untuk bentuk pertanyaan, cue card dan diskusi. Ini contoh resmi, bukan klaim kumpulan soal aktif lengkap.
2. **[British Council — Free IELTS Speaking practice](https://takeielts.britishcouncil.org/prepare/ielts-free-practice-mock-tests/academic/speaking)**. Portal materi contoh resmi; tersedia pula materi persiapan tambahan melalui IELTS Ready sesuai akses akun/pemesanan. Jangan menyebut angka tes lintas skill sebagai jumlah set Speaking saja.
3. **[IDP — IELTS Speaking practice tests](https://ielts.idp.com/prepare/all-test-types/speaking/practice-test)**. Menyediakan tautan Part 1, 2 dan 3. Halaman yang sama juga memuat IELTS Life Skills: **jangan mencampur Life Skills A1/A2/B1 dengan Speaking IELTS Part 1–3**.

Sumber resmi yang diperiksa menyediakan contoh dan materi persiapan; tidak ditemukan pada sumber-sumber tersebut bank publik lengkap yang menjamin mencakup semua soal ujian aktif.

### Referensi tambahan untuk variasi topik

- **[IELTS Liz — Part 1 Topics & Questions](https://ieltsliz.com/ielts-speaking-part-1-topics/)**: referensi pengajar independen untuk variasi tema dan ide pertanyaan, bukan sumber resmi IELTS atau jaminan soal yang akan keluar. Bedakan tulisan pengajar dari komentar peserta yang mengingat soal.
- **[IELTS Advantage — kumpulan pertanyaan PDF](https://www.ieltsadvantage.com/wp-content/uploads/2025/07/IELTS-Speaking-Questions-A-Comprehensive-Guide.pdf)**: bahan referensi variasi pertanyaan yang diterbitkan penyedia persiapan, bukan bank resmi atau izin redistribusi.

**Arah untuk database SpeakWE:** simpan contoh resmi sebagai rujukan bertautan sesuai terms. Tulis pertanyaan latihan asli berdasarkan kemampuan yang hendak dilatih dan spesifikasi format, dengan review pengajar. Tidak cukup sekadar mengganti beberapa kata dari kumpulan berhak cipta. Untuk mengimpor soal asli pihak lain ke aplikasi, perlu dasar izin yang mencakup pemakaian tersebut.

Pernyataan [hak cipta IELTS](https://ielts.org/legal/ielts-copyright-and-trade-mark-statement) membatasi materi situs pada penggunaan personal/nonkomersial dan mensyaratkan izin tertulis untuk penggunaan lain yang disebutkan. [Ketentuan IDP](https://ielts.idp.com/legal-notices) juga membatasi reproduksi/penyimpanan tanpa dasar izin. Karena itu “gratis dibuka” tidak dicatat sebagai “dataset bebas dimasukkan ke aplikasi”. Pada pekerjaan ini tidak dilakukan impor soal pihak ketiga.

Struktur bank usulan:

```text
question_id, mode, part, topic, prompt, cue_card_points,
linked_part2_id, followup_function, origin, source_url,
license_or_permission, author, review_status, version
```

Part 2 dan Part 3 perlu terhubung secara tema. [Format IELTS resmi](https://ielts.org/take-a-test/test-types/ielts-academic-test/ielts-academic-format-speaking) menjelaskan diskusi Part 3 mengembangkan topik Part 2 ke bahasan yang lebih umum/abstrak. Untuk mock full test, randomisasi dilakukan pada set yang masuk akal, bukan mencampur tiga bagian yang sama sekali tidak berkaitan. Part 1 boleh mencakup beberapa topik familiar dan tidak harus satu tema dengan Part 2–3.

Pertanyaan latihan baru diberi `origin: SpeakWE_original_IELTS_style`, bukan `official_question`, `actual_exam` atau `predicted_exam`. Jangan menganggap level CEFR dapat menetapkan “soal band 9”; kualitas performa dinilai dari jawaban dalam konteks tugas.

## 2. Spoken chunks dan discourse markers

- **[Cambridge English Grammar Today — Spoken English](https://dictionary.cambridge.org/grammar/british-grammar/spoken-english)**: mencakup chunks, ellipsis, hedges dan pengelolaan percakapan.
- **[Cambridge — Discourse markers](https://dictionary.cambridge.org/grammar/british-grammar/discourse-)**: referensi fungsi seperti menyambung gagasan, mengubah topik, menjelaskan ulang dan memperhalus pernyataan.
- **[Oxford OPAL spoken phrases](https://www.oxfordlearnersdictionaries.com/external/pdf/wordlists/opal/OPAL_spoken%20phrases.pdf)**: sekitar 250 frasa dalam 16 fungsi akademik menurut penerbit. Ini bahasa akademik, termasuk lecture signposting, sehingga tidak semuanya cocok untuk daily conversation atau IELTS. Pakai sebagai referensi; izin ekstraksi database produk belum ditetapkan.

Usulan kurasi SpeakWE dibagi menurut fungsi: memberi alasan, menambah contoh, membandingkan, mengakui ketidakpastian, memperbaiki ucapan, dan meminta klarifikasi. Buat contoh percakapan asli serta batas register. Jangan menyuruh pengguna menambahkan filler setiap kalimat atau menganggap banyak connector otomatis lebih lancar. Referensi tersebut bukan dump dataset yang sudah diakuisisi.

## 3. Collocations dan phrasal verbs

- **[Cambridge — Collocation](https://dictionary.cambridge.org/grammar/british-grammar/collocation)**: referensi pasangan kata dan kesalahan pemakaian, termasuk do/make, say/tell dan speak/talk. Cambridge Dictionary tetap rujukan utama untuk arti dan pola spesifik.
- **[British Council — Phrasal verbs B1–B2](https://learnenglish.britishcouncil.org/free-resources/grammar/b1-b2/phrasal-verbs)**: penjelasan separable/inseparable, termasuk penempatan objek/pronoun.
- **[British Council — Word order in phrasal verbs C1](https://learnenglish.britishcouncil.org/free-resources/grammar/c1/word-order-phrasal-verbs)**: referensi lanjutan pola urutan kata. Level halaman pengajaran tidak otomatis menjadi level setiap phrasal verb di dalamnya.

Rute yang disarankan: kurasi arti/pola dari referensi, tulis penjelasan Indonesia dan contoh SpeakWE sendiri, serta simpan bukti dan lisensi. Contoh asli dan klasifikasi editor tidak diklaim sebagai data kamus Cambridge. Tidak melakukan scrape seluruh definisi atau menyalin latihan British Council ke database.

## Urutan yang disarankan

1. Definisikan format pasangan grammar dan paraphrase yang menjaga konteks, termasuk kasus no-change dan kandidat yang harus ditolak.
2. Untuk prototipe, evaluasi CoEdIT sebagai sumber kandidat setelah audit komponen data; gunakan PAWS-Wiki untuk salah satu pengujian makna. Pisahkan benchmark NC dari jalur produksi.
3. Susun blueprint pertanyaan asli dari format resmi: variasi Part 1, cue card Part 2 dan rangkaian Part 3 yang terhubung. Pertanyaan daily conversation dibuat terpisah agar dialog dapat lebih fleksibel.
4. Tambahkan chunks berdasarkan fungsi dan collocation/phrasal verb berdasarkan kebutuhan topik. Lakukan review bahasa lisan dan penjelasan Indonesia sebelum menandai entri siap produksi.

Dokumen ini tidak menetapkan bahwa semua sumber telah lolos untuk produk komersial, tidak melatih scorer, dan tidak mengubah status dataset vocabulary/idiom yang sudah tersedia.
