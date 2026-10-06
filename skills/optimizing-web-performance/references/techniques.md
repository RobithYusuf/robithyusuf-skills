# Teknik Optimasi Performa Web

Setiap teknik ditulis dengan format: **kapan membantu**, **cara**, **jebakan**, dan **cara memverifikasi**. Contoh kode memakai nama generik; sesuaikan dengan framework proyek.

## Daftar isi

1. Rendering hybrid (prerender + client-rendered)
2. LCP lepas dari hydration
3. Pipeline thumbnail deterministik
4. Sumber penuh hanya saat diminta, dengan fallback
5. DOM bertahap
6. Motion terikat visibilitas
7. Cache berjenjang (nginx)
8. Font dan first paint

---

## 1. Rendering hybrid

**Kapan membantu.** HTML awal hampir kosong dan konten baru muncul setelah bundle JavaScript dieksekusi. Paling berdampak pada landing page dan halaman publik statis (docs, privacy, terms).

**Cara.**
- Prerender halaman publik yang isinya sama untuk semua pengunjung. Hasil build biasanya: `index.html` berisi konten, shell SPA (mis. `200.html`) untuk route aplikasi, dan bundle bernama hash konten.
- Route aplikasi yang bergantung pada sesi, `localStorage`, atau polling tetap client-rendered. Matikan SSR di route atau layout kelompoknya, **bukan** di root layout.
- Jangan prerender data runtime yang bisa basi (harga, kuota, stok). Lebih baik halaman itu tetap client-rendered daripada menampilkan angka build yang salah.

Contoh SvelteKit (adapter-static):

```js
// routes/+page.js (halaman publik)
export const prerender = true;
export const ssr = true;

// routes/(app)/+layout.js (kelompok route aplikasi)
export const ssr = false;
```

Padanan di framework lain: Next.js `generateStaticParams`/static export vs `'use client'` + dynamic; Nuxt `routeRules: { '/': { prerender: true }, '/app/**': { ssr: false } }`; Astro halaman statis default + island.

**Jebakan.**
- Mematikan SSR di root layout membuat konfigurasi prerender di halaman tidak efektif.
- **Membaca query string saat render** pada halaman prerender. Satu file HTML statis melayani semua query, jadi framework menolak (SvelteKit melempar `Cannot access url.search on a page with prerendering enabled`; Next.js `useSearchParams` memaksa bagian itu jatuh ke client). Ini berlaku juga untuk komponen global di root layout yang tampak tak berhubungan (modal auth, banner). Bungkus dengan guard browser (`if (browser)`) atau pindahkan ke `onMount`/`useEffect`.
- Dev server merender per-request dengan URL yang diketahui, jadi kesalahan di atas baru muncul saat build. Perubahan pada root layout atau komponen global wajib diuji dengan build produksi.
- Guard yang selamat "kebetulan" (mis. hubung-singkat `path === '/x'` yang membuat bacaan query tidak dieksekusi) bukan desain. Catat di laporan agar diperbaiki sebelum route tersebut ikut diprerender.
- Web server harus benar-benar menyajikan `index.html` untuk `/` (lihat teknik 7).

**Verifikasi.** `curl -s https://example.com/ | grep -c '<teks-hero>'` > 0, dan ukuran `/` sama dengan `/index.html`.

---

## 2. LCP lepas dari hydration

**Kapan membantu.** Konten hero sudah ada di HTML, tetapi LCP tercatat jauh setelah FCP atau setelah bundle selesai.

**Cara.** Cari ketergantungan tersembunyi pada JavaScript di elemen di atas lipatan:
- kelas animasi masuk (`reveal`, `fade-in`) yang baru dihapus oleh script;
- `opacity: 0` atau `visibility: hidden` awal pada teks/gambar hero;
- gambar hero yang `src`-nya diisi oleh JavaScript, atau memakai `loading="lazy"`.

Hapus ketergantungan tersebut untuk elemen di atas lipatan. Gambar LCP sebaiknya `loading="eager"` dan `fetchpriority="high"`. Animasi masuk boleh tetap ada untuk elemen di bawah lipatan.

**Jebakan.** Animasi `opacity` dari 0 menunda LCP walau elemennya sudah dirender, karena elemen tak terlihat tidak dihitung sebagai paint kandidat.

**Verifikasi.** Di trace, elemen LCP dan waktunya; LCP seharusnya mendekati FCP pada cache hangat.

---

