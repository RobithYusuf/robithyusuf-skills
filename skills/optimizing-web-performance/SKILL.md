---
name: optimizing-web-performance
description: Mengukur, mendiagnosis, dan memperbaiki performa muat halaman web (landing page, situs marketing, SPA/SSR) dengan metode baseline lalu penyebab lalu teknik lalu verifikasi dengan ukuran yang sama, mencakup Core Web Vitals (LCP, CLS, INP, FCP), rendering hybrid atau prerender, pipeline thumbnail gambar, galeri dan animasi yang hanya hidup saat terlihat, header cache nginx, font yang tidak render-blocking, serta laporan performa yang jujur soal batasnya. Gunakan saat halaman terasa lambat, skor Lighthouse rendah, LCP atau CLS buruk, gambar terlalu berat, cache tidak bekerja, atau sebelum dan sesudah optimasi perlu dibuktikan dengan angka, walau pengguna tidak menyebut skill ini. Cocok untuk permintaan seperti website lambat, optimasi performa, percepat landing page, LCP tinggi, kurangi ukuran gambar, atur cache nginx, audit performa, laporan performa, speed up page load, improve Core Web Vitals, fix slow LCP, web performance audit.
license: MIT
metadata:
  author: robithyusuf
  version: "1.0.0"
---

# Mengoptimasi Performa Web

Optimasi yang baik mengurangi **pekerjaan prematur**, bukan fitur atau kualitas yang benar-benar dilihat user. Hampir semua masalah muat halaman jatuh ke salah satu dari tiga sumber beban:

| Sumber beban | Contoh gejala |
|---|---|
| **Byte yang dikirim** | Gambar resolusi penuh di slot kecil, cache TTL 0, bundle besar |
| **Pekerjaan yang terlalu dini** | Ratusan elemen DOM/gambar di luar viewport, animasi dan loop `requestAnimationFrame` yang tidak terlihat |
| **Jalur kritis yang tertahan** | CSS font render-blocking, konten hero menunggu hydration, HTML kosong yang menunggu JavaScript |

Dua pola yang hampir selalu berlaku: **tunda pekerjaan sampai ada bukti user membutuhkannya** (bukti = irisan viewport atau aksi user, bukan waktu idle atau timeout), dan **kirim ukuran yang sesuai tempat tampilnya** sambil menyimpan sumber penuh untuk saat user memintanya.

## Alur kerja

Salin checklist ini dan centang selama bekerja:

```
- [ ] 1. Tetapkan kondisi ukur yang bisa diulang
- [ ] 2. Rekam baseline (lab + sinyal pendukung)
- [ ] 3. Petakan gejala ke penyebab, urutkan menurut dampak
- [ ] 4. Terapkan teknik, masing-masing dengan pengamannya
- [ ] 5. Verifikasi fungsional (lifecycle, fallback, tanpa regresi)
- [ ] 6. Ukur ulang dengan kondisi yang SAMA, bandingkan median
- [ ] 7. Tulis laporan, termasuk batas yang belum terbukti
```

### 1. Kondisi ukur

Angka hanya bisa dibandingkan bila kondisinya identik. Catat kondisi ini di laporan:

- **Lingkungan mirip produksi**: build produksi di belakang web server sungguhan (mis. container nginx), bukan dev server. Dev server (Vite, webpack dev, `next dev`) mengirim banyak modul terpisah, tanpa header cache produksi, dan merender per-request, sehingga timing-nya tidak mewakili apa pun. Dev server boleh dipakai untuk memeriksa *perilaku*, dan hanya untuk membandingkan sebelum vs sesudah di lingkungan yang sama.
- **Throttling tetap**: mis. Fast 4G + CPU 4× slowdown di Chrome DevTools.
- **Dua profil viewport**: desktop dan mobile.
- **Cache dingin dan cache hangat**: selisih besar di antara keduanya berarti volume transfer dan kebijakan cache adalah faktor dominan; selisih kecil berarti masalahnya di render/JavaScript.
- **Tab terfokus**: pastikan `document.visibilityState === 'visible'`. Tab latar atau window yang diminimalkan bisa menghentikan callback `IntersectionObserver` dan `requestAnimationFrame`, sehingga hasil lab menyesatkan.
- **Median minimal 3 run**, bukan satu angka. Jaringan, TLS, dan CDN bervariasi.

### 2. Baseline

Rekam metrik utama dan sinyal pendukung yang menjelaskan *mengapa* angkanya begitu:

| Metrik | Ambang "baik" (p75 lapangan) |
|---|---|
| LCP | ≤ 2,5 dtk |
| INP | ≤ 200 ms |
| CLS | ≤ 0,1 |
| FCP | ≤ 1,8 dtk |
| TTFB | ≤ 0,8 dtk |

Sinyal pendukung, dijalankan di console halaman yang diuji:

```js
// Jumlah elemen DOM dan gambar
document.querySelectorAll('*').length;
document.images.length;

// Animasi yang sedang berjalan vs yang terlihat
const running = document.getAnimations().filter(a => a.playState === 'running');
const visible = running.filter(a => {
  const el = a.effect?.target; if (!el) return false;
  const r = el.getBoundingClientRect();
  return r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth;
});
[running.length, visible.length];

// Gambar yang dimensi naturalnya jauh melebihi ukuran tampil (> 2x)
[...document.images].filter(i => i.complete && i.clientWidth &&
  i.naturalWidth > i.clientWidth * devicePixelRatio * 2)
  .map(i => [i.currentSrc, `${i.naturalWidth}x${i.naturalHeight}`, `${i.clientWidth}px`]);
```

Dari sisi server:

```bash
curl -sI https://example.com/ | grep -iE 'cache-control|age|etag|content-length'
curl -sI https://example.com/<path-aset-ber-hash>.js | grep -i cache-control
curl -s -o /dev/null -w 'ttfb=%{time_starttransfer} total=%{time_total}\n' https://example.com/
```

Dari trace DevTools (panel Performance atau Lighthouse): rantai request kritis, resource render-blocking, request yang masih pending saat LCP, long task, dan forced reflow. Bila tersedia MCP DevTools, trace dan insight-nya bisa diambil lewat tool tersebut.

Tandai jelas mana **hasil ukur** dan mana **estimasi model** (mis. "potensi penghematan" dari Lighthouse). Estimasi bukan hasil sesudah perbaikan.

### 3. Penyebab

Petakan setiap temuan ke sumber beban dan teknik. Urutkan menurut dampak terukur, bukan menurut mudahnya dikerjakan.

| Temuan | Penyebab umum | Teknik |
|---|---|---|
| Cold jauh lebih lambat dari warm | Cache TTL 0 / `no-store` pada aset statis | Cache berjenjang |
| HTML awal tidak berisi konten | Seluruh halaman client-rendered | Rendering hybrid |
| LCP tercatat jauh setelah konten ada di HTML | Kelas reveal / `opacity:0` menunggu hydration | LCP lepas dari hydration |
| Gambar natural ≫ ukuran tampil | Sumber resolusi penuh di kartu/thumbnail | Pipeline thumbnail |
| DOM besar, banyak elemen di luar viewport | Semua daftar/mode dibangun saat load | DOM bertahap |
| Banyak animasi berjalan, sedikit terlihat; forced reflow | Animasi/rAF/pengukuran tanpa gerbang visibilitas | Motion terikat visibilitas |
| CSS font di rantai kritis | Stylesheet font eksternal render-blocking | Font non-render-blocking |
| CLS > 0 setelah perubahan | Gambar tanpa dimensi, swap font | Dimensi eksplisit, cek ulang CLS |

TTFB yang tinggi layak dimonitor, tetapi jangan menyalahkannya sebelum terbukti; bandingkan dulu dengan selisih cold vs warm.

### 4. Terapkan teknik

Detail tiap teknik (kapan membantu, cara, jebakan, contoh konfigurasi) ada di [references/techniques.md](references/techniques.md). Baca bagian yang relevan sebelum mengubah kode. Ringkasnya:

1. **Rendering hybrid**: prerender halaman publik statis, route aplikasi tetap client-rendered.
2. **LCP lepas dari hydration**: konten hero terlihat dari HTML tanpa menunggu JavaScript.
3. **Pipeline thumbnail deterministik**: satu sumber daftar gambar, generator saat build, pemeriksa yang menggagalkan rilis.
4. **Sumber penuh hanya saat diminta**: lightbox/zoom memakai file asli, kartu tidak.
5. **DOM bertahap**: bangun section saat didekati, bangun mode berat saat dipilih.
6. **Motion terikat visibilitas**: animasi, rAF, dan scheduler hanya hidup saat terlihat dan tab aktif.
7. **Cache berjenjang**: `immutable` untuk aset ber-hash, TTL pendek + `stale-while-revalidate` untuk aset bernama stabil, `no-cache` untuk HTML.
8. **Font non-render-blocking**: first paint dengan system font, buang preconnect yang tidak dipakai.

