# Teknik Gerak

Setiap teknik: **kenapa** (efek yang dicari), **cara** (kode singkat; versi lengkap di `assets/motion-kit/`), dan **jebakan**. Semua contoh 1080 × 1920, 30 fps.

## Daftar isi

1. Grid ketukan
2. Easing dan keyframe
3. Motion blur dan mode draft
4. Transisi whip kontinu
5. Kamera: dorongan, drift, perspektif
6. Gerak idle
7. Tipografi kinetik
8. Kedalaman: pelat foto, partikel, rack focus, grain
9. Demo UI yang meyakinkan
10. Momen khas: serah terima 2D ke render 3D
11. Katalog transisi
12. Angka waktu yang aman

---

## 1. Grid ketukan

**Kenapa.** Cut yang jatuh di ketukan terasa "diedit"; cut di sembarang frame terasa template. Grid juga membuat musik bisa diganti tanpa menggeser adegan.

**Cara.** Ukur tempo dan fase musik (lihat `audio-and-delivery.md`), lalu kunci semua waktu ke `b(k)`:

```ts
export const BEAT = (60 / BPM) * FPS;          // 14.75 frame pada 122 BPM, 30 fps
export const b = (k: number) => Math.round(k * BEAT);

<Shot name="wall" from={b(24)} dur={b(32) - b(24)} …>
const SFX = [[b(16) - 1, 'hit', 0.2], [b(28) - 1, 'fwip', 0.4]];   // SFX 1 frame sebelum event visual
```

Adegan yang dipakai ulang di versi yang lebih panjang digeser **kelipatan bar** (mis. 16 ketukan) supaya semua momen di dalamnya tetap di grid.

**Jebakan.** Membulatkan `BEAT` ke integer membuat drift ±1 frame per beberapa bar. Simpan `BEAT` pecahan, bulatkan hanya hasil `b(k)`.

## 2. Easing dan keyframe

**Kenapa.** Speed graph AE dengan influence kuat: cepat di awal, mengendap panjang. Kurva CSS (`ease`, `ease-in-out`) terlalu simetris dan langsung terbaca web.

**Cara.** `E.out` untuk masuk, `E.in` untuk keluar dan whip, `E.inOut` untuk kamera, `E.back` hanya untuk pop UI kecil. Gerak multi-tahap pakai `keys()`:

```ts
const scale = keys(f, [
  [7, 0.52],
  [10, 1.25, E.in],      // easing menuju key ini
  [13, 4.6, E.in],       // memenuhi lensa tepat di cut
  [16, 10, E.linear],
]);
const p = pr(f, 16, 32);                       // progres 0..1 dengan E.out
const y = mix(140, 0, p);
```

Objek terbang mengikuti `bez()` dan berputar mengikuti arah lintasan (`bezAngle()`), bukan bergeser lurus.

**Jebakan.** `spring()` bawaan bagus untuk UI kecil, tetapi rantai spring untuk gerak kamera sulit dikendalikan dan sering "memantul" seperti web.

## 3. Motion blur dan mode draft

**Kenapa.** Tanpa blur, objek cepat terlihat seperti tumpukan frame; dengan blur sub-frame, terasa difilmkan.

**Cara.** Bungkus hanya layer cepat:

```tsx
<MB samples={12} shutter={240}>
  <Img src={staticFile('gen/plane_front.png')} style={{transform: `scale(${scale})`}} />
</MB>
```

Sampel 6–8 untuk kartu, 10–12 untuk objek yang menembus lensa. Semua efek mahal (MB, `Grain`, blur kedalaman) membaca `useDraft()` dan mati saat `draft: true`.

**Jebakan.** Membungkus seluruh komposisi melipatgandakan waktu render untuk layer yang diam. Elemen dengan `filter: blur()` sendiri di dalam MB dihitung berkali-kali; ringankan blur-nya di dalam MB.

## 4. Transisi whip kontinu

**Kenapa.** Whip yang meyakinkan adalah satu pita: shot lama keluar dan shot baru masuk dengan kecepatan yang sama di sambungannya. Dua animasi terpisah menghasilkan celah atau tumpang tindih yang terbaca slideshow.