## 3. Pipeline thumbnail deterministik

**Kapan membantu.** Gambar galeri/kartu dimuat dari sumber resolusi penuh untuk slot yang jauh lebih kecil (snippet di SKILL.md langkah 2 menemukannya).

**Cara.**
1. **Satu sumber daftar gambar.** Simpan daftar file di satu modul data. Markup membaca dari sana, tidak menulis nama file secara harfiah. Generator dan pemeriksa membaca modul yang sama, sehingga gambar yang tidak terdaftar tidak bisa luput.
2. **Generator saat build.** Buat turunan (WebP/AVIF) dengan nama sama di subfolder, ukuran ≈ 2× lebar tampil terbesar (untuk layar DPR 2), quality sekitar 75-80. Proses per batch kecil agar peak memory stabil.
3. **Pemeriksa yang menggagalkan rilis.** Script terpisah memastikan setiap gambar terdaftar punya turunan dengan format dan dimensi benar; exit code ≠ 0 bila tidak.
4. **Jalankan otomatis.** Pasang generator di `prebuild` dan pemeriksa di CI atau sebelum build image.
5. **Dimensi eksplisit.** `width`/`height` di elemen gambar plus `aspect-ratio` di slot CSS, supaya ruang tersedia sebelum request dimulai.

Contoh generator (Node + `sharp`):

```js
// scripts/build-thumbs.mjs
import sharp from 'sharp';
import { mkdir } from 'node:fs/promises';
import { ALL_IMAGES } from '../src/lib/gallery-data.js'; // satu sumber daftar

const SRC = 'static/assets/gallery';
const OUT = `${SRC}/thumbs`;
const MAX_W = 480, MAX_H = 600, QUALITY = 78, BATCH = 8; // 2x slot terbesar; batch kecil menjaga memori

await mkdir(OUT, { recursive: true });
for (let i = 0; i < ALL_IMAGES.length; i += BATCH) {
  await Promise.all(ALL_IMAGES.slice(i, i + BATCH).map(name =>
    sharp(`${SRC}/${name}`)
      .resize(MAX_W, MAX_H, { fit: 'inside', withoutEnlargement: true })
      .webp({ quality: QUALITY })
      .toFile(`${OUT}/${name.replace(/\.\w+$/, '.webp')}`)));
}
```

**Jebakan.**
- Nama file yang ditulis langsung di markup tidak terlihat oleh generator maupun pemeriksa. Kegagalannya senyap: tidak ada error, hanya byte berlebih yang terlihat saat dimensi natural dibandingkan dengan ukuran tampil.
- Commit hasil generator dan regenerasi di `prebuild` sekaligus aman untuk produksi, tetapi lingkungan dev/staging yang belum menjalankan generator diam-diam jatuh ke sumber penuh. Jalankan pemeriksa di semua lingkungan.
- Paket dengan binary native (`sharp`) butuh varian platform build di lockfile (mis. `linux-x64`, `linux-arm64`, `linuxmusl-*`). Lockfile yang diregenerasi di macOS bisa kehilangan varian Linux sehingga build image gagal saat deploy, bukan saat kerja harian.
- Bila script dan dependensi di-bake ke image dev sementara hanya `src/` yang di-mount, script baru menghasilkan `Script not found` sampai image di-rebuild. Gejalanya tampak seperti salah ketik.
- Seluruh folder `static/` biasanya ikut ke image. Sumber yang tidak dirujuk menambah ukuran deploy (bukan request halaman); jangan dihapus sebelum ada inventaris referensi.

**Verifikasi.** Pemeriksa lolos; di Network panel gambar kartu berasal dari path `thumbs/` dengan dimensi natural yang diharapkan; catat byte sebelum vs sesudah untuk interaksi yang sama.

---

## 4. Sumber penuh hanya saat diminta, dengan fallback

**Kapan membantu.** Halaman butuh kualitas penuh hanya pada interaksi tertentu (lightbox, zoom, unduh).

**Cara.** Kartu memakai thumbnail; URL sumber penuh disimpan di atribut data dan dipakai lightbox. Bila thumbnail hilang/rusak, handler `error` mengganti ke sumber penuh:

```html
<img src="/assets/gallery/thumbs/a.webp" data-full-src="/assets/gallery/a.jpg"
     width="480" height="600" loading="lazy" decoding="async" alt="...">
```

