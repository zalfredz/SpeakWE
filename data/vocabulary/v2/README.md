# Vocabulary SpeakWE versi 2

Versi aktif: **2.0.0**, 22 Oktober 2026. Versi 1 tetap tersedia untuk audit. Bank ini mendukung pencarian dan eksperimen rekomendasi; belum menjadi evaluator IELTS atau database produksi aplikasi.

## Perbaikan yang sudah diterapkan

| Hasil | Jumlah |
| --- | ---: |
| Baris klaim sumber asli tetap tersimpan | 9.935 |
| Entri unik kata + kelas kata setelah koreksi/penggabungan | 9.977 |
| Koreksi kelas kata berdasarkan pemeriksaan referensi | 15 |
| Flag ketidakcocokan WordNet yang dikonfirmasi sebagai kelas kata valid di Cambridge | 30 |
| Arti dengan level spesifik, penjelasan Indonesia dan contoh kalimat asli | 132 |
| Pasangan istilah Indonesia–konsep berstatus Y dari sumber | 12.265 |
| Entri wordlist dengan setidaknya satu tautan Indonesia berstatus Y | 4.452 |
| Entri dengan beberapa profil level sumber yang tetap dipertahankan | 127 |
| Kelas kata kosong/tidak valid setelah koreksi | 0 |

Contoh koreksi: *enviable* menjadi adjective, *remonstrate* menjadi verb, dan *batter* menjadi noun sesuai catatan sumber tentang pemain pemukul. Record asal tetap ada. Entri berkurang dari 9.984 karena tujuh hasil koreksi bergabung dengan entri kata/POS yang sudah ada; bukan karena baris sumber dibuang.

Ketidakadaan suatu kelas kata di WordNet sekarang dicatat sebagai celah cakupan, bukan otomatis dianggap kesalahan. Sebanyak 30 kasus mendapatkan konfirmasi Cambridge. Kasus lain tetap menyatakan asal dan tingkat buktinya.

## Dua jenis level

**Level wordlist** berlaku pada headword/POS sebagaimana tercantum di CEFR-J atau Octanove. **Level arti** melekat pada makna tertentu yang diperiksa. Keduanya disimpan terpisah. Banyak profil sumber tidak otomatis salah: bisa berbeda tujuan atau cakupan makna. Builder tidak memilih satu secara sembarang.

| Level | Arti yang diperiksa editor AI |
| --- | ---: |
| A1 | 34 |
| A2 | 14 |
| B1 | 20 |
| B2 | 18 |
| C1 | 14 |
| C2 | 32 |

Pemeriksaan referensi mencakup upaya lookup 221 headword unik. Tidak semuanya menampilkan label CEFR pada cuplikan yang tersedia. Cambridge adalah rujukan utama; akses langsung mendapat 403 sehingga pemeriksaan terbatas pada cuplikan halaman resmi yang terindeks. Seluruh bank tidak boleh disebut sudah terverifikasi Cambridge.

`reviewer_type: AI_editor`, `pilot_ready: true` dan `production_approved: false` pada 132 arti membedakan kurasi ini dari persetujuan manusia. Penjelasan Indonesia, pola pemakaian dan contoh kalimat ditulis untuk SpeakWE; tidak ada dump definisi/contoh Cambridge.

## Terjemahan Indonesia yang lebih ketat

Pemetaan v1 yang diratakan tidak membawa label mutu asli. V2 membaca distribusi Wordnet Bahasa yang masih menyertakan bahasa dan mutu. Pencarian default hanya menerima **Y (hand-checked good menurut proyek sumber)** untuk B (bersama Indonesia/Malay) atau I (Indonesia). Anotasi I mengalahkan B, termasuk penolakan X. Malay-only M dan hasil otomatis O/M/L tidak masuk indeks default.

Ini menyusutkan pemetaan default dari 106.688 menjadi 12.265 pasangan. Label Y bukan jaminan bebas kesalahan dan bukan review manusia oleh SpeakWE. Tautan otomatis lama tetap tersedia di folder draft untuk audit; tidak tampil pada hasil pencarian default.

Contoh nyata: istilah *makan* semula menaut ke 69 konsep yang bercampur. Setelah filter sumber tinggal empat konsep, tiga di antaranya verba. Lapisan arti yang diperiksa secara terpisah mengembalikan *eat* A1 dan *consume* B2 untuk makanan. *Consume* C1 adalah penggunaan sumber daya, sehingga tidak masuk slot C1 untuk makan.

