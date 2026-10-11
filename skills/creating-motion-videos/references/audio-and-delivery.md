# Audio, Render, dan Arsip

## Daftar isi

1. Sumber musik dan lisensi
2. Menyamakan musik dengan grid
3. SFX
4. Level dan cara mengukurnya
5. Voice over
6. Iterasi audio tanpa render ulang gambar
7. Render dan finishing
8. Arsip dan penamaan versi

---

## 1. Sumber musik dan lisensi

| Sumber | Cocok untuk | Catatan |
|---|---|---|
| Pustaka berlisensi (paket bisnis) | Iklan berbayar | Pastikan lisensi mencakup paid social ads dan konten tetap sah setelah langganan berhenti |
| Skor orisinal hasil sintesis (numpy/scipy) | Bebas lisensi, struktur persis grid | Kualitas terbatas, tetapi intro, build, riser, jeda, drop, breakdown bisa dikunci ke ketukan |
| Model musik generatif | Variasi cepat | Cek lisensi bobot dan keluaran. Model lokal berat memori: minta izin, tutup browser, satu proses, pakai watchdog memori, matikan sesudah selesai |
| Musik bawaan platform | Posting organik | Hanya sah di platform itu; serahkan juga versi tanpa musik |

## 2. Menyamakan musik dengan grid

1. **Ukur** tempo dan fase: envelope onset pita kick, lipat (fold) pada kandidat BPM, perhalus dengan regresi fase per jendela 16 ketukan. Kalibrasi bias detektor dengan click track yang diketahui.
2. **Regangkan** ke BPM grid. Resample murni ≤ 1,5 % tidak terdengar sebagai perubahan nada; di atas itu pakai time-stretch yang menjaga nada.
3. **Potong di batas bar** supaya drop lagu jatuh di ketukan drop video; untuk versi lebih panjang, ulangi bar utuh. Crossfade equal-power ± 8 ms di setiap sambungan.
4. **Lift** ke drop: sapuan low-pass/high-pass pada 8 ketukan terakhir sebelum drop + jeda ¼ ketukan tepat sebelum drop.
5. **Akhiran "button"**: hit di downbeat terakhir dengan ekor reverb, bukan fade out.
6. **Samakan loudness** semua kandidat bed supaya keseimbangan SFX tidak berubah saat musik diganti.

## 3. SFX

| Jenis | Dipakai untuk |
|---|---|
| whoosh | pergantian adegan besar |
| fwip | cut cepat di dalam adegan, swipe |
| flyby | objek melintasi kamera |
| hit | drop, hentakan kata |
| click, typing | interaksi UI |
| pop | tile/kartu muncul |
| swell/riser | menuju momen besar |
| tick | hitungan kecil |

- Sintesis sendiri (noise terfilter dengan sapuan frekuensi dan envelope) atau pustaka berlisensi; karakter harus seragam.
- Letakkan SFX 0–1 frame **sebelum** event visual; telinga menangkap sedikit lebih lambat.
- Jangan pasang whoosh di setiap cut. Whoosh besar untuk pergantian bagian, fwip kecil di dalam adegan.
- Kelola gain per kategori di satu tempat (mis. peta `{whoosh: 0.375, fwip: 0.56}` di komponen `Sfx`), supaya permintaan "transisinya kurang kencang/kekencangan" cukup satu perubahan untuk semua versi.

## 4. Level dan cara mengukurnya

| Lapisan | Target |
|---|---|
| Master | −14 LUFS integrated, true peak −1,5 dBTP |
| Transisi (whoosh, flyby, fwip) | ≥ 4 LU di bawah musik setempat (momentary 400 ms); kenaikan loudness mix akibat SFX ("poke") ≤ ± 1,5 dB |
| Voice over | ± 7 LU di atas musik setelah drop; 11–12 LU terdengar "ditempel" |
| SFX kecil saat ada suara | −4 dB |

Titik rawan transisi: intro pelan, build yang di-low-pass, breakdown, dan jeda sebelum drop. Level tetap yang pas di drop bisa menonjol 4–6 dB di bagian-bagian itu.

```bash
# level tiap kejadian: SFX saja vs musik saja pada jendela yang sama
python3 scripts/sfx_levels.py --music public/audio/music.wav --sfx out/sfx.wav --music-gain 0.9 \
  --fps 30 --frames 102,229,338,460,1165 --limit -4
# loudness master
ffmpeg -i out/myvideo.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "I:|Peak:"
```

Dengarkan juga di speaker ponsel dan earbud; speaker laptop menyembunyikan bass dan melebihkan treble.

## 5. Voice over