```js
// Satu listener capture menangkap error dari semua gambar, termasuk yang dibuat belakangan
document.addEventListener('error', e => {
  const img = e.target;
  if (img instanceof HTMLImageElement && img.dataset.fullSrc && img.src !== img.dataset.fullSrc) {
    img.src = img.dataset.fullSrc;
  }
}, true);
```

**Jebakan.** Fallback menutupi pipeline yang rusak. Ia menjaga UI, bukan pengganti pemeriksa aset.

---

## 5. DOM bertahap

**Kapan membantu.** DOM berisi ribuan elemen, dan banyak di antaranya ada di section jauh di bawah atau di mode yang belum dipilih.

**Cara.**
- Bangun konten section saat section mendekati viewport (`IntersectionObserver` dengan `rootMargin` beberapa ratus piksel, mis. `800px`), sekali saja, lalu `unobserve`.
- Mode berat (mis. "tampilkan semua") dibangun sekali saat user memilihnya; filter selanjutnya bekerja pada node yang sudah ada.
- Untuk daftar sangat panjang pertimbangkan `content-visibility: auto` + `contain-intrinsic-size`, atau virtualisasi.

```js
const io = new IntersectionObserver(([entry]) => {
  if (!entry.isIntersecting) return;
  buildSection(entry.target);
  io.unobserve(entry.target);
}, { rootMargin: '800px 0px' });
io.observe(document.querySelector('#gallery'));
```

**Jebakan.** Jangan memakai timeout global atau `requestIdleCallback` sebagai pemicu; pekerjaan jaringan dan DOM tetap menjadi beban pembukaan halaman.

**Verifikasi.** Di posisi teratas, container target kosong; setelah didekati, terisi; mode berat kosong sampai dipilih.

---

## 6. Motion terikat visibilitas

**Kapan membantu.** `document.getAnimations()` menunjukkan banyak animasi berjalan tetapi sedikit yang terlihat; trace menunjukkan forced reflow atau loop rAF terus-menerus.

**Cara.**
- **Default dijeda oleh CSS**, dan hanya kelas `ready` yang menjalankannya. Kelas `ready` aktif hanya bila (a) aset elemen sudah load/decode, (b) elemen beririsan dengan area observer, dan (c) `document.visibilityState === 'visible'`. Keluar dari area atau tab tersembunyi menjeda tanpa mengulang download.
- **Hindari saling-tunggu dengan lazy loading.** Track horizontal yang dijeda tidak pernah menggulirkan gambar `lazy` ke viewport, sehingga gambar tidak pernah dimuat dan track tidak pernah `ready`. Saat baris mendekati viewport, set semua gambarnya ke `eager`, tunggu `img.decode()`, baru tambahkan `ready`. Baris di atas lipatan mulai segera.
- **Loop rAF dan pengukuran** (`getBBox`, `getBoundingClientRect`) tidak dijalankan sebelum section terlihat, dan loop berhenti total saat section keluar atau tab tersembunyi.
- **Satu scheduler bersama** untuk efek periodik (mis. crossfade banyak kartu), bukan satu interval per elemen. Lapisan yang belum ditampilkan tidak diberi `src` sebelum giliran pertamanya.
- Section panjang dengan banyak animasi turunan: tandai dengan atribut (mis. `data-motion-section`) dan jeda turunannya saat section tidak terlihat.
- Hormati `prefers-reduced-motion`.

```css
.track { animation: scroll 40s linear infinite; animation-play-state: paused; }
.track.ready { animation-play-state: running; }
.row:hover .track { animation-play-state: paused; }
.row--reverse .track { animation-direction: reverse; } /* JANGAN pakai shorthand `animation` di sini */
@media (prefers-reduced-motion: reduce) { .track { animation: none; } }
```

```js
const update = (row, visible) => row.querySelector('.track')
  .classList.toggle('ready', visible && row.dataset.loaded === '1' && document.visibilityState === 'visible');
```

**Jebakan: invarian cascade CSS.** Properti singkat `animation` menulis ulang `animation-play-state` menjadi `running`. Bila shorthand muncul di selektor yang lebih spesifik daripada aturan jeda dasar (mis. modifier arah), aturan jeda kalah dan gerbang `ready` mati **tanpa error**: elemen tetap terlihat bergerak normal, padahal penundaan load dan jeda tab-tersembunyi tidak berlaku. Atur arah dan variasi lain dengan longhand (`animation-direction`, `animation-duration`).

