# Desain tahap 1: IELTS Speaking MVP

Tanggal: 22 Oktober 2026. Status: **draf untuk disetujui pengguna**.
Dokumen induk: [rancangan produk](../../rancangan-produk.md). Kalau ada yang bertentangan, dokumen ini yang berlaku untuk tahap ini.

## 1. Tujuan dan alasan

Tahap ini membangun alur **IELTS Speaking dari awal sampai laporan**, jalan di laptop pengembang. Pengguna memilih Part 1, Part 2, Part 3, atau full test. Mimo membacakan instruksi dan pertanyaan dengan suara yang lancar dan enak didengar. Pengguna menjawab lewat mikrofon. Setelah sesi selesai, sistem membuat transkrip, menilai empat kriteria IELTS dengan bukti, lalu menampilkan laporan.

Alasan IELTS dibangun duluan (keputusan pengguna): mode ini paling jelas aturannya dan paling langsung memakai data yang sudah dikumpulkan, yaitu 172 video mock test band 5–9 untuk kalibrasi penilai.

Ukuran keberhasilan tahap ini:
- Satu full test (Part 1 → 2 → 3) bisa diselesaikan di Chrome desktop tanpa error. Audio setiap jawaban tersimpan, dan laporan muncul dengan skor per kriteria **atau** status "bukti belum cukup" yang jelas.
- Suara Mimo terdengar natural, tanpa jeda atau putus di tengah kalimat.
- Penilai sudah dikalibrasi terhadap label 172 video, dan hasil perbandingannya tercatat (lihat §7).

## 2. Keputusan pengguna (bukan saran)

| Hal | Keputusan |
| --- | --- |
| Backend | **Django** (Python) |
| Frontend | **React + TypeScript (Vite)** |
| Mode pertama | **IELTS Speaking**: Part 1, 2, 3, dan full test |
| Login | **Belum ada.** Satu pengguna lokal untuk pengujian |
| Bank soal | **Campuran**: topik dan pola dari 172 transkrip mock test dijadikan inspirasi, wording-nya ditulis ulang secara original |
| Suara Mimo | **OpenAI TTS** (kualitas setara suara ChatGPT). Anggaran OpenAI: $25 |
| Penilaian | Tujuan akhir: **ML milik SpeakWE + Gemini sebagai fallback**. **Di tahap ini Gemini yang menilai** setiap sesi, sementara ML berjalan diam-diam (shadow). **Setiap keputusan Gemini disimpan untuk bahan belajar ML.** Gemini **wajib menilai sesuai temuan dan kriteria SpeakWE**, yaitu rubrik, aturan anti-penilaian murah, dan acuan dari 172 video |
| Gemini | Paket **gratis** untuk development |
| Hosting nanti | **Render + Supabase** (bukan bagian tahap ini) |

## 3. Bukan tujuan tahap ini

- Login dan akun, Daily Conversation, percakapan suara realtime, serta pertanyaan lanjutan yang dibuat AI secara langsung.
- Deployment publik, pembayaran, lip-sync, dan animasi Mimo baru.
- Penghapusan data oleh pengguna dan kebijakan retensi (dibutuhkan sebelum rilis, bukan sekarang).

## 4. Anti-tujuan (gagal walaupun secara teknis berjalan)

- Menampilkan band tanpa bukti dari jawaban, atau menebak nilai saat audio rusak/terlalu pendek.
- Mimo memuji berlebihan atau membocorkan nilai di tengah tes.
- Rekaman **pengguna asli** dikirim ke Gemini paket gratis. Data paket gratis boleh dipakai Google, jadi paket gratis hanya untuk rekaman pengembang/teman yang setuju dan data YouTube. Ini syarat wajib sebelum rilis.
- API key masuk ke kode frontend, repo, atau log.
- Data privat (`data/private/`) atau audio YouTube ikut ter-commit.

## 5. Batasan