## File utama

| File | Isi |
| --- | --- |
| [reviewed-senses.jsonl](reviewed-senses.jsonl) | 132 arti dengan level, makna Indonesia, register, pola, contoh dan bukti referensi |
| [indonesian-level-matrices.jsonl](indonesian-level-matrices.jsonl) | Pencarian istilah Indonesia ke slot A1–C2 dari arti yang diperiksa |
| [examples/makan.json](examples/makan.json) | Contoh yang diminta pengguna |
| [examples/penting.json](examples/penting.json) | Beberapa nuansa makna; jangan dianggap selalu saling menggantikan |
| [lexemes.jsonl](lexemes.jsonl) | 9.977 profil kata/POS; level sumber dipisahkan dari arti |
| [sense-levels/](sense-levels/) | Ekspor A1–C2 berdasarkan arti yang diperiksa |
| [wordlist-levels/](wordlist-levels/) | Ekspor level sumber headword/POS; belum verifikasi setiap arti |
| [source-checked-translation-senses.jsonl](source-checked-translation-senses.jsonl) | Konsep dengan tautan Indonesia Y dan provenance |
| [drafts/source-translation-candidates.jsonl](drafts/source-translation-candidates.jsonl) | Pemetaan lama; bukan hasil default |
| [pos-corrections.jsonl](pos-corrections.jsonl) | Koreksi dan record asal |
| [audit-original-196.jsonl](audit-original-196.jsonl) | Nasib 196 kasus yang ditandai pada v1 |
| [remaining-level-review.jsonl](remaining-level-review.jsonl) | 127 profil multilevel; tidak dipaksa menjadi satu level |
| [summary.json](summary.json), [migration-report.json](migration-report.json) | Hitungan dan perubahan yang dihitung builder |
| [sources.lock.json](sources.lock.json), [checksums.json](checksums.json) | Hash sumber dan hasil build |
| [../curation/](../curation/) | Input kurasi yang tidak tertimpa build |
| [../v2-validation-run.json](../v2-validation-run.json) | Hasil pengujian dan pemeriksaan artefak |

Slot kosong berarti belum ada kandidat yang diperiksa di versi ini. Istilah Indonesia bisa memiliki banyak arti; pertahankan `sense_key`, makna, kelas kata, register dan pola ketika memberi saran. Tidak ada kewajiban mengisi setiap level atau mengganti kata sederhana dengan kata sulit.

## Penggunaan lokal

Dari root SpeakWE, Python standar tanpa API key:

```powershell
python scripts/query-vocabulary-v2.py --id makan --pos verb
python scripts/query-vocabulary-v2.py --id penting
python scripts/query-vocabulary-v2.py --en consume
python scripts/query-vocabulary-v2.py --en calf
python scripts/query-vocabulary-v2.py --level A1 --limit 20
python scripts/query-vocabulary-v2.py --wordlist --level C2 --limit 20
```

Default level memakai tabel `reviewed_senses`. `--wordlist` memilih profil sumber yang lebih luas. Gunakan `--offset` untuk pagination. Query Indonesia mengembalikan arti yang diperiksa serta konsep Y sumber secara terpisah. SQLite bersifat lokal dan diabaikan Git karena ukurannya; JSONL dapat dibaca tanpa database.

Build ulang dan tes:

```powershell
python scripts/restore-vocabulary-sources.py
python scripts/build-vocabulary-v2.py
python -m unittest discover -s tests -p "test_vocabulary*.py" -v
python scripts/validate-vocabulary-v2.py
```

Restore memverifikasi SHA-256. Sumber SVN kualitas memakai URL trunk, tetapi konten persisnya dipin oleh hash. Jika upstream berubah, restore menolak mismatch, tidak diam-diam mengganti data. Input kurasi berada di luar folder hasil build. V1 memiliki salinan source lock aslinya di `v1/sources.lock.json`.

## Batas yang masih ada

Seluruh 9.977 profil belum diperiksa per arti dan belum semuanya memiliki terjemahan Indonesia yang dapat ditampilkan. Sebanyak 127 profil multilevel tetap terbuka; 132 arti terkurasi menyediakan pilihan spesifik tanpa menimpa klaim asal. Belum ada persetujuan reviewer manusia SpeakWE atau evaluasi akurasi rekomendasi. Bank belum mencakup semua kata Inggris, semua arti, idiom, collocation dan phrasal verb. Lisensi dan atribusi: [../LICENSE.md](../LICENSE.md).