**Verifikasi.** Pada elemen tanpa `ready`: `getComputedStyle(el).animationPlayState === 'paused'`. "Bergerak atau tidak" bukan indikator, karena elemen yang bergerak justru gejala bug ini. Simulasikan tab tersembunyi dan pastikan semua berhenti.

---

## 7. Cache berjenjang (nginx)

**Kapan membantu.** Cold jauh lebih lambat dari warm, dan `curl -sI` menunjukkan TTL efektif 0 atau tanpa `Cache-Control` pada aset statis.

**Cara.** Bedakan kebijakan per kelas aset:

| Kelas aset | Cache-Control | Alasan |
|---|---|---|
| Bundle bernama hash konten (`/_app/immutable/`, `/_next/static/`, `/assets/*-[hash].js`) | `public, max-age=31536000, immutable` | Isi berubah = URL berubah |
| Aset bernama stabil (gambar konten, unduhan) | `public, max-age=86400, stale-while-revalidate=604800` | Nama sama bisa menunjuk isi baru |
| HTML (halaman prerender dan shell SPA) | `no-cache` | Boleh disimpan, wajib revalidate agar bundle deploy terbaru langsung dipakai |

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;

    location / {
        index index.html;                       # WAJIB eksplisit, lihat jebakan
        try_files $uri $uri/ /200.html;          # fallback SPA untuk route aplikasi
        add_header Cache-Control "no-cache" always;
    }

    location /_app/immutable/ {
        add_header Cache-Control "public, max-age=31536000, immutable" always;
        try_files $uri =404;
    }

    location /assets/ {
        add_header Cache-Control "public, max-age=86400, stale-while-revalidate=604800" always;
        try_files $uri =404;
    }
}
```

**Jebakan.**
- **Pewarisan `add_header`.** Location yang punya `add_header` sendiri tidak mewarisi header dari level `server`. Header seperti `X-Robots-Tag: noindex` (staging) atau header keamanan harus diulang di setiap location tersebut, atau dikumpulkan dalam file `include`.
- **`index` hilang.** Banyak Dockerfile membuang `default.conf` bawaan image nginx, tempat `index` biasanya didefinisikan. Tanpa `index index.html;`, `try_files $uri $uri/ /200.html` tidak memetakan `/` ke `index.html`, sehingga homepage prerender kalah oleh shell SPA. Kegagalannya senyap: deploy sukses, `nginx -t` lolos, `/index.html` benar, status `/` tetap `200`. Bedakan lewat ukuran respons.
- Header cache hanya berlaku di web server produksi; dev server tidak mewakilinya.
- Di belakang CDN, periksa juga hit/miss dan header `Age`; CDN bisa menimpa atau mengabaikan header origin.

**Verifikasi.**

```bash
nginx -t
curl -sI https://example.com/ | grep -i cache-control                 # no-cache
curl -sI https://example.com/_app/immutable/<file>.js | grep -i cache  # immutable
curl -sI https://example.com/assets/<file>.webp | grep -i cache        # max-age + swr
```

Pada repeat view di DevTools, aset ber-hash harus dilayani dari cache tanpa request jaringan.

---

## 8. Font dan first paint

**Kapan membantu.** Stylesheet font eksternal muncul di rantai request kritis atau daftar render-blocking.

**Cara.**
- Muat stylesheet font secara non-blocking, dengan fallback tanpa JavaScript:

  ```html
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=<Font>:wght@400;700&display=swap"
        media="print" onload="this.media='all'">
  <noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=<Font>:wght@400;700&display=swap"></noscript>
  ```

- Alternatif yang lebih kuat: self-host file font (subset, WOFF2), `<link rel="preload" as="font" crossorigin>` hanya untuk weight di atas lipatan, `font-display: swap`, dan fallback yang metriknya disesuaikan (`size-adjust`, `ascent-override`) untuk menekan pergeseran.
- **Buang preconnect yang tidak dipakai** di halaman tersebut (mis. widget CAPTCHA atau SDK pihak ketiga yang hanya dibutuhkan di alur auth). Koneksi yang tidak dipakai saat landing hanya memakan slot jaringan awal.
- Batasi jumlah family dan weight.

**Jebakan.** First paint dengan system font lalu swap bisa menggeser teks. Periksa ulang CLS di desktop dan mobile setiap kali font, weight, atau copy hero berubah.

**Verifikasi.** Stylesheet font tidak lagi berada di daftar render-blocking; FCP tidak menunggu origin font; CLS tetap ≤ 0,1.