**Cara.** Shot keluar `exit: {dir: 'up', len: 16}` berakhir di frame N; shot masuk mulai di `N - 16` dengan `enter: {dir: 'up', len: 16}`. Arah, panjang, dan kurva sama (`E.inOut`). `Shot` di kit menambahkan blur searah gerak sebanding kecepatan (maks 70 px) dan pemisahan RGB maks 9 px. Panjang 14–16 frame; lebih cepat terasa kasar, lebih lambat terasa slide.

**Jebakan.** ID filter SVG harus unik per shot. Whip ke arah berbeda di dua sisi satu sambungan merusak ilusi pita.

## 5. Kamera: dorongan, drift, perspektif

**Kenapa.** Layar yang diam total adalah tanda paling kuat "halaman web". Kamera nyata selalu sedikit bergerak.

**Cara.**

```tsx
const drift = useDrift('logos', 4);                       // Perlin, ≤ 6 px
const pull = mix(1.06, 1, pr(f, 10, 72, E.outSoft));      // dorongan pelan sepanjang shot
<AbsoluteFill style={{transform: `translate(${drift.x}px, ${drift.y}px) scale(${pull})`}}>…</AbsoluteFill>

// kartu masuk dengan perspektif, satu per satu (stagger 3 frame)
<AbsoluteFill style={{perspective: 1800, perspectiveOrigin: '50% 70%'}}>
  <div style={{transformOrigin: '50% 100%', transform: `translateY(${mix(140, 0, p)}px) rotateX(${mix(-62, 0, p)}deg)`}} />
</AbsoluteFill>
```

Kamera yang mengikuti subjek (mis. caret yang sedang mengetik) dihitung sebagai fungsi frame, lalu dilepas ke framing lebar dengan `E.inOut` sebelum aksi besar.

**Jebakan.** Drift > 8 px atau terlalu cepat terasa kamera goyang amatir. Perspektif di parent yang juga ber-scale bisa membuat teks buram; render teks penting di luar layer perspektif.

## 6. Gerak idle

**Kenapa.** Aset yang benar-benar diam terlihat seperti tempelan. Gerak idle kecil membuat semuanya terasa satu dunia.

**Cara.** `floatAt(frame, seed, {amp, rot, breathe})`: sinus pelan + noise + skala "napas", fase dari seed sehingga kelompok aset tidak bergerak serempak. Amplitudo kartu 7 px, rotasi 0,6°, napas 0,5 %. Gabungkan dengan transform masuk: `transform: \`translateY(...) rotateX(...) ${floatCss(fl)}\``.

**Jebakan.** Amplitudo besar membuat penonton memperhatikan gerakannya, bukan isinya.

## 7. Tipografi kinetik

**Kenapa.** Teks yang muncul dengan fade terasa slide presentasi. Kata yang naik dari mask masing-masing terasa title design.

**Cara.**

```tsx
<Line segs="Butuh logo?" start={14} size={150} color="#0f1424" />
<Line segs={[{t: 'Bikin di sini', accent: true}, {t: 'juga.'}]} start={19} size={68} accent={GRAD} />
<Slam text="Selesai." start={b(16)} size={180} />
<Caption index="02" text="Ganti warna" start={40} />
```

Aturan: stagger 2–3 frame per kata; satu kata aksen per judul (italic, boleh gradien halus); mask menyisakan 0,36 em di bawah untuk huruf berekor; kata disembunyikan sebelum dan sesudah geraknya.

Variasi hierarki per adegan (bukan semua di kiri atas): kiri, kanan, tengah, tengah layar; baris kecil + kata raksasa atau sebaliknya; berat 300 vs 800; label kapital kecil dengan tracking 0,08 em.

**Jebakan.** `overflow: hidden` tanpa padding bawah memotong g, j, p, y. Pada ukuran ≥ 150 px, bagian atas kata yang menunggu di bawah mask bisa terlihat; karena itu opacity 0 sebelum gerak dimulai. Gradien di teks (`background-clip: text`) butuh padding untuk kemiringan italic.

## 8. Kedalaman

**Kenapa.** Tiga lapis (latar, subjek, depan) dengan fokus berbeda adalah ciri kamera; satu lapis datar adalah ciri halaman.