Setiap teknik punya pengaman wajib agar tidak berbalik menjadi bug: **dimensi gambar eksplisit** (`width`/`height` + `aspect-ratio` slot) supaya penundaan tidak menimbulkan CLS, **fallback** ke sumber penuh bila turunan hilang, dan **pemeriksa otomatis** yang menggagalkan build bila aset turunan tidak lengkap.

### 5. Verifikasi fungsional

Optimasi lifecycle sering gagal *tanpa error*. Periksa perilaku, bukan hanya angka. Sesuaikan daftar ini dengan halaman:

1. Tab terfokus, `visibilityState` = `visible`, cache bersih.
2. Response HTML mentah (`curl -s https://example.com/ | grep '<teks-hero>'`) sudah berisi konten hero.
3. Di posisi paling atas, container yang ditunda masih kosong (`el.childElementCount === 0`).
4. Elemen bergerak yang belum siap benar-benar dijeda: `getComputedStyle(el).animationPlayState === 'paused'`. Elemen yang tetap bergerak justru bisa menjadi gejala gerbang yang rusak.
5. Scroll ke section yang ditunda: konten terbangun, gambar selesai dimuat, animasi berjalan, tidak ada request gagal atau elemen yang membeku.
6. Gambar yang diminta berasal dari path turunan dengan dimensi natural yang diharapkan (Network panel atau snippet di langkah 2).
7. Mode/aksi yang memicu konten berat (filter, "tampilkan semua", lightbox) tetap bekerja.
8. Keluar dari section atau sembunyikan tab: loop dan animasi berhenti; kembali: berlanjut.
9. Ulangi di viewport mobile, periksa console dan request gagal.
10. Jalankan pemeriksa aset dan validasi konfigurasi server (mis. `nginx -t`) di container.

### 6. Ukur ulang

Sesudah deploy ke lingkungan uji:

1. **Cek dulu bahwa yang tersaji memang hasil prerender.** Bandingkan ukuran `/` dan `/index.html`:
   ```bash
   for p in / /index.html; do curl -s -o /dev/null -w "$p %{http_code} %{size_download}\n" "https://example.com$p"; done
   ```
   Keduanya harus sama. Bila `/` jauh lebih kecil, server menyajikan shell SPA; status `200` tidak membedakan keduanya.
2. Cek header cache tiap kelas aset dengan `curl -sI`.
3. Ulangi audit cold dan warm dengan kondisi langkah 1, median ≥ 3 run.

Target awal yang masuk akal: tidak ada regresi CLS, tidak ada request gambar gagal, LCP cold turun secara material, repeat view mendapat cache hit. Data lapangan (RUM / CrUX) lebih menentukan daripada satu trace lab.

Bila masih lambat, investigasi berurutan: waterfall HTML/CSS/JS aktual → hit/miss CDN dan header `Age` → ukuran dan chunk JavaScript halaman → long task saat hydration → latency origin. Jangan menebak dari spinner atau satu screenshot.

### 7. Laporan

Tulis laporan dari [assets/report-template.md](assets/report-template.md). Laporan menjadi sumber kebenaran untuk optimasi berikutnya, jadi wajib memuat: kondisi ukur, tabel sebelum/sesudah per skenario, penyebab yang dibuktikan, keputusan beserta alasan dan trade-off, invarian yang tidak boleh dilanggar, prosedur verifikasi, dan **batas**: apa yang belum terbukti (efek CDN, latency geografis, perangkat low-end, Safari iOS, data lapangan) dan apa yang sengaja tidak dikerjakan. Beri tanggal pada angka; angka lab adalah rekaman, bukan jaminan permanen.

## Jebakan yang sering lolos

- Teknik yang benar bisa mati senyap oleh konfigurasi di tempat lain: SSR dimatikan di root layout, `index` nginx hilang sehingga `/` jatuh ke fallback SPA, properti singkat `animation` mengembalikan `animation-play-state` ke `running`. Selalu verifikasi efeknya, jangan hanya kodenya.
- Kegagalan saat prerender (mis. membaca query string saat render) tidak muncul di dev server; uji perubahan pada layout/komponen global dengan build produksi.
- Mengganti gerbang visibilitas dengan `setTimeout` atau `requestIdleCallback` hanya menunda beban, tidak menghilangkannya: CPU idle tidak berarti user akan melihat section itu.
- Fallback ke sumber penuh menjaga UI tetap jalan, tetapi bisa menyembunyikan pipeline yang rusak. Pemeriksa aset tetap harus menggagalkan rilis.
