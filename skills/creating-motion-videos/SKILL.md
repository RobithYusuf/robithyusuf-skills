---
name: creating-motion-videos
description: Mengarahkan dan membangun video motion graphic dengan Remotion yang terasa seperti garapan After Effects profesional, bukan template HTML atau AI slop. Mencakup struktur cerita iklan pendek, grid ketukan musik, easing ala speed graph, motion blur, transisi whip kontinu, kamera 2.5D, tipografi kinetik, aset fotorealistis dari image generation (gpt-image lewat endpoint kompatibel OpenAI, atau Codex), mix musik, SFX, dan voice over, verifikasi still, render, dan arsip versi. Melengkapi skill resmi remotion-dev/skills yang membahas API dasar. Gunakan saat membuat atau memperbaiki video promosi, iklan Reels, TikTok, atau Shorts, explainer produk, animasi teks, atau saat animasi terasa kaku, murahan, atau kelihatan buatan AI, walau pengguna tidak menyebut skill ini. Cocok untuk permintaan seperti bikin video promosi, video iklan Reels, animasi Remotion, motion graphic keren, kayak After Effects, video produk SaaS, generate aset 3D untuk video, make a promo video, Remotion animation, motion design.
license: MIT
metadata:
  author: robithyusuf
  version: "1.0.0"
---

# Membuat Video Motion dengan Remotion

Targetnya video yang dibaca penonton sebagai hasil editor motion profesional. Remotion sudah punya skill resmi untuk API (komposisi, media, font, render); skill ini mengisi bagian yang tidak dibahas di sana: **keputusan gerak, cerita, rasa visual, aset, audio, dan alur kerja** yang membuat hasilnya konsisten.

Kesan "HTML hasil generate" hampir selalu datang dari tiga sumber, dan setiap kunci di bawah menjawab salah satunya:

| Sumber kesan murahan | Gejala | Lawannya |
|---|---|---|
| Gerak bawaan CSS | linear atau `ease`, semua elemen muncul bersamaan, layar diam total | kurva speed graph, stagger, kamera yang selalu hidup |
| Bahasa visual web | pill, badge, kartu ber-shadow, gradien ungu, layar biru polos | foto studio, material nyata, caption editorial |
| Bukti palsu | mockup HTML tiruan, metafora yang tidak terjadi di dunia nyata | screenshot dan keluaran produk asli, situasi nyata |

## Persiapan

- Skill resmi Remotion untuk API dasar: `npx skills add remotion-dev/skills` (router `remotion-best-practices`, plus `remotion-markup`, `remotion-render`, dll.). Jangan ulangi isinya di sini; baca bila butuh detail API.
- Paket proyek: `@remotion/motion-blur` dan `@remotion/noise` (plus `@remotion/bundler` dan `@remotion/renderer` untuk `stills.mjs`) dengan versi **sama persis** dengan `remotion`. Alat: `ffmpeg`, Python 3 dengan `numpy` dan `Pillow` (key chroma, contact sheet), `scipy` dan `soundfile` (ukur audio).
- Image generation (opsional), pilih salah satu:
  - Endpoint kompatibel OpenAI Images API: env `IMAGE_API_BASE_URL`, `IMAGE_API_KEY`, `IMAGE_MODEL` (default `gpt-image-2`) dan `pip install openai`. Nilainya hanya di environment atau secret manager, tidak pernah di file, prompt, log, atau commit.
  - Codex CLI dengan fitur `image_generation` aktif (cek `codex features list`).
- Starter kit: salin [assets/motion-kit/](assets/motion-kit/) ke proyek (`ease.ts`, `beat.ts`, `context.tsx` ke `src/lib/`; `Film.tsx`, `Shot.tsx`, `Type.tsx` ke `src/components/`; `stills.mjs` ke `scripts/`).

## Alur kerja

Salin checklist ini dan centang selama bekerja:

```
- [ ] 1. Brief: satu pesan, platform, durasi, bukti asli apa yang tersedia, fakta yang boleh disebut
- [ ] 2. Rencana adegan di grid ketukan, momen khas jatuh di drop
- [ ] 3. Aset: bukti asli dulu, lalu aset generatif (key, rapikan alfa)
- [ ] 4. Bangun adegan dengan motion kit, cek dalam mode draft
- [ ] 5. Still di frame kunci (draft lalu full) + contact sheet, perbaiki
- [ ] 6. Audio: musik di grid, SFX, VO, ukur level per kejadian
- [ ] 7. Render, finishing loudness, cover, arsipkan versi lama
- [ ] 8. Review akhir dengan daftar anti-slop
```

### 1. Brief

Satu video, satu pesan. Tanyakan fakta yang akan tampil (harga, angka, klaim, nama fitur) dan jangan mengarangnya; angka yang salah di iklan lebih mahal daripada adegan yang hilang. Kumpulkan bukti asli: screenshot UI resolusi 2x, keluaran produk sungguhan, data nyata. Format Reels/TikTok/Shorts: 1080 × 1920, 30 fps; 15–30 dtk untuk iklan, 60 dtk untuk explainer.

