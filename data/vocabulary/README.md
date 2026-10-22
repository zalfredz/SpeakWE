# Dataset vocabulary SpeakWE

Folder aktif: `C:\Users\Asus TUF\Downloads\SpeakWE`. Versi aktif: **[2.0.0](v2/README.md)**.

V2 sudah memperbaiki 15 kelas kata, mengonfirmasi 30 kasus kelas kata yang sebelumnya salah ditandai karena celah WordNet, menambahkan 132 arti terkurasi dengan contoh asli, dan menyaring pencarian Indonesia memakai label mutu asli Wordnet Bahasa. Tersedia 9.977 entri kata/POS dan 12.265 tautan Indonesia berstatus Y dari sumber; 127 profil multilevel tetap dipertahankan untuk review. Seluruh 9.935 baris sumber tetap tersimpan.

**Mulai dari [panduan v2](v2/README.md)** dan gunakan `python scripts/query-vocabulary-v2.py --id makan --pos verb`. Contoh hasil: [makan A1–C2](v2/examples/makan.json). Level arti yang diperiksa dipisahkan dari level wordlist. Kurasi dilakukan editor AI dengan bukti cuplikan Cambridge; belum persetujuan manusia atau verifikasi seluruh bank.

## Arsip dokumentasi v1

Semua hitungan, perintah dan status di bawah bagian ini menjelaskan **versi 1**, bukan versi aktif. Data v1 dipertahankan untuk audit dan perbandingan. Pencarian v1 masih berisi kandidat Indonesia yang belum disaring; gunakan v2 untuk pekerjaan baru.

Dataset ini sudah diisi dari sumber terbuka berizin, bukan daftar kata yang dibuat dengan menebak level. **Cambridge Dictionary menjadi rujukan pemeriksaan utama sesuai arahan pengguna. Seluruh bank belum diverifikasi terhadap Cambridge.** Label impor tetap bernama/scope wordlist sumber dan tidak diklaim sebagai label Cambridge.

## Isi dan cakupan nyata

| Isi | Jumlah |
| --- | ---: |
| Baris asli wordlist yang dipertahankan | 9.935 |
| Entri unik kata + kelas kata, termasuk variasi ejaan sumber | 9.984 |
| Bentuk kata berbeda setelah normalisasi | 8.845 |
| Entri dengan satu level wordlist tanpa konflik/flag kelas kata yang memblokir | 9.788 |
| Entri yang ditahan untuk review level/kelas kata | 196 |
| Entri dengan tautan makna Inggris WordNet | 9.374 |
| Entri dengan kandidat pasangan Indonesia dari Wordnet Bahasa | 8.049 |
| Konsep/synset WordNet keseluruhan | 117.659 |
| Inventaris tambahan Inggris WordNet: kata + kelas kata | 155.287 |
| Istilah Indonesia yang menaut ke konsep dengan kandidat berlevel | 16.355 |
| Entri rekomendasi yang disetujui melalui review manusia | 0 |

Angka inventaris 155.287 mencakup istilah majemuk, nama, kata teknis, dan kata di luar wordlist. **Sebagian besar tidak punya level CEFR.** Inventaris ini memperluas pencarian; jangan menyebutnya 155 ribu vocab berlevel A1–C2 atau seluruh bahasa Inggris.

Perbedaan jumlah baris sumber dan entri terjadi karena variasi bertanda `/` diekspansi, sedangkan headword/POS yang sama digabung dengan semua klaim aslinya tetap disimpan.

### Entri dengan satu level wordlist yang dapat diekspor

| Level sumber | Entri |
| --- | ---: |
| A1 | 1.177 |
| A2 | 1.425 |
| B1 | 2.450 |
| B2 | 2.757 |
| C1 | 1.033 |
| C2 | 946 |

“Dapat diekspor” berarti lolos pemeriksaan struktur dan konflik sumber; belum berarti sense, register, terjemahan, dan rekomendasinya telah diverifikasi.

## File yang dipakai

