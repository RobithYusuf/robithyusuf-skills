# Aset Generatif

Aset fotorealistis hasil image generation untuk properti, latar, dan karakter. Bukti produk (UI, keluaran) tetap harus asli.

## Daftar isi

1. Kapan generate
2. Persiapan dan keamanan kunci
3. Jalur A: endpoint kompatibel OpenAI Images API
4. Jalur B: Codex CLI
5. Resep prompt
6. Pascaproses: key chroma, alfa, potong
7. Pemeriksaan kualitas
8. Lisensi dan etika

---

## 1. Kapan generate

| Butuh | Sumber |
|---|---|
| UI produk, hasil produk, data | **Asli** (screenshot 2x, file keluaran) |
| Objek 3D (pesawat kertas, ponsel, struk, kemasan generik) | Generate di latar chroma hijau, lalu key |
| Latar (cyclorama studio, dinding plester, meja) | Generate tanpa objek, dipakai sebagai pelat foto |
| Situasi masalah (meja kerja malam, toko sepi) | Generate fotorealistis, layar/teks diganti belakangan |
| Karakter/maskot 3D | Edit dari ilustrasi 2D yang sudah ada sebagai referensi, supaya tetap on-model |
| Ikon, garis, kursor | Kode (SVG/CSS), jangan generate |

## 2. Persiapan dan keamanan kunci

- Env var: `IMAGE_API_BASE_URL` (base URL endpoint, termasuk `/v1` bila provider memakainya), `IMAGE_API_KEY`, `IMAGE_MODEL` (default `gpt-image-2`). Isi dari secret manager atau shell profile, **jangan** di file proyek, prompt agent, log, atau commit. `.env` wajib masuk `.gitignore`.
- Bila kunci hanya ada di server atau container backend (mis. backend produk sudah punya klien gateway), jalankan skrip generate **di sana** lalu salin hasilnya (`docker cp`, `scp`). Kunci tidak pernah menyentuh laptop atau repo video.
- Jangan pernah mencetak nilai env atau base URL di output skrip; cukup nama model dan path keluaran.

## 3. Jalur A: endpoint kompatibel OpenAI Images API

Pakai [../scripts/gen_image.py](../scripts/gen_image.py) (`pip install openai`, Pillow untuk `--flatten`):

```bash
# objek di latar hijau, 3 varian
python3 scripts/gen_image.py --prompt-file prompts/plane_side.txt --size 1536x1024 --chroma --n 3 \
  --out public/gen/raw/plane_side.png
# latar studio kosong, potret
python3 scripts/gen_image.py --prompt "Photograph of an empty seamless studio cyclorama …" --size 1024x1536 \
  --opaque --out public/gen/raw/studio_dark.png
# karakter 3D dari maskot 2D (edit dengan referensi)
python3 scripts/gen_image.py --edit assets/mascot_2d.png --prompt-file prompts/mascot3d.txt --size 1536x1024 \
  --chroma --out public/gen/raw/mascot3d.png
# cek permintaan tanpa memanggil API
python3 scripts/gen_image.py --prompt "…" --size 1024x1536 --dry-run
```

Perilaku gateway yang sering ditemui:
- **Parameter diabaikan.** `size`, `background`, atau `quality` bisa diabaikan oleh gateway pihak ketiga. Skrip menulis rasio dan orientasi di **teks prompt** (`--no-ratio-text` untuk mematikan).
- **PNG transparan bermask kotor** untuk latar datar. Tambahkan `--opaque` (kalimat "solid, fully opaque background") dan, bila tetap terjadi, `--flatten '#00B140'` untuk aset chroma atau `--flatten '#ffffff'` untuk latar putih.
- **Lambat dan terbatas.** Edit bisa 50–100 dtk; 429 dan timeout biasa. Skrip mencoba ulang dengan jeda bertambah; jalankan maksimal ± 3 permintaan paralel.
- **Ukuran gpt-image-2**: sisi kelipatan 16, sisi terpanjang ≤ 3840, rasio ≤ 3:1. Ukuran umum `1024x1024`, `1536x1024`, `1024x1536`.

`--n` untuk varian satu prompt; aset yang berbeda = prompt berbeda. Simpan semua prompt di berkas (`prompts/*.txt` atau satu skrip) supaya aset bisa dibuat ulang.

## 4. Jalur B: Codex CLI

Codex punya tool bawaan `image_gen` (fitur `image_generation`, cek `codex features list`) dan skill sistem `imagegen`. Jalur bawaan memakai login Codex, **tidak** butuh `OPENAI_API_KEY`.

```bash
codex exec -C . -s workspace-write \
  "Pakai skill imagegen (tool bawaan image_gen). Use case: product-mockup. Subject: one crisp white paper airplane, \
three-quarter side view, nose to the upper right. Scene/backdrop: flat solid chroma-key green #00B140 edge to edge. \
Constraints: no text, no logo, no shadow on the background. Salin hasil terpilih ke public/gen/raw/plane_side.png."
```

- Hasil bawaan tersimpan di `$CODEX_HOME/generated_images/<sesi>/` (default `~/.codex`). Aset yang dipakai proyek wajib disalin ke workspace; cari yang terbaru dengan `ls -t "${CODEX_HOME:-$HOME/.codex}"/generated_images/*/*.png | head -1`.
- Gambar referensi (gaya, karakter, atau gambar yang mau diedit) dilampirkan dengan `-i path.png`.
- Transparansi: minta latar transparan pada tool bawaan, atau generate di latar chroma lalu jalankan skrip bawaan skill imagegen:
  `python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/scripts/remove_chroma_key.py" --input in.png --out out.png --auto-key border --soft-matte --despill`
