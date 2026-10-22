# Strategi data SpeakWE

Diperbarui: **22 Oktober 2026**. Folder aktif: `C:\Users\Asus TUF\Downloads\SpeakWE`.

Dokumen ini menindaklanjuti daftar sumber dari pengguna. **Vocabulary v2 sudah tersedia**: [panduan dan hitungan dataset](../data/vocabulary/v2/README.md). V1 dipertahankan sebagai arsip. Corpus audio masih inventaris; model belum dilatih dan bank belum diverifikasi menyeluruh. Metadata terstruktur tersedia di [source-registry.json](../data/catalog/source-registry.json).

Tambahan riset teks: **[grammar → koreksi, paraphrase, bank pertanyaan IELTS, spoken chunks dan collocation](grammar-paraphrase-and-question-sources.md)**. Ada 18 sumber/tool/referensi dalam [katalog](../data/catalog/text-coaching-sources.json). Ini inventaris kandidat, bukan akuisisi corpus. Audio/transkrip band 5–9 sedang dikerjakan di luar jalur ini sesuai pembagian pengguna.

## 1. Prioritas 2: bank bahasa untuk laporan

Tujuan: menunjukkan bagian jawaban yang bisa dibuat lebih tepat/natural, dengan arti Indonesia, contoh lisan asli, register, dan alasan. Utamakan manfaat bagi fluency; jangan membuat pengguna sibuk menghafal ungkapan sulit di setiap kalimat.

### Pembagian pekerjaan dan fokus aktif

Arahan pengguna: AI lain menangani audio dan transkrip. Fokus di sini adalah **vocabulary A1–C2 dan idiom IELTS Speaking**, dengan **Cambridge Dictionary sebagai rujukan pemeriksaan utama**. [Bank idiom v1](../data/language-bank/README.md) kini memuat 60 idiom + 8 ungkapan terkait, 68 pasangan contoh asli dan starter pack 15 idiom; cakupannya pilot editor AI, belum persetujuan manusia. Inventaris YouTube/corpus tetap disimpan sebagai referensi, tetapi akuisisi audio dan transkripsi bukan pekerjaan aktif di sini.

Bank teks direncanakan memiliki tiga lapisan:

| Lapisan | Isi | Kegunaan |
| --- | --- | --- |
| Vocabulary | Kata/verb beserta part-of-speech, arti tertentu, pola pemakaian, dan level bersumber | Memahami pilihan kata dan menawarkan alternatif yang sesuai |
| Expressions | Collocation, phrasal verb, idiom, connector/discourse marker, register dan contoh | Memperluas ungkapan yang natural dan sesuai maksud |
| Contoh spoken English dalam bentuk teks | Kalimat, dialog pendek, serta jawaban latihan dengan topik dan penjelasan | Mencontohkan pengembangan ide dan penggunaan ungkapan dalam konteks |

Teks contoh yang ditulis untuk bank diberi label sebagai contoh tertulis, bukan transkrip ujaran nyata. Level teks utuh tidak disimpulkan dari kata tersulitnya. Penetapan level buatan penulis/AI dicatat sebagai estimasi yang perlu review, terpisah dari label yang didukung sumber; band IELTS tetap tidak otomatis ditetapkan.

Usulan urutan kurasi: fondasi A1–A2, pengembangan jawaban B1–B2, lalu ketepatan/fleksibilitas C1–C2 pada topik yang sama. Dengan begitu rekomendasi dapat menyesuaikan kemampuan pengguna. Target 200–500 entri ungkapan tetap merupakan bagian dari bank ini, bukan jumlah seluruh kosakata A1–C2.

Bank teks mendukung laporan dan rekomendasi. Penilaian fluency/pronunciation tetap memakai jalur audio dan evaluator yang dirancang terpisah. Kini tersedia **9.977 entri headword/POS** setelah 15 koreksi kelas kata dan penggabungan entri yang sama. Seluruh 9.935 baris sumber dipertahankan; 127 profil multilevel tetap terbuka. Ada 132 arti terkurasi dengan contoh asli dan penjelasan Indonesia berdasarkan pemeriksaan terbatas cuplikan Cambridge oleh editor AI. Pemetaan default Indonesia hanya memakai 12.265 pasangan berlabel Y dari Wordnet Bahasa, bukan semua kandidat otomatis. Belum ada persetujuan produksi oleh reviewer manusia SpeakWE.