| File/folder | Fungsi |
| --- | --- |
| [v1/vocabulary.jsonl](v1/vocabulary.jsonl) | Entri CEFR impor utama; satu objek JSON per baris |
| [v1/by-level/](v1/by-level/) | Enam file A1–C2; mengecualikan entri dengan level null |
| [v1/vocabulary.sqlite](v1/vocabulary.sqlite) | Pencarian kata, makna, sumber, dan kandidat Indonesia secara lokal |
| [v1/english-inventory.jsonl](v1/english-inventory.jsonl) | Inventaris WordNet lebih luas; level yang tidak tersedia tetap null |
| [v1/source-claims.jsonl](v1/source-claims.jsonl) | Seluruh 9.935 baris/klaim sumber dengan identitas baris |
| [v1/review-queue.jsonl](v1/review-queue.jsonl) | 196 entri berkonflik atau bermasalah pada kelas kata |
| [v1/cambridge-review-queue.jsonl](v1/cambridge-review-queue.jsonl) | Semua entri beserta target lookup Cambridge; belum diperiksa satu per satu |
| [v1/candidates/](v1/candidates/) | Kelompok konsep/arti dan indeks Indonesia dari pemetaan sumber yang belum ditinjau |
| [v1/summary.json](v1/summary.json) | Hitungan yang dihitung oleh builder |
| [v1/qa-report.json](v1/qa-report.json) | Hasil pemeriksaan teknis dan batasnya |
| [v1/checksums.json](v1/checksums.json) | SHA-256 keluaran build |
| [sources/sources.lock.json](sources/sources.lock.json) | URL, revision, ukuran, dan SHA-256 sumber yang benar-benar diambil |
| [LICENSE.md](LICENSE.md), [licenses/](licenses/) | Lisensi adaptasi, atribusi, dan ketentuan asli |
| [../../docs/vocabulary-makan-example.md](../../docs/vocabulary-makan-example.md) | Contoh bentuk “makan → level” yang tidak memaksakan enam padanan |
| [reference-examples/makan.json](reference-examples/makan.json) | Contoh JSON makna “makan” berdasarkan pemeriksaan indeks Cambridge terbatas; terpisah dari impor wordlist |

## Bentuk data dan arti level

Satu kata mempunyai kelas kata dan dapat memiliki banyak arti. Karena itu bentuk utama adalah **headword + POS + klaim level sumber**, lalu tautan ke konsep/arti. Satu kelompok arti menyediakan slot `A1`, `A2`, `B1`, `B2`, `C1`, `C2` sebagai array. Slot yang tidak didukung sumber tetap `[]`.

Field penting:

- `entry_id`: ID stabil dari kata yang dinormalisasi dan kelas kata.
- `word`, `forms`, `pos`: kata, variasi ejaan yang benar-benar tercantum, dan kelas kata sumber.
- `cefr_level`: satu level wordlist sumber yang tidak berkonflik dan tidak terkena flag POS pemblokir; **bukan level setiap arti**.
- `cefr_levels_claimed`, `claims`: seluruh klaim level dan record asli, termasuk konflik serta catatan pembatas makna dari sumber.
- `level_scope`: selalu menjelaskan bahwa level headword/POS belum diverifikasi untuk sense.
- `sense_ids`: tautan tepat lemma/POS ke WordNet 3.0, bukan hasil model yang menebak makna.
- `quality_flags`, `review_status`: masalah sumber dan kebutuhan review.
- `recommendation_approved`: **false** untuk seluruh impor ini.
- `primary_reference`, `cambridge_review_status`, `cambridge_lookup_url`: rujukan utama dan antrean pengecekan. URL dihasilkan sebagai target lookup; keberadaan/redirect halaman belum dijamin.

Contoh: bila `abundance` menerima B1 dari satu daftar dan C2 dari daftar lain, builder mempertahankan kedua klaim dan menulis `cefr_level: null`. Builder tidak memilih level lebih tinggi/rendah secara sembarang, atau menganggap klaim tersebut pasti berlaku pada arti yang sama.