- Fallback CLI skill imagegen (`scripts/image_gen.py` di folder skill itu) memakai Images API dan butuh `OPENAI_API_KEY`; model bawaannya `gpt-image-2`, yang tidak mendukung `background=transparent` di jalur CLI. Pakai hanya bila memang perlu kontrol parameter.
- Format prompt yang dianjurkan skill imagegen: `Use case / Asset type / Primary request / Scene/backdrop / Subject / Style/medium / Composition/framing / Lighting/mood / Materials/textures / Constraints / Avoid`.

## 5. Resep prompt

Prompt dalam bahasa Inggris (model paling patuh). Struktur: subjek dan material → sudut dan framing → cahaya dan lensa → latar → larangan. Akhiran latar hijau yang terbukti bersih:

```text
Isolated on a perfectly flat, evenly lit, solid chroma-key green background (pure #00B140) that fills the whole
frame edge to edge: no floor, no horizon, no gradient, no vignette, no shadow cast on the background, no green
reflections on the object. No text, no logo, no watermark, no brand marks anywhere.
```

- **Objek pahlawan**: "Photorealistic studio product photograph of ONE <objek> made of <material nyata dengan tekstur>. <Sudut>, <arah>. Soft large key light from the top left, gentle fill, realistic soft shading, crisp focus, 85mm lens, high-end commercial still life. The object occupies about 70% of the frame width, fully inside the frame." + akhiran hijau. Buat tampak samping dan tampak depan terpisah bila objek akan terbang ke kamera.
- **Perangkat dengan layar kosong**: "PERFECTLY straight-on front view (orthographic, zero tilt, zero perspective) … The ENTIRE display area is a flat matte solid chroma-key green (#00B140) with no reflections, no UI, no glare." Layar hijau tertutup bingkai menjadi "lubang" yang posisinya diukur `key_chroma.py --hole`.
- **Latar studio**: "Photograph of an empty seamless photo studio cyclorama in deep neutral charcoal graphite, NO blue tint: smooth curve from wall to floor, one soft pool of overhead light in the lower third falling off into near-black, very subtle haze, fine film grain. Completely empty: no objects, no people, no light fixtures, no text. Medium-format camera, vertical composition." Variasi: dinding plester hangat dengan cahaya jendela miring, cyclorama kertas putih hangat.
- **Serpihan untuk partikel**: banyak potongan kertas kecil terpisah di latar hijau, tidak saling menempel, lalu dipisah per komponen (`--split`).
- **Properti kosong** (struk, kartu, kemasan): permukaan polos tanpa teks; teks asli ditempel di Remotion supaya tajam dan benar.
- **Karakter dari maskot 2D** (edit dengan referensi): "Recreate the SAME character from this illustration as a premium 3D render … same face, same colors, same accessories. Materials: <material nyata>. Soft studio lighting … NOT plastic, NOT glossy toy, no glow, no sparkles, no motion lines, no extra objects." + akhiran hijau.

Larangan yang selalu ditulis: no glow, no sparkles, no lens flare, no text, no logo, no watermark. Arah cahaya sama untuk semua aset satu video.

## 6. Pascaproses: key chroma, alfa, potong

```bash
python3 scripts/key_chroma.py public/gen/raw/plane_side.png public/gen/raw/plane_front.png --out public/gen --crop
python3 scripts/key_chroma.py public/gen/raw/phone.png --out public/gen --crop --hole     # + phone.hole.json
python3 scripts/key_chroma.py public/gen/raw/scraps.png --out public/gen/scraps --split 2500
python3 scripts/key_chroma.py public/gen/raw/mascot3d.png --out public/gen --crop --solid 200
```

- Key berbasis dominasi hijau (`g − max(r, b)`) dengan ambang lunak dan despill (hijau tidak boleh melebihi kanal lain di tepi objek), median filter untuk bintik di tepi.
- `--hole` mencari area transparan yang tertutup (layar perangkat) dan menulis kotak + perkiraan radius sudut ke JSON, sehingga konten bisa diletakkan tepat di belakang bingkai.
- `--solid 200` meratakan alfa ≥ 200 menjadi penuh (membersihkan mask kotor dari gateway).
- Simpan sumber mentah di `public/gen/raw/` dan hasil key di `public/gen/`. Ukuran tampil × 2 sudah cukup; foto besar boleh `.webp`.

## 7. Pemeriksaan kualitas

Buka setiap hasil sebelum dipakai: teks gibberish, jari/tangan aneh, perspektif perangkat tidak lurus, sisa hijau di tepi (halo), bayangan yang jatuh ke latar hijau, arah cahaya berbeda dengan aset lain. Lebih cepat generate ulang dengan satu perubahan prompt daripada memperbaiki manual.

## 8. Lisensi dan etika

- Periksa ketentuan provider untuk penggunaan komersial keluaran.
- Jangan membuat kemiripan orang nyata, logo, kemasan, atau nama merek nyata.
- Ikuti kebijakan label konten AI di platform iklan untuk gambar realistis.
