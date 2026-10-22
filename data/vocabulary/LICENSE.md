# Lisensi dan atribusi dataset vocabulary

Adaptasi gabungan SpeakWE pada `v1/` dan `v2/` dibagikan dengan **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)** untuk kontribusi adaptasinya. Ketentuan dan pemberitahuan sumber asli di bawah tetap berlaku. Penetapan ini tidak mengubah lisensi kode aplikasi SpeakWE dan tidak memberi lisensi ulang atas Cambridge Dictionary.

Lisensi: <https://creativecommons.org/licenses/by-sa/4.0/>. Teks hukum: <https://creativecommons.org/licenses/by-sa/4.0/legalcode.en>.

Perubahan oleh SpeakWE: normalisasi pencarian, ekspansi variasi ejaan yang tercantum, penggabungan headword/POS dengan preservasi seluruh klaim, deteksi konflik, penautan ke WordNet, pengelompokan kandidat makna, penambahan field status, dan ekspor JSONL/SQLite. Tidak ada endorsement dari pemilik sumber.

Perubahan v2: koreksi kelas kata dengan bukti referensi, pemisahan level per arti, penjelasan Indonesia dan contoh kalimat asli yang disusun editor AI untuk SpeakWE, serta penyaringan mutu terjemahan dari anotasi asli Wordnet Bahasa. Catatan editor AI tidak diklaim sebagai persetujuan reviewer manusia.

## CEFR-J Vocabulary Profile v1.5

The CEFR-J Wordlist Version 1.5. Compiled by **Yukio Tono, Tokyo University of Foreign Studies**. Copyright **Tono Laboratory at TUFS**.

Distribusi: <https://github.com/openlanguageprofiles/olp-en-cefrj>. Ketentuan penyedia mengizinkan penggunaan riset dan komersial tanpa biaya dengan sitasi yang tepat. Salinan ketentuan terdapat pada [licenses/CEFR-J-and-Octanove-terms.md](licenses/CEFR-J-and-Octanove-terms.md). Versi dan hash artefak ada di source lock.

## Octanove Vocabulary Profile C1/C2 v1.0

Created by **Octanove Labs**, distributed by Open Language Profiles under **CC BY-SA 4.0**. <https://github.com/openlanguageprofiles/olp-en-cefrj>.

Bagian ini berbeda lisensinya dari CEFR-J. Pemberitahuan sumber dan atribusi dipertahankan; kontribusi adaptasi gabungan mengikuti CC BY-SA 4.0.

## Princeton WordNet 3.0

**WordNet 3.0 Copyright 2006 by Princeton University. All rights reserved.** Digunakan sesuai lisensi WordNet 3.0. Salinan lengkap, termasuk disclaimer, harus ikut saat mendistribusikan data yang terkait: [licenses/Princeton-WordNet-3.0.txt](licenses/Princeton-WordNet-3.0.txt).

Princeton WordNet: <https://wordnet.princeton.edu/>. Paket yang digunakan dipin dari distribusi NLTK Data, bukan model NLTK yang dilatih ulang. Definisi, contoh, domain, dan synset berasal dari WordNet; bukan teks baru yang dikarang SpeakWE.

## Wordnet Bahasa — Indonesia

**Wordnet Bahasa**, melalui Open Multilingual Wordnet, digunakan dengan lisensi MIT. Semua pemegang hak dan disclaimer dipertahankan dalam [licenses/Wordnet-Bahasa-MIT.txt](licenses/Wordnet-Bahasa-MIT.txt).

Noor, N. H. M., Sapuan, S., and Bond, F. (2011). *Creating the Open Wordnet Bahasa*. Serta Francis Bond dan David Moeljadi dan kontributor sebagaimana tercantum pada lisensi sumber. Citation asli tersedia di `sources/wordnet-bahasa-citation.bib`.

Distribusi: <https://github.com/omwn/omw-data>, bagian `wns/msa/wn-data-ind.tab`. Hanya bahasa `ind` yang diambil; data `zsm` (Malay) tidak dicampurkan sebagai Indonesian.

Open Multilingual Wordnet: Francis Bond and Ryan Foster (2013). *Linking and extending an open multilingual wordnet*. ACL 2013.

V2 juga memakai distribusi mutu asli dari [Wordnet Bahasa](https://wn-msa.sourceforge.net/eng/index.html), artefak [wn-msa-all.tab](https://svn.code.sf.net/p/wn-msa/tab/trunk/wn-msa-all.tab), berlisensi MIT yang sama. Tanggal pengambilan dan SHA-256 ada di source lock. Hanya anotasi B/I berstatus Y masuk indeks default, dengan anotasi I mengalahkan B; bahasa M (Malay-only) dikecualikan. Ini berbeda dari label `ind`/`zsm` pada distribusi OMW yang diratakan.

## Cambridge Dictionary

<https://dictionary.cambridge.org/> adalah **rujukan pemeriksaan utama** yang dipilih pengguna. Cambridge bukan pemasok bulk wordlist pada dataset impor ini. Definisi dan contoh Cambridge tidak di-scrape/disalin massal. Tautan lookup yang dihasilkan tidak menyatakan izin API, hasil verifikasi, atau endorsement Cambridge.

Catatan kurasi v2 menyimpan fakta level/POS, URL dan cakupan pemeriksaan cuplikan terindeks. Makna Indonesia, contoh dan pola ditulis untuk SpeakWE; bukan redistribusi kamus Cambridge. Lookup yang tidak menampilkan label CEFR tidak diubah menjadi label tebakan.