## Makna Indonesia dan Cambridge

**Jangan gunakan isi `candidates/` langsung sebagai sinonim atau terjemahan final.** Pemeriksaan sampel menemukan pemetaan Indonesia yang terlalu luas: satu istilah dapat ditempel ke beberapa makna Inggris yang berbeda atau tidak cocok. Pemetaan asli dipertahankan untuk audit, diberi status kandidat, dan belum disetujui untuk pengguna aplikasi.

Setiap kandidat harus diperiksa terhadap definisi konsep, konteks, register, dan Cambridge. Padanan yang bersifat khusus tidak otomatis menggantikan kata umum. Kata yang tidak memiliki level tidak dinaikkan ke C2 hanya karena jarang dipakai.

Percobaan membuka halaman Cambridge secara langsung pada 22 Oktober 2026 mendapat HTTP 403. Beberapa hasil indeks pencarian menampilkan bagian entri sehingga dapat dipakai untuk pemeriksaan terbatas, seperti perbedaan arti *consume*. Itu bukan pemeriksaan menyeluruh seluruh dictionary. Tidak ada scraping massal Cambridge, dump definisi/contohnya, atau klaim izin API Cambridge. [Integrasi API resmi](https://dictionary.cambridge.org/develop) dapat ditinjau jika nanti dibutuhkan.

## Cara mencari

Jalankan dari root SpeakWE, tanpa API key dan tanpa paket Python tambahan:

```powershell
python scripts/query-vocabulary.py --en eat
python scripts/query-vocabulary.py --en consume --limit 5
python scripts/query-vocabulary.py --id makan --limit 5
python scripts/query-vocabulary.py --level C2 --limit 20
```

Gunakan `--offset` untuk halaman berikutnya. Pencarian Indonesia menampilkan **kandidat mentah**, bukan jawaban terverifikasi. Untuk bentuk data konsep “makan”, lihat [contoh kandidat sumber](v1/candidates/examples/makan.json); beberapa tautannya memang perlu ditolak saat review.

SQLite dapat dibuka dengan aplikasi pembaca SQLite. Tabel `entries`, `claims`, `entry_claims`, `concepts`, `entry_senses`, `english_terms`, dan `indonesian_terms` memakai indeks serta foreign key. Contoh query:

```sql
SELECT word, pos, cefr_level FROM entries WHERE word = 'eat';
SELECT word, pos, cefr_level FROM entries WHERE cefr_level = 'C2' ORDER BY word;
```

`indonesian_terms` berisi hubungan dari sumber, belum keputusan penerjemahan yang disetujui. File SQLite lebih dari 100 MiB sehingga diabaikan oleh `.gitignore`; dapat dibuat ulang dari sumber yang dipin.

## Build ulang dan pemeriksaan

```powershell
python scripts/restore-vocabulary-sources.py
python scripts/build-vocabulary.py
python -m unittest discover -s tests -p test_vocabulary.py -v
```

Restore hanya mengambil file sumber yang hilang dari URL revision tetap dan memverifikasi hash. Build bekerja lokal, tidak memakai dictionary API, tidak memperkirakan level lewat frekuensi, dan tidak membuat terjemahan AI. Keluaran builder ditulis ulang pada folder versi; pindahkan kurasi manual ke folder terpisah agar tidak tertimpa.

Pemeriksaan memastikan integritas sumber, preservasi baris, ID unik, nilai level yang valid, konflik tidak dipaksa selesai, 117.659 konsep WordNet, tautan makna yang ada, serta integritas SQLite. Tes regresi juga melindungi alias ejaan, POS yang hilang, dan larangan menyebarkan level ke sinonim tanpa sumber.

Pemeriksaan teknis **tidak membuktikan setiap level atau terjemahan sumber benar**. Zero error untuk semua kata Inggris dan semua arti tidak dapat dijanjikan. Dataset ini menyimpan ketidakpastian agar kesalahan sumber tidak disembunyikan sebagai fakta.