- Laptop pengembang: Windows 11, GTX 1650 4 GB, RAM terbatas (proses berat pernah dihentikan karena RAM penuh).
- Transkripsi memakai faster-whisper lokal (`medium.en`, mode batched, word timestamps). Pipeline-nya sudah terbukti di `data/private/youtube-band-dataset/pipeline.py`.
- Paket gratis Gemini punya batas permintaan per menit/hari. Kalibrasi 172 video harus bisa dicicil dan dilanjutkan.
- Akses mikrofon di HP butuh HTTPS. Uji di HP lewat LAN perlu tunnel/sertifikat dev. Target utama tahap ini adalah Chrome desktop. Safari iPhone dan Chrome Android cukup diuji sekali sebelum tahap ini ditutup.
- Wording pertanyaan di bank harus original. Pertanyaan yang diucapkan examiner di video hanya boleh menjadi inspirasi topik.

## 6. Cara kerja

### 6.1 Bank soal

- **Isi:**
  - Part 1: topik, masing-masing berisi 3–5 pertanyaan.
  - Part 2: cue card (judul, 3–4 poin "You should say", dan satu kalimat penutup "and explain…"), ditambah 1–2 pertanyaan penutup singkat.
  - Part 3: 4–6 pertanyaan diskusi yang terikat ke tema satu cue card.
- **Status per item:** `draft` → `approved`. **Hanya item `approved` yang boleh dipakai sesi.** Review dan approve dilakukan pengguna di Django admin.
- **Provenance per item:** `original`, atau `inspired_by` dengan ID video sumber.
- **Target awal:** ±30 topik Part 1 dan ±30 cue card beserta set Part 3-nya. 46 pertanyaan dari PDF yang sudah diimpor masuk sebagai bahan Part 1. Pertanyaan yang `part: null` direview dulu.
- **Pengacakan:** dilakukan di server. Seed dan ID soal yang terpilih disimpan di sesi supaya bisa diaudit.

### 6.2 Suara Mimo

- Semua teks yang diucapkan Mimo (instruksi tetap, pertanyaan, cue card, kalimat transisi) **dibuat audionya sekali di awal** lewat OpenAI TTS, lalu disimpan sebagai file. Saat sesi, frontend hanya memutar file.
- Nama file dibentuk dari hash (teks, voice, instruksi gaya, model). Kalau teks atau gaya suara berubah, hanya file itu yang dibuat ulang. Item `draft` tidak dibuatkan audio.
- Gaya suara untuk IELTS: tenang, jelas, ramah tapi netral, kecepatan sedang. Profil suara disimpan berversi.
- **Pemilihan suara:** buat sampel 3–5 voice OpenAI dengan naskah yang sama (instruksi, pertanyaan Part 1, cue card), lalu **pengguna memilih**.
- Kalau file audio gagal diputar, teks pertanyaan ditampilkan dan sesi tetap berjalan.

### 6.3 Alur sesi (server sebagai sumber kebenaran)

Status sesi: `created → mic_check → active → finalizing → completed`. Dari `active` bisa ke `interrupted`, lalu ke `active` lagi atau `abandoned`. Status penilaian terpisah: `queued → processing → ready / partial / failed`.

| Mode | Isi |
| --- | --- |
| Part 1 | 2–3 topik, 3–5 pertanyaan per topik |
| Part 2 | Cue card tampil sebagai kartu tugas → 1 menit persiapan (boleh lebih cepat) → bicara maksimal 2 menit → Mimo menghentikan di menit ke-2 → 1–2 pertanyaan penutup |
| Part 3 | Pertanyaan diskusi dari tema cue card |
| Full test | Part 1 → Part 2 → Part 3 berurutan; Part 3 memakai tema cue card yang sama; tidak boleh melompati bagian |

