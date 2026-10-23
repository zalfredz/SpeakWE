# SpeakWE

Aplikasi web untuk latihan **speaking bahasa Inggris** bersama **Mimo**, maskot axolotl yang ramah. Ada dua mode latihan:

- **Daily Conversation**: ngobrol dua arah lewat suara dengan topik sehari-hari.
- **IELTS Speaking**: latihan Part 1, Part 2, Part 3, atau simulasi tes penuh.

Fokus utamanya **fluency**. Koreksi grammar, saran vocabulary, dan idiom diberikan setelah sesi, berdasarkan bukti dari jawaban pengguna. SpeakWE tidak memberi pujian atau band tinggi tanpa bukti. Hasilnya adalah estimasi latihan, bukan nilai resmi IELTS.

> **Status (Oktober 2026): MVP IELTS berjalan lokal.** Latihan Part 1/2/3 dan full test sudah bisa dijalankan di browser. Suara Mimo masih memakai suara bawaan browser, dan penilai otomatis (Whisper + Gemini) sudah jalan tetapi belum dikalibrasi.

## Status

| Bagian | Status |
| --- | --- |
| Rancangan produk dan arsitektur | ✅ [docs/rancangan-produk.md](docs/rancangan-produk.md) |
| Aset Mimo (video, poster, font) | ✅ [dist/assets/](dist/assets/) (video masih ber-watermark; belum ada lip-sync) |
| Referensi IELTS dari PDF | ✅ Script import tersedia; hasilnya disimpan privat |
| Vocabulary A1–C2 | ✅ [9.977 entri](data/vocabulary/README.md), 132 arti terkurasi; belum direview manusia |
| Bank idiom IELTS | ✅ [60 idiom + 8 ungkapan terkait](data/language-bank/README.md); pilot |
| Riset sumber grammar, paraphrase, dan soal | ✅ [docs/grammar-paraphrase-and-question-sources.md](docs/grammar-paraphrase-and-question-sources.md) |
| Dataset audio mock test band 5–9 | ✅ 172 video + transkrip; **lokal saja**, tidak ikut repo |
| Bank soal awal: 10 topik Part 1 + 10 cue card dengan Part 3 | ✅ [data/question-bank/](data/question-bank/ielts-v1.json) (draft, perlu di-approve) |
| Web app IELTS: beranda, cek mic, ruang latihan dengan Mimo animasi, hasil sesi | ✅ [frontend/](frontend/) (suara Mimo sementara memakai suara browser) |
| Backend sesi, timer, upload jawaban, dan check-in | ✅ [backend/](backend/) (belum ada akun dan riwayat) |
| Penilai IELTS: Whisper + Gemini (ML sendiri menyusul) | ✅ [backend/ielts/assessment/](backend/ielts/assessment/) (kalibrasi dengan dataset band belum selesai) |

## Struktur repositori

```text
SpeakWE/
├── backend/              Django: bank soal, alur sesi, upload jawaban, check-in
├── frontend/             React + Vite: layar latihan dan Mimo animasi
├── docs/                 rancangan produk, strategi data, riset sumber
├── data/
│   ├── vocabulary/       dataset vocabulary CEFR A1–C2 (v2 aktif, v1 arsip)
│   ├── language-bank/    bank idiom dan ungkapan
│   ├── catalog/          registry sumber data dan lisensinya
│   ├── question-bank/    bank soal IELTS original (draft)
│   └── private/          data berhak cipta/pribadi — diabaikan Git
├── scripts/              build, query, dan validasi data
├── tests/                unit test dataset
├── dist/assets/          aset Mimo untuk web
├── Visual/, output/      bahan kerja animasi Mimo (belum aset final)
└── .openai/hosting.json  manifest hosting statis (belum dipublikasikan)
```

## Menjalankan aplikasi (lokal)

Butuh Python 3.11+ dan Node.js 18+.

```powershell
# 1. Backend Django (port 8010)
cd backend
python -m venv ..\.venv
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py seed_bank          # bank soal masuk sebagai draft
..\.venv\Scripts\python.exe manage.py createsuperuser    # untuk approve soal di /admin/
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8010

# 2. Frontend React (terminal lain)
cd frontend
npm install
npm run dev        # buka http://localhost:5173
```