### Kandidat dan keputusan awal

| Sumber | Kegunaan | Ketentuan yang ditemukan dan keputusan SpeakWE |
| --- | --- | --- |
| CEFR-J Wordlist v1.5 melalui Open Language Profiles | Baseline level lemma/part-of-speech A1–B2 | Sudah diimpor dari revision tetap, hash dan atribusi disimpan. Penggunaan riset/komersial dengan sitasi sesuai ketentuan sumber; bukan verifikasi level setiap arti. [Sumber](https://github.com/openlanguageprofiles/olp-en-cefrj#terms-of-use) |
| Oxford 3000/5000 | Wordlist A1–B2 dan perluasan B2–C1 | Informasi tersedia untuk belajar tidak sama dengan izin ekstraksi/database produk. Tahan import sampai izin yang mencakup penggunaan SpeakWE jelas. [Cakupan](https://www.oxfordlearnersdictionaries.com/about/wordlists/oxford3000-5000), [ketentuan](https://www.oxfordlearnersdictionaries.com/terms-and-conditions) |
| English Vocabulary Profile (EVP) | Memahami konsep level per arti/frasa | Penerbit menyatakan tidak melisensikan data untuk tujuan komersial. Jangan menyalin label/definisi/contoh atau membangun database komersial dari EVP. Penggunaan referensi pun harus sesuai ketentuannya. [Pernyataan penerbit](https://englishprofile.org/?menu=contact-us), [halaman resource](https://englishprofile.org/?menu=english-vocabulary-profile) |
| Kurasi SpeakWE | Idiom, collocation, phrasal verb, discourse marker | Batch idiom sudah tersedia: 60 idiom + 8 ungkapan terkait dengan contoh/penjelasan asli, CC BY 4.0 untuk kontribusi SpeakWE. Cambridge diperiksa melalui cuplikan terindeks. Status editor AI, belum reviewer manusia; target total 200–500 tetap perluasan. |
| Octanove C1/C2 v1.0 | Mengisi celah wordlist C1/C2 | Sudah diimpor. **CC BY-SA 4.0**; adaptasi gabungan dataset mengikuti lisensi ini dengan atribusi dan pemberitahuan perubahan. Level tetap bukan label sense otomatis. [Sumber](https://github.com/openlanguageprofiles/olp-en-cefrj#terms-of-use) |
| Princeton WordNet 3.0 dan Wordnet Bahasa `ind` | Definisi/konsep Inggris dan tautan kandidat Indonesia | Sudah diambil dengan revision/hash tetap; lisensi WordNet dan MIT disertakan. Sampel pemetaan Indonesia mengandung masalah semantik sehingga seluruh pemetaan otomatis tetap kandidat, bukan terjemahan siap pakai. |
| Cambridge Dictionary | Rujukan cek utama pilihan pengguna, pada level arti dan register | Antrean lookup tersedia untuk seluruh entri. Halaman langsung mendapat 403; beberapa bagian indeks pencarian dapat diperiksa terbatas. Belum ada scraping massal, izin bulk/API, atau verifikasi menyeluruh. [Sumber](https://dictionary.cambridge.org/), [API resmi](https://dictionary.cambridge.org/develop) |

Halaman proyek CEFR-J langsung mengalami kegagalan fetch saat pemeriksaan; distribusi v1.5 diambil dari repository Open Language Profiles dengan ketentuan yang disertakan. Artefak yang diambil dan hash terdapat di [source lock](../data/vocabulary/sources/sources.lock.json). Contoh pemisahan level headword dan level arti ada pada [“makan → level”](vocabulary-makan-example.md).

### Target kurasi pertama

Usulan pembagian **200 entri**, dapat disesuaikan berdasarkan kebutuhan topik:

| Jenis | Target |
| --- | ---: |
| Collocation lisan | 70 |
| Phrasal verb | 50 |
| Idiom | 40 |
| Discourse marker/connector dengan fungsi yang jelas | 40 |
| Total | 200 |

Angka tersebut target kerja, bukan jumlah entri yang sudah ada. Prioritaskan topik rutin, kerja/belajar, keluarga, makanan, tempat, pengalaman, dan opini. Kata kerja tunggal dapat ditambahkan dari wordlist berizin sebagai jalur terpisah; jangan memaksakan 200 entri ini semuanya C1/C2.

**Realisasi batch idiom:** 68 entri dengan 33 tag topik; 60 idiom dan 8 tipe terkait yang tidak dihitung sebagai idiom inti. Ada label CEFR teramati pada 28 ungkapan/arti, sementara 40 null. Kecocokan Part 1/2/3 dan prioritas belajar merupakan keputusan editorial, bukan daftar resmi atau klaim frekuensi. Bank ini tidak memberi bonus band otomatis. Evaluator harus menilai ketepatan dan konteks, serta mempertahankan kelancaran. Lihat [katalog](../data/language-bank/idioms-v1/CATALOG.md) dan [aturan rekomendasi](../data/language-bank/idioms-v1/recommendation-policy.json).

### Field minimal per entri

| Kelompok | Isi |
| --- | --- |
| Identitas | ID stabil, bentuk ungkapan, kategori, lemma/part-of-speech bila relevan, `sense_id` |
| Makna | Arti Indonesia yang ditulis sendiri, batas makna dan konteks yang tidak cocok |
| Pemakaian | Pola grammar, register, topik, nuansa, variasi yang diperbolehkan |
| Contoh | Contoh lisan asli, contoh penggantian span, penjelasan perubahan nuansa |
| Level | `cefr_level` nullable, `level_scope` = lemma_pos/sense/phrase, sumber dan metode penetapan level |
| Provenance | Sumber, versi/hash, tanggal akses, atribusi/lisensi, asal contoh/terjemahan |
| Review | Status, penulis/reviewer, tanggal, catatan pemeriksaan bahasa dan hak penggunaan |

Jangan menyalin level dari wordlist ke semua sense sebuah kata. Jika level arti tertentu belum terbukti, simpan `cefr_level: null` pada entri sense dan simpan hasil wordlist sebagai metadata terpisah. B2–C2 adalah sasaran perluasan pilihan bahasa, bukan rumus penilaian IELTS.

### Alur penerbitan entri

```text
draft → language_review → rights_review → approved → retired/revised
```

Status ini rancangan, belum merupakan validator otomatis. Reviewer memastikan makna, register, grammar, kealamian lisan, contoh asli, sumber level, dan lisensi. Entri yang belum disetujui tidak dipakai sebagai rekomendasi terverifikasi.

Pada laporan: ambil span pengguna → pahami maksud → cari kandidat yang disetujui → periksa kesetaraan makna → tawarkan alternatif dan alasannya. Batasi saran agar tidak mengganggu latihan. Tidak perlu mengganti kalimat yang sudah baik, dan tidak ada bonus band otomatis karena satu idiom.

## 2. Corpus untuk eksperimen

### Matriks sumber

| Dataset | Tujuan eksperimen | Label/cakupan dan batas | Status penggunaan awal |
| --- | --- | --- | --- |
| Speak & Improve Corpus 2025 | Fluency/disfluency, ASR learner, eksperimen assessment holistik | Sekitar 315 jam; CEFR indikatif holistik, subset transkrip sekitar 55 jam; bukan empat band IELTS | Lisensi khusus riset/pendidikan nonkomersial. Tidak untuk produk komersial; pelepasan model/statistik turunan memerlukan persetujuan. Akses registrasi. [Sumber dan lisensi](https://researchdatasets.cambridge.org/datasets/speak-and-improve-corpus-2025) |
| speechocean762 | Baseline pronunciation dan analisis prosodi read-aloud | 5.000 kalimat, lima penilai; seluruh penutur berbahasa ibu Mandarin, separuh anak-anak. Label fonem/kata/kalimat, bukan skor IELTS conversation | CC BY 4.0, kandidat eksperimen dengan atribusi dan pencatatan perubahan. Uji ulang pada orang Indonesia dan spontaneous speech. [OpenSLR](https://openslr.org/101/), [repo penulis](https://github.com/jimbozhang/speechocean762) |
| ICNALE Spoken | Mempelajari learner Asia termasuk Indonesia; monolog/dialog dengan konteks tugas | Pilih modul dan arti labelnya. Level peserta tidak otomatis label kemampuan speaking untuk setiap rekaman. Modul spoken/written tidak boleh dicampur | Akses registrasi. Terms melarang redistribusi dan analisis ujaran interviewer. Halaman yang diperiksa tidak memberi izin komersial eksplisit: tandai belum jelas, bukan otomatis bebas atau otomatis lisensi NC tertentu. [Terms](https://language.sakura.ne.jp/icnale/index.html), [akses/modul](https://language.sakura.ne.jp/icnale/download.html) |
| L2-ARCTIC | Riset error fonem dan variasi pelafalan L2 | Dominan read speech dari 24 pembicara/6 L1; subset anotasi error. Bukan benchmark percakapan IELTS; jangan menyamakan semua aksen dengan kesalahan | CC BY-NC 4.0 dan akses melalui formulir. Tahan dari jalur model komersial tanpa izin tambahan. [Sumber dan lisensi](https://psi.engr.tamu.edu/l2-arctic-corpus/) |
| Common Voice English | Uji ASR, robustness perangkat/aksen pada subset yang sesuai | Audio dan transkrip ASR; bukan nilai fluency/IELTS. Periksa rilis, scripted vs spontaneous, metadata dan distribusi penuturnya | Common Voice dipublikasikan sebagai CC0; akses kini lewat Mozilla Data Collective. Pin release/ID dataset dan tinjau terms akses; jangan menganggap seluruh katalog Mozilla berlisensi CC0. [Katalog Common Voice](https://mozilladatacollective.com/datasets?q=common+voice), [terms platform](https://mozilladatacollective.com/terms/consumers) |

### Perbedaan yang harus dipertahankan

- CEFR holistik adalah label yang berbeda dari empat kriteria IELTS. Tidak membuat pemetaan deterministik “B2 = band tertentu”.
- Read-aloud memberi konteks teks yang sudah diketahui, berbeda dari menyusun jawaban spontan. Kemampuan mengenali error fonem tidak membuktikan kemampuan menilai coherence.
- Prompt/text reference untuk pronunciation tidak selalu sama dengan transkrip verbatim yang mempertahankan hesitation. Catat asal setiap representasi.
- Aksen yang berbeda tidak otomatis berarti tidak dapat dipahami. Evaluasi di kelompok pengguna SpeakWE sebelum membuat coaching.
- Di ICNALE Spoken Dialogue, pisahkan speaker dan patuhi larangan analisis ujaran interviewer. Akses/izin harus jelas sebelum memproses audio.
- Kumpulan contoh B2–C2 bukan pengganti audio berlabel manusia yang mencakup kemampuan lebih rendah dan kasus buruk.

### Rancangan eksperimen yang bermanfaat

1. **ASR:** gunakan subset Common Voice sesuai izin dan, sesudah haknya jelas, learner speech yang relevan. Ukur WER/CER, kesalahan pada ujaran ragu-ragu, serta hilangnya fillers/repetition. Terapkan normalisasi teks yang terdokumentasi.
2. **Pronunciation:** gunakan speechocean762 sebagai baseline sesuai label aslinya. Evaluasi per level label dan kelompok dewasa/anak; jangan mengubah skalanya langsung menjadi band IELTS.
3. **Fluency:** utamakan rekaman spontan. Jika riset Cambridge diperbolehkan untuk penggunaan yang dimaksud, eksperimen tetap terisolasi dari jalur produk. Jangan mengirim benchmark ke API tanpa memastikan persyaratan retensi/pemakaian datanya sesuai ketentuan corpus.
4. **Validasi produk:** kumpulkan audio pengguna Indonesia dengan izin yang sesuai dan penilaian empat kriteria dari manusia. Inilah kandidat utama untuk kalibrasi SpeakWE, termasuk jeda, berbagai level, noise, dan variasi perangkat.

Semua eksperimen memakai split resmi jika tersedia dan audit tumpang tindih pembicara/prompt. Training, calibration, validation, dan test harus dibedakan; test tidak dipakai untuk membuat pseudo-label lalu melatih model yang diuji pada test itu sendiri.

## 3. Akuisisi, provenance, dan pemisahan penggunaan

### Intake link YouTube dari pengguna

Status 22 Oktober 2026: **172 video unik band 5–9** sudah diunduh audionya dan ditranskripsi (faster-whisper `medium.en`, mode batched, timestamp per kata, filler dipertahankan). Semua hasil ada di `data/private/youtube-band-dataset/` dan diabaikan Git:

- `labels.csv`: `band_group` (7 mencakup 7–7.5), `band_exact` dari judul, kelompok asli pengguna, dan koreksi manual.
- `spoken_scores.csv`: skor yang diucapkan examiner atau tertulis di deskripsi. 93 video punya overall, 32 punya nilai kriteria, 15 lengkap empat kriteria. Semua overall jatuh di kelompok band yang sama dengan label.
- `pipeline.py`: metadata → audio → transkrip → label; dapat diulang.

Batas: suara examiner dan kandidat belum dipisahkan, transkrip belum diperiksa manual terhadap audio, dan label berasal dari examiner channel, bukan penilai terlatih SpeakWE. Catalog lama `youtube-band-9-candidates.json` tidak dipakai lagi.

Sebelum kandidat menjadi contoh training, periksa sumber penilaian, cakupan bagian/full test, identitas pembicara, pengulangan sesi di channel berbeda, edit/musik, spontaneous vs model answer, serta hak penggunaan. Simpan band yang diklaim terpisah dari penilaian yang sudah ditinjau. Jangan memberi empat skor kriteria berdasarkan satu angka pada judul.

Transkrip yang sudah dikumpulkan pengguna tetap dapat menjadi referensi teks dengan provenance yang sesuai. Untuk analisis fluency, audio dan transkrip verbatim bertimestamp perlu mempertahankan jeda, pengulangan, serta self-correction. Semua rekaman dari pembicara/performa yang sama dikelompokkan pada split dataset yang sama.

### Catatan akuisisi

Registry memiliki `source_id`, versi, URL, tanggal pemeriksaan, ketentuan yang teramati, status keputusan internal, tujuan label, batas penggunaan, dan `acquisition_status`. Registry adalah catatan manual; belum ada kode yang menegakkan aturan tersebut.

Sebelum data dipakai, catat artefak/commit/release tertentu, hash, bukti atribusi/lisensi, syarat akses, izin penggunaan yang dimaksud, dan lokasi privat. Saat ini `not_downloaded` berarti belum diambil oleh proyek, bukan file gagal ditemukan di seluruh komputer.

Usulan penyimpanan setelah akuisisi:

```text
data/catalog/                 metadata sumber yang boleh ditinjau tim
data/private/external/        artefak corpus; tidak di-push atau di-host publik
data/private/language-bank/   draft kurasi dan catatan reviewer
data/private/dataset-snapshots/ dataset berizin dengan split berversi
```

Lokasi privat saja tidak membuat pemakaian corpus menjadi sah. Model registry harus melacak seluruh data pelatihannya; flag nonkomersial/tidak jelas diwariskan sebagai pembatas internal rilis sampai haknya dipastikan. Menyalin bobot hasil eksperimen ke service produksi tidak menghapus asal datanya.

Tidak mengisi formulir, menyetujui perjanjian akses, mengirim email, mengunduh corpus besar, atau mengunggah data ke provider dalam pekerjaan inventaris ini.

## 4. Urutan kerja berikutnya

**Fokus aktif di sini adalah butir bank bahasa teks.** Butir corpus, audio, dan penilaian di bawah merupakan backlog/integrasi dengan pekerjaan AI lain.

1. Vocabulary v2 sudah memperbaiki 15 kelas kata dan memisahkan 132 arti terkurasi. Perluasan berikutnya bertumpu pada antrean 127 profil multilevel dan arti yang belum diperiksa, memakai Cambridge sebagai rujukan utama. Jangan menimpa klaim sumber atau menganggap lookup tanpa label sebagai bukti level.
2. Pertahankan source lock/atribusi CEFR-J, Octanove dan Wordnet Bahasa beserta mutu aslinya. V2 hanya menampilkan tautan Indonesia Y; anotasi Indonesia mengalahkan anotasi bersama. Tinjau sisa terjemahan per konsep; jangan mengubah level headword menjadi level semua arti. Bank idiom sudah berisi 68 entri pilot; perluasan menuju 200–500 ungkapan dan review rekomendasi masih backlog.
3. Pronunciation/ASR: siapkan eksperimen terpisah speechocean762 dan Common Voice setelah versi serta terms akuisisi dicatat.
4. Cambridge, ICNALE, L2-ARCTIC: pastikan penggunaan yang dimaksud cocok dengan izin sebelum mengambil/memproses datanya. Jangan menggabungkan corpus ke satu dump tanpa provenance.
5. Scoring IELTS: siapkan protokol penilaian manusia dan contoh audio berizin. Dataset publik di atas adalah bahan eksperimen komponen, bukan bukti scorer SpeakWE akurat.

Oxford/EVP tidak menjadi dependensi yang menghalangi MVP: bank dengan contoh asli dan sumber level yang berizin bisa dibangun lebih dahulu.