- **Satu giliran = satu pertanyaan Mimo + satu rekaman jawaban.**
- **Akhir jawaban dideteksi dari hening** (keputusan pengguna, 22 Okt 2026):
  - Jawaban selesai setelah **3 detik hening**. Angka ini ada di konfigurasi.
  - Hening baru dihitung **setelah pengguna mulai bicara**.
  - Berlaku untuk Part 1, Part 3, dan Daily Conversation.
  - **Part 2 long turn tidak diakhiri oleh hening.** Jawaban berjalan sampai batas 2 menit, atau sampai pengguna mengakhirinya.
  - Risikonya, jeda mencari kata yang lebih dari 3 detik akan memotong jawaban. Angkanya dievaluasi saat uji coba.
  - Deteksi dilakukan di browser dari level suara mikrofon (Web Audio), di Chrome dan Safari.
- Ada batas aman durasi per jawaban Part 1/3 supaya rekaman tidak jalan terus kalau tombol terlupa. Angkanya diserahkan ke builder dan ditaruh di konfigurasi.
- Timer dijalankan di browser, tapi server mencatat waktu mulai dan selesai setiap giliran, lalu memvalidasinya.
- Ruang latihan **hanya berisi Mimo**: tanpa teks, timer, atau progres. Pengecualiannya:
  - **subtitle** ucapan Mimo, yang muncul hanya saat Mimo bicara dan hilang setelahnya;
  - cue card ringkas di Part 2, karena itu materi tugas;
  - tombol ikon "Akhiri sesi".

  Satu layar ini menjadi template untuk Part 1, Part 2, Part 3, dan Daily Conversation.
- Daily check-in tetap dicatat: satu per tanggal lokal (`Asia/Jakarta`), idempoten, hanya untuk sesi `completed` dengan durasi bicara yang memadai. Ambang durasinya ada di konfigurasi.

### 6.4 Rekaman

- Gunakan MediaRecorder dengan format yang dipilih lewat `isTypeSupported`. Satu file per giliran, diunggah ke backend setelah giliran selesai.
- Server menyimpan metadata (durasi, checksum, format) dan menormalisasi ke WAV 16 kHz untuk analisis tanpa mengubah tempo.
- Penyimpanan tahap ini: folder media lokal. Kodenya dibuat supaya nanti tinggal diganti ke Supabase Storage (S3-compatible) lewat konfigurasi.

### 6.5 Penilaian setelah sesi

Dijalankan sebagai **job asynchronous**: tabel job + proses worker terpisah (perintah Django). Halaman hasil memeriksa status secara berkala. Kalau penilaian gagal, sesi yang sudah selesai dan check-in-nya tetap aman.

1. **Gerbang kualitas audio.** Rekaman kosong, hening, atau terlalu pendek menghasilkan `insufficient_evidence` atau `partial`, bukan nilai.
2. **Transkripsi** faster-whisper. Transkrip verbatim disimpan: filler, pengulangan, dan word timestamps tidak dirapikan.
3. **Fitur:**
   - Audio dan waktu: rasio jeda, panjang rentang bicara, kecepatan bicara, jumlah filler, pengulangan, dan self-correction.
   - Teks: ragam kosakata dan indikator grammar.
