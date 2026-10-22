# Bank idiom SpeakWE untuk IELTS Speaking

Versi awal sudah dibuat: **60 idiom + 8 ungkapan terkait**, dengan 68 pasang contoh asli, 33 tag topik dan starter pack 15 idiom. File berada di `Downloads\SpeakWE\data\language-bank`.

## Yang dapat dipakai sekarang

- [Katalog yang bisa dibaca langsung](idioms-v1/CATALOG.md): seluruh arti, pola, contoh, konteks, kesalahan pemakaian dan tautan Cambridge.
- [60 idiom JSONL](idioms-v1/idioms.jsonl): untuk eksperimen fitur rekomendasi.
- [Semua 68 entri JSONL](idioms-v1/expressions.jsonl): idiom dan ungkapan terkait dengan tipe yang dibedakan.
- [Starter pack](idioms-v1/starter-pack.jsonl): 15 idiom sebagai urutan belajar editorial, bukan hasil pengukuran frekuensi.
- [Topik dan pertanyaan latihan asli](idioms-v1/topics.json): tidak diklaim sebagai pertanyaan tes resmi/terbaru.
- [Aturan rekomendasi](idioms-v1/recommendation-policy.json), [ringkasan](idioms-v1/summary.json), [sumber](idioms-v1/sources.json), dan [hasil pengujian](validation-run.json).

Delapan entri terkait adalah *get the hang of something*, *on the same page*, *lend a hand*, *a double-edged sword*, *in no time*, *a breath of fresh air*, *a change of scene*, dan *down to earth*. Tipe disimpan sebagai phrase, collocation, figurative noun, atau adjective sesuai cakupan editorial/referensi; tidak semuanya dicatat sebagai idiom inti. Sebagian kamus/edisi dapat mengelompokkan ungkapan yang sama secara berbeda.

## Bentuk satu entri

Setiap entri berisi `entry_id`, `phrase`, `expression_type`, `meaning_id`, `topics`, `ielts_parts`, `register`, `pattern`, `plain_en`, `idiomatic_en`, `when_to_use_id`, `avoid_id`, `variant`, serta bukti referensi dan status review.

Contoh *under the weather*:

- Arti: sedang kurang sehat.
- Kalimat biasa: “I felt a little unwell yesterday, so I skipped my evening walk.”
- Pilihan idiomatis: “I felt a little under the weather yesterday, so I skipped my evening walk.”
- Cocok untuk kondisi badan yang kurang sehat; bukan rasa canggung atau keadaan terendam air.

Contoh *have a lot on your plate* berarti banyak urusan. Ungkapan ini tidak otomatis dapat diganti dengan *bite off more than you can chew*, yang menyatakan beban di luar kemampuan. Saran harus menjaga maksud dan intensitas pembicara.

## Rujukan dan cakupan pemeriksaan

**Cambridge Dictionary adalah rujukan utama** sesuai pilihan pengguna. Ada 68 catatan referensi untuk 68 entri. Pemeriksaan memakai bagian halaman resmi yang tersedia pada indeks pencarian, 22 Oktober 2026. Percobaan akses langsung ke salah satu halaman mendapat 403; tidak ada bypass, scraping massal atau dump definisi/contoh kamus.

**28 entri memiliki label CEFR yang terlihat pada ungkapan/arti yang sesuai; 40 tetap null.** Label tidak diisi berdasarkan kesan bahwa idiom itu sulit. *Lose track* yang lebih luas memiliki label B2 pada referensi; untuk varian khusus *lose track of time*, `cefr_level` tetap null dan fakta B2 disimpan hanya di `reference_cefr_level`. CEFR bukan band IELTS, dan contoh kalimat utuh tidak diberi level atau band dari satu ungkapan di dalamnya.

Salah satu rujukan *recharge your batteries* adalah entri bilingual Cambridge yang memuat penjelasan Inggris dan label C2 untuk istirahat/memulihkan energi. Ini dipisahkan dari *recharge* C1 yang berarti mengisi baterai listrik. Makna idiom *a breath of fresh air* yang dipilih adalah perubahan yang menyegarkan, bukan sekadar keluar mencari udara.

Penjelasan Indonesia, pasangan kalimat, pola dan catatan penggunaan disusun editor AI untuk SpeakWE. Statusnya **reference-checked pilot**, `human_reviewed: false`, `production_approved: false`. Part IELTS dan register adalah panduan editorial; bukan aturan resmi bahwa idiom tertentu hanya boleh di bagian tertentu. Tautan referensi tidak menyiratkan dukungan Cambridge terhadap SpeakWE.

## Cara mencari

Jalankan dari root SpeakWE; tidak perlu paket tambahan atau API key:

```powershell
python scripts/query-idioms.py --starter
python scripts/query-idioms.py --search "kurang sehat"
python scripts/query-idioms.py --search "break the ice"
python scripts/query-idioms.py --topic uang --part 3 --idioms-only
python scripts/query-idioms.py --topic travel --limit 20
```

Pencarian sederhana ini mencocokkan frasa, arti, varian dan topik. Ini belum pencarian semantik, detektor idiom dari audio, atau mesin penilai IELTS. Hasil pencarian berisi kandidat; kesesuaian arti tetap perlu diperiksa. `--offset` tersedia untuk pagination.

Build dan periksa:

```powershell
python scripts/build-idiom-bank.py
python -m unittest discover -s tests -p "test_idiom_bank.py" -v
```

Kurasi yang dapat diedit ada di [curation/ielts-idioms.json](curation/ielts-idioms.json) dan [curation/idiom-reference-checks.json](curation/idiom-reference-checks.json). Builder memeriksa pasangan input/referensi, ID, topik, bagian IELTS dan menulis hash hasil. Folder `idioms-v1/` adalah keluaran build; simpan perubahan kurasi pada input.

## Pemakaian untuk laporan Mimo

Setelah sesi selesai, sistem dapat memilih potongan jawaban pengguna, memeriksa maksudnya, lalu mempertimbangkan idiom yang cocok. Tampilkan potongan asli, pilihan kalimat, arti, dan alasan kecocokannya. Pemeriksaan perlu mencakup makna, intensitas, sikap, tense, pronoun dan register; jangan menambah fakta yang tidak diucapkan pengguna. Contoh buatan bank bukan bukti bahwa potongan serupa pasti memiliki maksud yang sama.

Sebagai pilihan desain produk, mulai dari maksimal 1–2 saran opsional per sesi, tanpa menyela latihan. Itu bukan kuota resmi IELTS. Jangan mewajibkan pengguna menyisipkan idiom atau memberi poin dari jumlah idiom. Jawaban sederhana yang tepat dan lancar tetap valid.

IELTS membahas ketepatan makna, gaya, collocation dan paraphrase dalam Lexical Resource; panduan idiom resminya juga mengingatkan agar idiom sesuai topik dan tidak dipaksakan/berlebihan. [Panduan idiom IELTS](https://ielts.org/news-and-insights/how-to-use-idioms-in-the-ielts-speaking-test), [kriteria Speaking](https://ielts.org/cdn/ielts-guides/ielts-speaking-key-assessment-criteria.pdf).

Bank ini belum dihubungkan ke aplikasi atau evaluator. Tidak ada skor bonus otomatis, target band per idiom, penilaian pronunciation, audio contoh, atau pengujian akurasi rekomendasi manusia. Lisensi kontribusi asli: [LICENSE.md](LICENSE.md).
