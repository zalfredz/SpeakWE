# Setup di laptop baru

Repo Git hanya berisi kode, dokumen, dan data yang boleh dibagikan. Bagian di bawah ini **tidak ikut repo** dan harus disalin manual (flashdisk/drive pribadi) atau dibuat ulang.

## 1. Disalin manual

| Path | Ukuran | Isi | Kalau tidak disalin |
| --- | --- | --- | --- |
| `backend/.env` | kecil | `GEMINI_API_KEY`, `HF_TOKEN` | Buat ulang; sebaiknya pakai key baru |
| `data/private/youtube-band-dataset/` | ±2,7 GB | audio, transkrip, label, skor examiner | Tidak bisa dibangun ulang dengan mudah |
| `data/private/gemini-manual-test/` | ±29 MB | paket uji manual Gemini | — |
| `data/private/ielts-reference-v1/` | kecil | referensi IELTS hasil olahan PDF | Import ulang dari PDF (rancangan produk §14) |
| `research/` | ±2 MB | catatan riset | — |
| `backend/db.sqlite3` + `backend/media/` | ±6 MB | sesi, rekaman, hasil penilaian | Opsional; lihat langkah 3 |

## 2. Dibuat ulang

```powershell
# Python 3.11+ dan Node.js 18+
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
# Whisper di GPU NVIDIA butuh juga:
.venv\Scripts\python.exe -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
# Tanpa GPU NVIDIA: tambahkan WHISPER_DEVICE=cpu ke backend\.env

cd frontend; npm install; cd ..

# Database vocabulary (.sqlite tidak ikut repo)
python scripts/restore-vocabulary-sources.py
python scripts/build-vocabulary-v2.py
```

Tools dataset/ML (diarization, kalibrasi) memakai venv terpisah. Lihat [requirements-ml.txt](../requirements-ml.txt):

```powershell
python -m venv .venv-ml
.venv-ml\Scripts\python.exe -m pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
.venv-ml\Scripts\python.exe -m pip install -r requirements-ml.txt
```

Model Whisper dan pyannote diunduh otomatis saat pertama dipakai. pyannote butuh `HF_TOKEN` yang sudah menyetujui syarat `pyannote/speaker-diarization-3.1` dan `pyannote/segmentation-3.0` di Hugging Face.

## 3. Database aplikasi

Kalau `db.sqlite3` dan `media/` disalin, lewati langkah ini. Kalau tidak:

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py seed_bank --approve
```

## 4. Cek

```powershell
cd backend; ..\.venv\Scripts\python.exe manage.py test ielts; cd ..
cd frontend; npx vitest run; cd ..
```

Lalu jalankan aplikasi seperti di [README](../README.md#menjalankan-aplikasi-lokal).