4. **Penilai di tahap ini: Gemini.** Router tetap dibuat, tapi kebijakannya untuk tahap ini adalah "selalu Gemini". ML **selalu dijalankan dalam shadow mode**: prediksinya dicatat, tidak ditampilkan. Router baru boleh mengizinkan ML menentukan skor setelah lulus gerbang di §7.
   - **Input Gemini:** semua rekaman jawaban sesi, transkrip verbatim ber-timestamp, konteks soal, dan **paket kriteria SpeakWE** yang berversi:
     - deskriptor band resmi IELTS;
     - aturan anti-penilaian terlalu baik dari rancangan induk §6.2;
     - **acuan per band dari 172 video**: rentang fitur fluency yang teramati per `band_group` (rasio jeda, kecepatan bicara, filler per menit) dan beberapa cuplikan jawaban kandidat per band sebagai jangkar. Cuplikan diambil dari bagian kandidat hasil §7 langkah 1.
   - **Output Gemini:** JSON per kriteria berisi band, bukti, dan alasan **yang merujuk ke kriteria dan acuan tersebut**. Validator menolak output yang tidak menyertakan bukti untuk setiap band.
   - **Keputusan Gemini disimpan untuk ML.** Band per kriteria, bukti, versi paket kriteria, dan fitur yang sama dengan input ML disimpan sebagai label **silver**. Label ini dipisahkan dari label **gold** (label 172 video dan penilaian manusia). Silver boleh dipakai untuk melatih ML, tapi **tidak boleh menjadi satu-satunya dasar evaluasi** apakah ML sudah layak. Rekaman pengguna hanya masuk bahan latih kalau pengguna mengizinkan.
5. **Validasi hasil:**
   - JSON sesuai schema.
   - Band per kriteria berupa bilangan bulat 0–9.
   - Timestamp bukti berada di dalam rekaman, dan kutipan bukti benar-benar ada di transkrip.
   - Hasil yang tidak lolos validasi dibuang, lalu dicoba ulang sekali, atau statusnya ditandai `failed`.
6. **Overall** dihitung oleh server, bukan oleh Gemini. Overall hanya dihitung untuk full test dengan keempat kriteria terisi, memakai rata-rata dengan konvensi pembulatan IELTS: pecahan .25 naik ke .5, pecahan .75 naik ke bilangan bulat berikutnya. Prompt, schema, dan contoh output lengkap ada di [prompt evaluator Gemini](2026-10-22-gemini-evaluator-prompt.md). Latihan per bagian diberi label "estimasi terbatas Part X".
7. **Rekomendasi bahasa** diambil dari bank vocabulary v2 dan bank idiom yang sudah ada. Yang ditampilkan hanya alternatif yang mempertahankan maksud kalimat asli.
8. Setiap hasil disimpan dengan provenance: versi evaluator, model, prompt, rubrik, dan router.

### 6.6 Laporan

Berisi ringkasan (yang sudah baik dan hambatan terbesar), estimasi per kriteria atau status bukti belum cukup, bukti (kutipan asli + timestamp + tombol putar ulang potongan audio), 1–3 prioritas perbaikan, saran upgrade ungkapan, dan label **"Estimasi latihan SpeakWE, bukan nilai resmi IELTS"**.

### 6.7 Layar

Home (Mimo + tombol IELTS + status check-in) → Pilih latihan (Part 1/2/3/Full + estimasi durasi) → Cek mikrofon → Ruang latihan (template yang sama untuk semua mode; lihat §6.3) → Menunggu penilaian → Hasil → Riwayat (daftar sesi). Di ruang latihan, Mimo **bergerak sesuai status** memakai mesin animasi canvas yang sudah ada (`output/speakwe-mimo-demo/mimo-fullbody-engine.js`; keputusan pengguna). Status yang dipakai: `speaking`, `listening`, `thinking`, dan `ready` (diam); `encourage` dan `success` tersedia untuk nanti. **Semua tampilan Mimo di aplikasi memakai mesin ini** (keputusan pengguna, 23 Okt 2026), termasuk Beranda dan layar persiapan, bukan foto 3D atau video PixVerse. Versi mesin yang dipakai: satu ritme napas 3,6 detik untuk seluruh gerakan, kedua mata selalu berkedip bersamaan, proporsi kepala B (1,0 × 0,93), dan tangan tidak tertutup kepala. Kalau `prefers-reduced-motion` aktif, satu frame statis per status digambar ulang hanya saat status berubah.

## 7. Jalur ML (berjalan paralel, offline)

