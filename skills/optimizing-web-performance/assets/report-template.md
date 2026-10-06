# Performa Web: <nama-halaman>

Dokumen ini mencatat baseline, penyebab, keputusan implementasi, dan prosedur verifikasi performa
<nama-halaman> pada <app>. Ia menjadi sumber kebenaran untuk optimasi frontend berikutnya. Angka di
bawah adalah rekaman audit pada **<YYYY-MM-DD>**, bukan jaminan permanen.

## 1. Kondisi ukur

| Parameter | Nilai |
|---|---|
| Target | <https://staging.example.com/path> |
| Build | <build produksi di belakang web server / dev server (hanya untuk perilaku)> |
| Alat | <Chrome DevTools Performance / Lighthouse / WebPageTest / RUM> |
| Throttling | <Fast 4G, CPU 4×> |
| Viewport | <desktop 1280×720, mobile 390×844> |
| Cache | <dingin dan hangat> |
| Jumlah run | <n, dilaporkan median> |

Catatan pembanding: <mis. lingkungan lokal hanya membandingkan sebelum vs sesudah di lingkungan yang sama>.

## 2. Baseline (sebelum)

| Skenario | FCP | LCP | CLS | INP/TBT | Temuan utama |
|---|---:|---:|---:|---:|---|
| Desktop, cache dingin | <x> dtk | <x> dtk | <x> | <x> | <mis. N gambar, N request pending saat LCP> |
| Mobile, cache dingin | <x> dtk | <x> dtk | <x> | <x> | <...> |
| Desktop, cache hangat | <x> dtk | <x> dtk | <x> | <x> | <...> |

Sinyal pendukung:

- Cache: <TTL efektif per kelas aset>
- Rantai kritis / render-blocking: <resource dan durasinya>
- DOM: <jumlah elemen; container yang dibangun prematur>
- Animasi: <N berjalan, N terlihat; forced reflow N ms>
- Gambar: <contoh dimensi natural vs ukuran tampil>
- TTFB: <rentang sampel>

Tandai setiap angka sebagai **hasil ukur** atau **estimasi model** (mis. potensi penghematan Lighthouse).

## 3. Penyebab

| # | Penyebab | Bukti | Sumber beban |
|---|---|---|---|
| 1 | <...> | <trace / curl / snippet console> | <byte / pekerjaan dini / jalur kritis> |

## 4. Prinsip solusi

<Apa yang dikurangi (pekerjaan prematur) dan apa yang sengaja dipertahankan (fitur, kualitas yang dilihat user).>

## 5. Keputusan implementasi

Satu subbagian per teknik.

### 5.<n> <Nama teknik>

- **Mekanisme:** <apa yang diubah, di mana (path relatif di repo)>
- **Alasan:** <mengapa ini, bukan alternatif lain>
- **Trade-off:** <apa yang dikorbankan>
- **Invarian:** <aturan yang tidak boleh dilanggar agar teknik tetap bekerja, dan cara memeriksanya>
- **Perintah terkait:** <generator, pemeriksa, build>

## 6. Kebijakan cache

| Path | Cache-Control | Alasan |
|---|---|---|
| <aset ber-hash> | `public, max-age=31536000, immutable` | <...> |
| <aset bernama stabil> | `public, max-age=<n>, stale-while-revalidate=<n>` | <...> |
| <HTML> | `no-cache` | <...> |

## 7. Hasil (sesudah)

| Skenario | Sebelum | Sesudah | CLS sesudah | Catatan |
|---|---:|---:|---:|---|
| Desktop LCP, dingin | <x> dtk | <x> dtk | <x> | <median n run> |
| Mobile LCP, dingin | <x> dtk | <x> dtk | <x> | <...> |
| Byte gambar pada <interaksi> | <x> KB | <x> KB | – | <penghematan %> |

Pemeriksaan fungsional: <ringkasan hasil langkah verifikasi, mis. container tunda kosong di posisi atas,
track tanpa `ready` = `paused`, gambar dari path thumbnail dengan dimensi benar, tidak ada request gagal>.

## 8. Verifikasi wajib (untuk perubahan berikutnya)

1. <langkah, beserta nilai yang diharapkan>
2. <...>

Sesudah deploy: bandingkan ukuran `/` vs `/index.html`, cek header cache per kelas aset, lalu ulangi audit
dengan kondisi bagian 1.

## 9. Batas dan hal yang belum terbukti

- <hal yang hanya berlaku di lingkungan produksi>
- <efek CDN, latency geografis, perangkat low-end, Safari iOS, data lapangan yang belum diamati>
- <cakupan yang sengaja tidak dikerjakan dan alasannya>
- <risiko build/deploy yang diketahui>

Bila angka tetap lambat, urutan investigasi berikutnya: waterfall HTML/CSS/JS aktual → hit/miss CDN dan
`Age` → ukuran/chunk JavaScript → long task saat hydration → latency origin.

## 10. Ringkasan teknik

| # | Teknik | Mekanisme | Menyerang |
|---|---|---|---|
| 1 | <...> | <...> | <byte / pekerjaan dini / jalur kritis / ketahanan> |

Angka pada dokumen ini berasal dari lab; yang menentukan tetap Core Web Vitals lapangan sesudah rilis.