### 2. Cerita di grid ketukan

Struktur 30 dtk yang terbukti: **hook** (0–2 dtk, masalah dengan kata-kata penonton, sudah bergerak sejak frame 0) → **masalah nyata** (situasi yang benar-benar terjadi, bukan metafora) → **momen khas di drop** (transformasi yang hanya dimiliki produk ini, mis. input berubah menjadi hasil) → **bukti** (satu fitur per cut, keluaran asli) → **penawaran** (fakta saja) → **CTA** (URL + brand, cukup lama untuk dibaca).

Kunci tempo dulu, baru animasi: `BEAT = 60 / BPM × fps`, `b(k) = round(k × BEAT)`. Semua cut, judul, dan aksen jatuh di `b(k)` atau setengah ketukan. Tulis rencana adegan sebagai tabel (ketukan, frame, visual, teks layar, SFX, VO) sebelum menulis kode; template dan pola hook ada di [references/story-and-taste.md](references/story-and-taste.md).

### 3. Aset

Urutan prioritas: (1) **bukti asli**: screenshot UI kosong lalu teks yang diketik disusun ulang di atasnya dengan font UI yang sama supaya bisa dianimasikan, keluaran produk asli; (2) **aset fotorealistis hasil generate** untuk properti dan latar (objek 3D, cyclorama studio, perangkat berlayar hijau); (3) **gambar kode** hanya untuk elemen sederhana (kursor, cincin klik, garis progres).

Aset generatif: latar chroma hijau `#00B140`, tanpa teks atau logo, kalimat "fully opaque background", lalu key dengan [scripts/key_chroma.py](scripts/key_chroma.py). Resep prompt, jalur API vs Codex, dan jebakan gateway ada di [references/generative-assets.md](references/generative-assets.md). Konten contoh memakai brand fiktif; jangan tampilkan nama, logo, atau wajah pihak nyata.

### 4. Kunci gerak

Ini inti skill. Detail dan kode ada di [references/motion-techniques.md](references/motion-techniques.md); implementasinya ada di motion kit.

1. **Easing speed graph, bukan CSS.** Masuk `bezier(0.16, 1, 0.3, 1)` (cepat lalu mengendap lama), keluar `bezier(0.7, 0, 0.84, 0)`, gerak kamera `bezier(0.83, 0, 0.17, 1)`. Overshoot hanya untuk pop UI kecil. Mata membaca niat dari percepatan; kurva linear terbaca mesin.
2. **Keyframe per segmen.** Helper `keys(f, [[frame, nilai, easing], ...])` seperti keyframe AE, setiap segmen dengan easing sendiri. Lebih terkendali daripada rantai spring.
3. **Motion blur hanya di layer cepat.** `CameraMotionBlur` (6–12 sampel, shutter 180–240°) membungkus objek terbang dan kartu yang masuk; transisi whip memakai blur searah gerak. Mode draft mematikan semuanya.
4. **Whip sebagai satu pita kontinu.** Shot keluar dan shot masuk berbagi frame dan kurva yang sama, jadi sambungannya bergerak dengan satu kecepatan; blur sebanding kecepatan, pemisahan RGB tipis (maks ±9 px). Crossfade antar adegan membuat video terasa slideshow.
5. **Kamera tidak pernah diam.** Setiap shot punya dorongan pelan (skala 1,06 → 1) dan drift Perlin ≤ 6 px; kartu masuk dengan perspektif (`rotateX` dari −60°).
6. **Setiap aset hidup.** Bob + drift + "napas" kecil dengan fase sendiri per aset (amplitudo 7–10 px, rotasi < 1°). Terasa, tidak ditonton.
7. **Tipografi kinetik lewat mask.** Kata naik dari mask masing-masing dengan stagger 2–3 frame. Mask wajib menyisakan ruang ±0,36 em di bawah untuk huruf berekor (g, j, p, y) dan menyembunyikan kata sebelum/sesudah geraknya. Kata hentakan: dari skala 1,3 dengan blur yang menghilang dan tracking yang merapat.
8. **Hierarki tipografi berganti tiap adegan.** Selang-seling kiri, kanan, tengah; kontras ukuran (baris kecil lalu kata besar), kontras berat (300 vs 800), baris kecil kapital renggang. Semua judul dua baris di kiri atas adalah tanda template.
9. **Kedalaman.** Pelat foto latar + subjek + partikel depan (dekat besar dan buram, jauh kecil dan tajam, parallax), rack focus saat reveal, grain film 6–8 % blend overlay, vinyet lembut.
10. **Satu momen khas.** Satu transformasi unik produk, jatuh tepat di drop, dengan SFX hit, motion blur, dan hard cut tertutup objek yang memenuhi lensa.
11. **Waktu baca.** Teks layar bertahan ± 0,3 dtk per kata + 0,5 dtk; cut boleh cepat, teks tidak.

### 5. Verifikasi visual