1. **Pisahkan suara examiner dan kandidat** pada 172 video, dan potong bagian feedback examiner di akhir video. Sebelum langkah ini selesai, data belum boleh dipakai untuk melatih model.
2. **Fitur yang sama dengan §6.5 langkah 3** dihitung dari bagian kandidat. Kode fiturnya dipakai bersama untuk training dan untuk aplikasi.
3. **Baseline model** memprediksi `band_group` overall. Prediksi per kriteria hanya dicoba sejauh label memungkinkan (15 video berlabel lengkap, 32 sebagian).
4. **Evaluasi** dengan validasi silang yang dikelompokkan per video/kandidat dan per channel. Laporkan MAE, persentase tebakan dalam ±0,5 dan ±1 band, serta kecenderungan terlalu murah atau terlalu ketat.
5. **Kalibrasi Gemini** pada 172 video yang sama (dicicil sesuai batas gratis), memakai paket kriteria SpeakWE yang sama dengan aplikasi. Bandingkan dengan label dan dengan ML. Hasil Gemini pada video ini juga disimpan sebagai label silver. Video yang dipakai sebagai jangkar di prompt dikecualikan dari evaluasi Gemini, supaya hasilnya tidak bocor.
6. **Gerbang ML:** angka ambangnya ditetapkan setelah baseline pertama terlihat, dan **dikonfirmasi pengguna** sebelum router mengizinkan ML menentukan skor yang tampil.

Ada pergeseran domain yang perlu dicatat di laporan evaluasi: data YouTube direkam dengan mikrofon studio dan didominasi penutur non-Indonesia, sedangkan pengguna nanti merekam lewat mikrofon HP.

## 8. Keputusan perancang (bisa dikoreksi pengguna)

- **Bahasa:** antarmuka dan laporan dalam bahasa Indonesia. Pertanyaan, kutipan jawaban, dan contoh ungkapan tetap dalam bahasa Inggris.
- **Satu panggilan Gemini per sesi.** Semua rekaman jawaban sesi dikirim sekaligus dengan penanda giliran, karena kriteria IELTS dinilai menyeluruh. Ini juga menghemat kuota gratis. Kalau total audio melebihi batas input model, panggilan dipecah per Part, lalu band kriteria digabung dengan rata-rata berbobot durasi bicara.
- **Rubrik:** deskriptor band Speaking **resmi IELTS** yang publik menjadi acuan prompt dan `rubric_version`. Rubrik dari PDF pengguna hanya dipakai sebagai pembanding.
- **Kalibrasi Gemini:** selisihnya terhadap label 172 video diukur dan dicatat. Kalau Gemini rata-rata meleset lebih dari 0,5 band ke satu arah (terlalu murah atau terlalu ketat), koreksi offset berversi diterapkan sebelum skor ditampilkan, dan dicatat di provenance. Kalau polanya tidak konsisten, skor tetap tampil dengan label estimasi, lalu masalahnya dilaporkan ke pengguna.
- **Bank soal:** builder menyusun draf original dengan transkrip sebagai inspirasi, lalu pengguna mereview di Django admin. Pembuatan draf tidak memakai anggaran API. Wording diperiksa supaya tidak sama persis dengan ucapan examiner di transkrip.
- **Syarat minimum full test bisa diuji:** 10 topik Part 1 dan 10 cue card beserta set Part 3-nya berstatus `approved`. Target ±30 tetap berlaku untuk penutupan tahap.

## 9. Diserahkan ke builder

Struktur app Django, DRF atau view biasa, library state di frontend, library audio, styling, angka batas durasi, format API rinci (mengikuti endpoint di rancangan induk §11.3 sejauh relevan), cara menjalankan worker di Windows, desain prompt Gemini, algoritma ML baseline, dan model diarization.

## 10. Yang dibutuhkan dari pengguna saat build

- API key OpenAI dan Gemini (disimpan di `.env`, tidak di-commit).
- Memilih suara Mimo dari 3–5 sampel.
- Mereview dan meng-approve bank soal di Django admin.
- Mengonfirmasi angka gerbang ML.