Pindah laptop: lihat [docs/setup-laptop-baru.md](docs/setup-laptop-baru.md).

Penilaian otomatis (Whisper + Gemini) berjalan di terminal ketiga. Isi `backend/.env` dengan `GEMINI_API_KEY=...` (file ini diabaikan Git), lalu jalankan `..\.venv\Scripts\python.exe manage.py run_assessments` dari folder `backend`. Transkripsi memakai GPU; tanpa GPU set `WHISPER_DEVICE=cpu` (lebih lambat). Paket gratis Gemini hanya untuk rekaman uji, bukan rekaman pengguna asli.

Sesi IELTS baru bisa dimulai setelah minimal 3 topik Part 1 dan 1 cue card di-approve di `http://127.0.0.1:8010/admin/`. Mikrofon hanya jalan di `localhost` atau HTTPS. Tes: `npx vitest run` (frontend) dan `manage.py test ielts` (backend).

## Mulai cepat (data bahasa)

Butuh Python 3.11+. Script data hanya memakai library bawaan Python.

```powershell
# Bangun ulang database vocabulary lokal (file .sqlite tidak ikut repo)
python scripts/restore-vocabulary-sources.py
python scripts/build-vocabulary-v2.py

# Contoh pencarian
python scripts/query-vocabulary-v2.py --id makan --pos verb
python scripts/query-vocabulary-v2.py --level B2 --limit 20
python scripts/query-idioms.py --search "kurang sehat"
python scripts/query-idioms.py --topic travel --part 2

# Tes dan validasi
python -m unittest discover -s tests -v
python scripts/validate-vocabulary-v2.py
```

`restore-vocabulary-sources.py` memverifikasi SHA-256 setiap sumber. Kalau sumber upstream berubah, prosesnya berhenti dan file tidak diganti diam-diam.

Import referensi IELTS dari PDF milik sendiri (butuh `pip install PyMuPDF`) dijelaskan di [rancangan produk §14](docs/rancangan-produk.md#14-menjalankan-persiapan-data-lokal).

## Data privat

Folder `data/private/` dan `research/` **tidak ikut repo**. Isinya:

- referensi IELTS hasil olahan PDF yang hak redistribusinya belum jelas;
- dataset audio YouTube band 5–9 (audio, transkrip, label, skor examiner) beserta pipeline-nya. Dataset ini dipakai untuk riset dan kalibrasi, bukan untuk didistribusikan.

Clone baru tidak akan berisi data ini. Jangan memindahkan isinya ke `dist/` atau folder lain yang ikut di-commit.

## Lisensi data

Setiap dataset punya lisensinya sendiri:

- Vocabulary: adaptasi CEFR-J, Octanove (CC BY-SA 4.0), Princeton WordNet, dan Wordnet Bahasa (MIT). Lihat [data/vocabulary/LICENSE.md](data/vocabulary/LICENSE.md).
- Bank idiom: CC BY 4.0 untuk kontribusi SpeakWE. Lihat [data/language-bank/LICENSE.md](data/language-bank/LICENSE.md).

Cambridge Dictionary dipakai sebagai rujukan pemeriksaan, bukan sumber data yang disalin. SpeakWE tidak berafiliasi dengan IELTS, Cambridge, British Council, atau IDP. Lisensi kode aplikasi belum ditetapkan.

## Roadmap

1. **Prototipe UI dan audio**: Home dengan Mimo, pilih mode, izin mikrofon, rekam dan putar ulang.
2. **Daily Conversation**: backend sesi, satu jalur suara nyata, daily check-in.
3. **Hasil latihan**: transkrip, replay, coaching berbukti, rekomendasi dari bank bahasa.
4. **IELTS pilot**: Part 1–3 dan full test, evaluator API dibandingkan dengan penilaian manusia.
5. **Dataset dan ML**: model penilai sendiri, dijalankan dulu sebagai shadow model sebelum menggantikan API.

Detail kebutuhan, arsitektur, kontrak API, rancangan suara Mimo, dan kriteria selesai ada di [docs/rancangan-produk.md](docs/rancangan-produk.md).