**Cara.**
- **Pelat foto**: foto cyclorama studio kosong atau dinding plester hasil generate sebagai latar (`Plate`), dengan dorongan skala pelan. Jauh lebih hidup daripada gradien CSS.
- **Partikel depan** (`Particles`): potongan kertas, daun, debu hasil key; yang dekat besar, blur 6–14 px, bergerak cepat; yang jauh kecil, tajam, lambat.
- **Rack focus**: `filter: blur(${tw(f, 30, 44, 12, 0)}px)` pada subjek sementara latar naik dari 0 ke 6 px.
- **Grain** 6–8 % blend overlay dan **vinyet** lembut di lapisan paling atas, sekali untuk seluruh komposisi.
- **Kilau**: satu sapuan cahaya `soft-light` melintasi kartu saat reveal, bukan glow.

**Jebakan.** Grain > 10 % terbaca kotor setelah kompresi platform. Blur besar di banyak layer + motion blur = render sangat lambat; batasi.

## 9. Demo UI yang meyakinkan

**Kenapa.** Penonton percaya pada UI asli. Mockup HTML buatan sendiri hampir selalu salah ukuran, salah font, dan terlihat palsu.

**Cara.**
1. Screenshot UI asli dalam keadaan kosong pada 2x, simpan sebagai gambar.
2. Teks yang "diketik" disusun ulang di atas screenshot dengan font dan ukuran UI yang sama, `text.slice(0, n)` dengan `n` dari progres linear, plus caret berkedip.
3. Kamera zoom (≈ 2,5x) mengikuti posisi caret (ukur lebar teks dengan `canvas.measureText` memakai font yang sama), lalu mundur ke framing lebar sebelum klik.
4. Kursor gaya macOS dengan drop shadow, tekan = skala 0,88, cincin klik yang membesar dan memudar.
5. Teks yang diketik adalah brief/isi asli, bukan lorem ipsum.

**Jebakan.** Font UI belum termuat saat mengukur → posisi caret meleset; ukur setelah gerbang font.

## 10. Momen khas: serah terima 2D ke render 3D

**Kenapa.** Satu transformasi yang diingat penonton (mis. kartu input terlipat menjadi pesawat kertas yang terbang menembus lensa) membedakan video dari template mana pun. Jatuhkan di drop musik.

**Cara.**
1. Elemen 2D berubah bentuk dengan transform bertahap (lipat = `rotateX` + `scaleY` di keyframe, bayangan ikut).
2. Pada frame saat gerak paling cepat atau objek paling kecil, tukar ke render fotorealistis (opacity silang 1–2 frame); gerak cepat menyembunyikan sambungannya.
3. Render 3D mengikuti lintasan `bez()` dengan rotasi mengikuti arah, motion blur 10–12 sampel.
4. Tampak depan membesar `E.in` sampai memenuhi lensa tepat di frame drop, hard cut ke adegan berikut di balik objek, SFX hit 1 frame sebelumnya.

**Jebakan.** Bila render 3D dan elemen 2D berbeda warna/arah cahaya, sambungannya terlihat. Generate render dengan arah cahaya yang sama dengan adegan.

## 11. Katalog transisi

| Transisi | Kapan | Catatan |
|---|---|---|
| Whip kontinu | default antar adegan | 14–16 frame, arah konsisten per bagian |
| Push-through | ke momen besar | objek memenuhi lensa, cut di baliknya |
| Match cut | dua adegan dengan bentuk sama | posisi dan ukuran bentuk identik di frame cut |
| Mask wipe mengikuti tepi objek | reveal hasil | tepi mask mengikuti objek nyata, bukan garis lurus |
| Hard cut di ketukan | montase cepat | tanpa efek, ritme yang bekerja |

Hindari: crossfade antar adegan, preset zoom-blur, putaran 3D kubus, glitch berlebihan, transisi yang berbeda-beda di setiap cut.

## 12. Angka waktu yang aman

| Hal | Nilai |
|---|---|
| Masuk elemen | 12–18 frame, `E.out` |
| Keluar elemen | 10–12 frame, `E.in` |
| Whip | 14–16 frame |
| Stagger kata | 2–3 frame |
| Stagger kartu/tile | 3 frame atau setengah ketukan |
| Teks layar bertahan | ± 0,3 dtk per kata + 0,5 dtk |
| Hook | bergerak sejak frame 0, pesan terbaca sebelum 2 dtk |
| CTA | ≥ 2,5 dtk diam terbaca di akhir |
