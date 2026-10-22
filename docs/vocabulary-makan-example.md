# Bentuk “makan → A1–C2” yang digunakan

Rujukan utama sesuai pengguna: **Cambridge Dictionary**. Pemeriksaan di bawah berdasarkan bagian entri yang ditampilkan hasil indeks pencarian pada 22 Oktober 2026; akses halaman langsung saat itu mendapat HTTP 403. Ini contoh rancangan dan catatan referensi terbatas, bukan klaim seluruh bank sudah diperiksa atau izin menyalin database Cambridge.

## Satu makna, slot level boleh kosong

Konsep: **makan atau mengonsumsi makanan**, bukan menghabiskan sumber daya atau diliputi perasaan.

| Level | Kandidat yang didukung pemeriksaan contoh ini |
| --- | --- |
| A1 | **eat** — kata umum untuk makan |
| A2 | Kosong: belum ada padanan yang didukung pada contoh ini |
| B1 | Kosong: belum ada padanan yang didukung pada contoh ini |
| B2 | **consume** — untuk makan/minum; register formal |
| C1 | Kosong: *consume* pada arti memakai sumber daya bukan padanan yang sama dengan makan |
| C2 | Kosong: tidak diisi dengan kata sulit tanpa bukti |

Sumber fakta level dan pemisahan arti: [eat](https://dictionary.cambridge.org/dictionary/english/eat), [consume](https://dictionary.cambridge.org/us/dictionary/english/consume). Terjemahan dan catatan Indonesia di tabel adalah ringkasan yang ditulis untuk contoh ini; bukan salinan definisi/contoh Cambridge.

Entri impor CEFR-J memberi *consume* level B1 pada headword/POS. Pemeriksaan Cambridge di atas menunjukkan B2 untuk arti makan/minum dan C1 untuk arti memakai sumber daya. **Klaim wordlist umum dan level per arti tidak digabung menjadi satu fakta.** Data impor tetap menyimpan asalnya; label per arti baru boleh menjadi bagian bank tervalidasi melalui proses review yang sesuai.

## Bentuk objek yang dituju

Contoh berikut adalah ilustrasi catatan makna yang diperiksa terbatas, terpisah dari ekspor wordlist impor:

Versi aktif yang dapat dibaca program tersedia di [v2/examples/makan.json](../data/vocabulary/v2/examples/makan.json), dengan record arti, pola, contoh asli dan provenance. Pencarian: `python scripts/query-vocabulary-v2.py --id makan --pos verb`. [reference-examples/makan.json](../data/vocabulary/reference-examples/makan.json) adalah contoh awal yang tetap disimpan.

```json
{
  "concept_key": "makan-makanan",
  "meaning_id": "makan atau mengonsumsi makanan",
  "pos": "verb",
  "levels": {
    "A1": [{"word": "eat", "register": "general"}],
    "A2": [],
    "B1": [],
    "B2": [{"word": "consume", "register": "formal"}],
    "C1": [],
    "C2": []
  },
  "primary_reference": "Cambridge Dictionary",
  "reference_check_scope": "indexed_excerpt_only",
  "production_approved": false
}
```

Makna lain dibuat sebagai konsep terpisah, misalnya “menggunakan/menghabiskan sumber daya”. Jangan menambahkan label C2 pada *ingest* hanya karena terdengar teknis; bagian entri yang ditinjau menunjukkan register medis/khusus tanpa label CEFR yang terlihat. [Rujukan ingest](https://dictionary.cambridge.org/us/dictionary/english/ingest).

Kandidat mentah v1 tetap arsip. V2 sudah membaca label mutu asli Wordnet Bahasa: hanya B/I berstatus Y dari sumber masuk pencarian default, dan anotasi I mengalahkan B. Hasil *makan* turun dari 69 konsep menjadi empat (tiga verba). Lapisan arti terkurasi di atas terpisah dari konsep sumber ini. Term yang sama tetap bukan bukti bahwa semua kata dalam hasil pencarian saling menggantikan. Rincian: [panduan v2](../data/vocabulary/v2/README.md).