- Naskah bercerita, **tidak** membacakan teks layar. Take dipecah hanya di akhir kalimat. Pakai timestamp per kata dari TTS untuk memastikan frasa jatuh di adegan yang dibicarakannya. Diam di drop.
- Olahan: high-pass 90 Hz, −2,5 dB di 250 Hz, +2,5 dB di 3,8 kHz, de-esser, kompresi ringan, ruang stereo pendek (± 0,45 dtk) dicampur tipis.
- Mix: bed musik −2,5 dB selama ada VO, dip −6 dB lagi di bawah tiap kalimat (attack ± 6 frame, release ± 18 frame, jeda pendek antar kalimat tetap ter-dip). SFX kecil yang jatuh di tengah kalimat −4 dB. Bunyi mirip whoosh di versi VO boleh −3 dB lagi, dan riser bawaan musik di-dip saat bertabrakan dengan kalimat.
- Versi tanpa VO tetap komposisi terpisah dengan mix yang identik; menambah VO tidak boleh mengubah versi lama.
- Simpan take mentah TTS di cache supaya mengubah olahan tidak memakan kredit, dan kunci snapshot model supaya take ulang bersuara sama. Paket gratis TTS sering tidak mencakup lisensi komersial.

## 6. Iterasi audio tanpa render ulang gambar

Render audio saja (Remotion tidak mengambil screenshot frame untuk codec audio), lalu mux dengan video mentah:

```bash
npx remotion render src/index.ts MyVideo out/sfx.wav --codec=wav --props='{"music":false}'
ffmpeg -y -i out/render-raw.mp4 -i out/sfx.wav -i public/audio/music_b.wav \
  -filter_complex "[2:a]volume=0.9[m];[1:a][m]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[a]" \
  -map 0:v -map "[a]" -c:v copy -ar 48000 -c:a aac -b:a 256k -movflags +faststart out/preview-music-b.mp4
```

Butuh prop `music` di komposisi untuk mematikan musik. Satu pratinjau selesai dalam detik, bukan menit.

## 7. Render dan finishing

```bash
npx remotion render src/index.ts MyVideo out/render-raw.mp4 --crf=16 --concurrency=6
# master
ffmpeg -y -i out/render-raw.mp4 -c:v copy -af "loudnorm=I=-14:TP=-1.5:LRA=11" -ar 48000 -c:a aac -b:a 256k \
  -movflags +faststart out/myvideo.mp4
# tanpa musik (SFX saja), untuk dipasangi musik dari pustaka platform
npx remotion render src/index.ts MyVideo out/sfx-only.wav --codec=wav --props='{"music":false}'
ffmpeg -y -i out/render-raw.mp4 -i out/sfx-only.wav -map 0:v -map 1:a -c:v copy -af "alimiter=limit=0.84:level=false" \
  -ar 48000 -c:a aac -b:a 256k -shortest -movflags +faststart out/myvideo-no-music.mp4
# cover dari frame 0
ffmpeg -y -i out/render-raw.mp4 -vf "select=eq(n\,0)" -vframes 1 -q:v 2 out/cover.jpg
```

- Simpan `render-raw.mp4` untuk mux ulang audio kapan pun.
- `loudnorm` satu tahap bisa sedikit melewati target true peak; untuk pengiriman ketat pakai dua tahap (ukur dulu, lalu terapkan dengan `measured_*`).
- Turunkan `--concurrency` bila memori menipis (motion blur dan blur besar memakan RAM per tab Chrome).

## 8. Arsip dan penamaan versi

Masukkan langkah arsip ke skrip render supaya tidak terlupa:

```json
"render": "sh scripts/archive.sh before-render && remotion render src/index.ts MyVideo out/render-raw.mp4 --crf=16 && sh scripts/finish.sh"
```

```sh
#!/bin/sh
# scripts/archive.sh [label]: salin master + cover ke out/archive/<waktu>_<label>/ sebelum ditimpa.
set -e
cd "$(dirname "$0")/.."
ls out/myvideo*.mp4 >/dev/null 2>&1 || { echo "belum ada master"; exit 0; }
sig() { for f in "$@"; do [ -f "$f" ] && printf '%s %s\n' "$(basename "$f")" "$(wc -c < "$f")"; done; }
LAST=$(ls -d out/archive/*/ 2>/dev/null | sort | tail -1)
if [ -n "$LAST" ] && [ "$(sig "$LAST"myvideo*.mp4)" = "$(sig out/myvideo*.mp4)" ]; then
  echo "sama dengan arsip terakhir ($LAST)"; exit 0
fi
DEST="out/archive/$(date +%Y-%m-%d_%H%M)_${1:-render}"
mkdir -p "$DEST" && cp -p out/myvideo*.mp4 out/cover*.jpg "$DEST"/ 2>/dev/null || true
echo "diarsipkan ke $DEST"
```

Varian mendapat nama baru (`-vo`, `-60s`, `-music-b`), bukan menimpa berkas yang sudah dikirim.