Jangan menilai dari kode. Render still di frame kunci (awal, tengah, dan akhir tiap adegan, drop, CTA) dalam mode draft setengah resolusi, gabungkan dengan [scripts/contact_sheet.py](scripts/contact_sheet.py), perbaiki, lalu ulangi dengan `--full` untuk memeriksa blur dan grain:

```bash
COMP=MyVideo node scripts/stills.mjs 30 120 236 400 900     # draft, 0,5x, cepat
COMP=MyVideo node scripts/stills.mjs --full 236 900         # resolusi penuh + motion blur
python3 <skill>/scripts/contact_sheet.py out/stills out/stills/sheet.jpg
```

Periksa: huruf berekor terpotong, teks penting di bawah y ≈ 1600 (tertutup UI platform) atau terlalu dekat tepi kanan, font fallback di frame awal, frame kosong di sambungan cut, elemen yang bertabrakan, gibberish di aset generatif. Tonton render draft penuh sekali di ponsel sebelum render final.

### 6. Audio

Detail di [references/audio-and-delivery.md](references/audio-and-delivery.md). Target yang sudah teruji:

| Lapisan | Target |
|---|---|
| Master | −14 LUFS integrated, true peak −1,5 dBTP |
| Whoosh/transisi | ≥ 4 LU di bawah musik setempat (momentary), terutama di intro dan breakdown yang pelan |
| Voice over | ± 7 LU di atas musik (bed −2,5 dB selama ada VO, dip −6 dB di bawah tiap kalimat) |
| SFX kecil saat ada suara | −4 dB |
| Drop | tanpa kata, musik penuh |

Ukur per kejadian dengan [scripts/sfx_levels.py](scripts/sfx_levels.py), jangan menebak dengan telinga di speaker laptop. Untuk iterasi audio tidak perlu render ulang gambar: render audio saja (`--codec=wav`) lalu mux dengan `-c:v copy`.

### 7. Render, finishing, arsip

Render master (mis. `--crf=16`), lalu finishing: `loudnorm=I=-14:TP=-1.5:LRA=11`, AAC 48 kHz 256k, `+faststart`; versi tanpa musik (SFX saja) untuk dipasangi musik dari pustaka platform; cover dari frame yang dirancang. **Arsipkan master lama sebelum menimpa** (salin ke `out/archive/<tanggal>_<label>/`) dan beri nama baru untuk varian; pemilik sering ingin membandingkan atau menunjukkan versi lama ke tim.

### 8. Anti-slop

Tolak tanpa diminta: gradien ungu/violet, glow neon, sparkle dan lens flare, emoji, blob 3D melayang, kartu glassmorphism, badge/pill/chip gaya web sebagai label, layar biru polos, metafora "otak AI" atau metafora yang tidak terjadi di dunia nyata, garis tipis di antara label dan teks (terbaca sebagai em dash), daftar bullet di layar, em dash di copy. Pakai: UI dan keluaran asli, material nyata (kertas, kain, logam), caption editorial (nomor redup + teks), tombol CTA bila memang bahasa tombol produk. Alasan dan contoh tiap butir ada di [references/story-and-taste.md](references/story-and-taste.md).

## Jebakan umum

- **Font fallback di frame awal.** `@fontsource` memuat face secara malas; tahan render dengan `delayRender` sampai `document.fonts.load()` selesai untuk **setiap** berat/gaya yang dipakai (lihat `context.tsx` di kit).
- **Render lambat.** Motion blur mengalikan waktu render sejumlah sampel. Bungkus layer cepat saja dan sediakan prop `draft`.
- **Filter SVG beradu.** ID filter harus unik per shot, kalau tidak shot lain ikut ter-blur.
- **Teks gradien terpotong.** `background-clip: text` butuh padding untuk ekor huruf dan kemiringan italic.
- **Gateway gambar mengabaikan parameter.** `size` dan `background` bisa diabaikan; kunci rasio di teks prompt, cek kanal alfa setiap hasil.
- **Whoosh terasa keras di bagian sepi.** Level tetap yang pas di drop menonjol di intro; ukur per kejadian.
- **Komponen bersama dipakai banyak potongan.** Mengubah `Shot`/`Type` mengubah semua versi; render ulang dan cek semuanya, dan koordinasikan berkas bila ada sesi lain yang bekerja paralel.

## Rujukan

- Teknik gerak dan potongan kode: [references/motion-techniques.md](references/motion-techniques.md)
- Cerita, template adegan, tipografi, anti-slop: [references/story-and-taste.md](references/story-and-taste.md)
- Aset generatif (API kompatibel OpenAI, Codex, key chroma): [references/generative-assets.md](references/generative-assets.md)
- Musik, SFX, VO, loudness, render, arsip: [references/audio-and-delivery.md](references/audio-and-delivery.md)
- Starter kit: [assets/motion-kit/](assets/motion-kit/)
- Skrip: [scripts/gen_image.py](scripts/gen_image.py), [scripts/key_chroma.py](scripts/key_chroma.py), [scripts/contact_sheet.py](scripts/contact_sheet.py), [scripts/sfx_levels.py](scripts/sfx_levels.py)
