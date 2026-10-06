---
name: fixing-svelte5-warnings
description: Menangani compiler warning Svelte 5 (runes mode) seperti state_referenced_locally, a11y_consider_explicit_label, a11y_label_has_associated_control, dan a11y_missing_attribute dengan memperbaiki akar masalah, bukan membungkam massal. Mengumpulkan warning lewat svelte-check, mengelompokkan per kode, memperbaiki penyebabnya ($derived, closure, aria-label, for/id, alt), lalu memakai svelte-ignore hanya untuk false positive yang terverifikasi. Gunakan saat svelte-check, vite dev, atau vite build menampilkan warning Svelte, saat migrasi ke Svelte 5, saat upgrade Svelte memunculkan banyak warning baru, atau sebelum rilis yang menargetkan nol warning. Cocok untuk permintaan seperti fix warning svelte, hilangkan warning svelte-check, bersihkan warning svelte, state referenced locally, svelte-ignore, a11y warning svelte, fix svelte 5 warnings, clean up svelte-check warnings, This reference only captures the initial value.
license: MIT
metadata:
  author: robithyusuf
  version: "1.0.0"
---

# Memperbaiki Warning Svelte 5

Tujuannya: warning hilang karena penyebabnya diperbaiki, bukan karena disembunyikan. Sebagian besar warning Svelte 5 menandai bug nyata (nilai yang tidak reaktif, elemen yang tidak terbaca screen reader). Membungkam massal menyembunyikan bug itu sekaligus warning baru yang mungkin lebih serius.

## Alur kerja

```
- [ ] 1. Kumpulkan warning dengan svelte-check, kelompokkan per kode
- [ ] 2. Tentukan scope (file yang diubah saja, atau batch cleanup)
- [ ] 3. Klasifikasi tiap temuan: fix atau false positive
- [ ] 4. Perbaiki akar masalah per kode (lihat references/warnings.md)
- [ ] 5. Suppress per-instance hanya untuk false positive terverifikasi, beri alasan
- [ ] 6. Jalankan ulang svelte-check, bandingkan jumlah warning
```

**1. Kumpulkan.** Jalankan dari root proyek. Pakai script `check` di `package.json` bila ada, karena biasanya sudah memuat flag `--tsconfig` yang benar.

```bash
npx svelte-check --threshold warning                    # ringkasan yang bisa dibaca manusia
npx svelte-check --output machine-verbose 2>/dev/null \
  | grep -o '"code":"[^"]*"' | sort | uniq -c | sort -rn  # hitung per kode warning
```

`machine-verbose` mencetak satu objek JSON per baris (`filename`, `start`, `message`, `code`), jadi mudah difilter per kode atau per file. Warning dari `vite dev`/`vite build` sama dengan dari compiler, tetapi svelte-check lebih lengkap karena memeriksa semua file, bukan hanya yang dimuat.

**2. Tentukan scope.** Default: perbaiki warning di file yang memang sedang diubah. Jangan menyapu warning di file lain dalam perubahan yang sama, karena diff jadi sulit di-review dan perbaikan `$derived` bisa mengubah perilaku. Batch cleanup seluruh proyek sebaiknya jadi commit terpisah (mis. `fix: resolve N Svelte compiler warnings`). Lihat bagian "Kapan memperbaiki" di bawah.

**3. Klasifikasi.** Untuk tiap kode, buka bagian yang sesuai di [references/warnings.md](references/warnings.md) dan tentukan:
- **Bug nyata** → perbaiki (langkah 4). Ini kasus mayoritas.
- **Disengaja** (mis. sengaja menyalin nilai awal prop ke state form) → suppress per-instance dengan alasan (langkah 5).
- **False positive compiler** → pastikan dulu dengan membaca kondisi pemicu di references. Banyak "false positive" ternyata salah paham. Contoh: `a11y_label_has_associated_control` tidak pernah muncul bila `<label>` punya atribut `for`.

**4. Perbaiki akar masalah.** Ringkasan cepat:

| Kode | Penyebab umum | Perbaikan default |
|---|---|---|
| `state_referenced_locally` | Nilai `$props()`/`$state()` dipakai di top-level script sehingga hanya nilai awal yang tertangkap | Bungkus dengan `$derived(...)`, atau rujuk lewat closure (`() => value`) |
| `a11y_consider_explicit_label` | `<button>`/`<a>` hanya berisi ikon | Tambah `aria-label`, atau teks `sr-only` |
| `a11y_label_has_associated_control` | `<label>` tanpa `for` dan tanpa kontrol di dalamnya | `for` + `id` yang cocok, atau bungkus kontrolnya |
| `a11y_missing_attribute` | `<img>` tanpa `alt`, `<a>` tanpa `href`, `<iframe>` tanpa `title`, dll. | Tambah atribut wajib; `alt=""` untuk gambar dekoratif |

Kode lain: cari di dokumentasi resmi (`https://svelte.dev/docs/svelte/compiler-warnings`), baca kondisi pemicunya, lalu tambahkan entri baru ke references/warnings.md mengikuti template di bagian akhir file itu.

**5. Suppress hanya bila perlu.** Taruh komentar tepat di atas baris/elemen pemicu, sebut kodenya persis, dan tulis alasan dalam kurung:

```svelte
<script lang="ts">
  let { product } = $props();
  // svelte-ignore state_referenced_locally (form sengaja menyalin nilai awal, tidak ikut prop)
  let form = $state({ name: product?.name ?? '' });
</script>

<!-- svelte-ignore a11y_autofocus (dialog pencarian, fokus langsung adalah perilaku yang diharapkan) -->
<input autofocus />
```

Beberapa kode boleh digabung dengan koma dalam satu komentar. Jangan pakai `svelte-ignore` tanpa kode atau dengan kode yang tidak relevan, karena itu ikut menyembunyikan warning lain di elemen yang sama.

**6. Verifikasi.** Jalankan ulang perintah langkah 1. Jumlah per kode harus turun sesuai yang diperbaiki, dan tidak ada kode baru yang muncul. Untuk perbaikan `state_referenced_locally`, uji juga perilakunya: ubah nilai sumber (navigasi ke data lain, update prop) dan pastikan UI ikut berubah, atau sengaja tidak berubah bila memang disalin.

## Kapan suppress vs fix

| Situasi | Pendekatan |
|---|---|
| Array/objek/nilai turunan dibuat dari props | **Fix** dengan `$derived()` |
| State dioper ke `setContext` atau fungsi | **Fix** dengan closure (`() => count`) |
| Form edit sengaja menyalin nilai awal prop | **Suppress** per-instance, atau `$derived` yang bisa ditimpa bila form harus reset saat prop berubah |
| Tombol/link ikon tanpa label | **Fix** dengan `aria-label` |
| `<label>` tanpa asosiasi | **Fix** dengan `for`/`id` |
| `<img>` tanpa `alt` | **Fix**, selalu |
| Warning dari komponen pihak ketiga di `node_modules` | **Filter global** berdasarkan path file, bukan berdasarkan kode |

## Filter global (jalan terakhir)

Hanya untuk kode yang tidak bisa diubah (library pihak ketiga, file hasil generate). Filter berdasarkan **lokasi file**, jangan matikan kode warning untuk seluruh proyek, karena itu menyembunyikan masalah baru di kode sendiri.

```js
// svelte.config.js
export default {
  compilerOptions: {
    // true = tampilkan warning, false = buang
    warningFilter: (warning) => !warning.filename?.includes('node_modules'),
  },
};
```

`warningFilter` adalah opsi compiler, jadi ikut berlaku di build (vite-plugin-svelte) dan di svelte-check yang meneruskan `compilerOptions` dari `svelte.config.js`. Opsi `onwarn` adalah opsi vite-plugin-svelte, jadi jangan andalkan untuk svelte-check. Untuk svelte-check saja tersedia flag `--compiler-warnings "kode:ignore"`, tetapi flag ini mematikan kode untuk semua file, jadi hindari kecuali sementara.

## Kapan memperbaiki

- **Saat menulis komponen baru**: langsung benar (`$derived`, `aria-label`, `for`/`id`, `alt`). Perbaikan a11y hanya butuh beberapa detik, tetapi cepat menumpuk bila ditunda.
- **Sebelum PR/merge**: perbaiki warning di file yang diubah saja.
- **Sebelum rilis atau saat sprint cleanup**: batch fix seluruh proyek dalam commit terpisah, target nol warning.
- **`state_referenced_locally`**: kerjakan saat batch/refactor, bukan di tengah fitur, karena memilih `$derived` vs salinan sengaja butuh memahami alur datanya.
- **Jangan** saat sedang menangani hotfix produksi, saat tidak paham konteks komponennya, atau di file milik tim lain (buat issue terpisah). Warning tidak memblokir build.

Setelah proyek mencapai nol warning, kunci di CI agar tidak muncul lagi:

```bash
npx svelte-check --fail-on-warnings
```

## Jebakan umum

- **Membungkus dengan `$derived` secara membabi buta.** `$derived` membuat nilai ikut berubah saat sumber berubah. Untuk state form yang sedang diedit pengguna, ini bisa menimpa input pengguna. Putuskan dulu: nilai harus mengikuti sumber, atau sengaja disalin sekali.
- **`aria-hidden="true"` pada tombol** memang menghilangkan `a11y_consider_explicit_label`, tetapi membuat tombol tidak terlihat oleh screen reader. Itu bukan perbaikan.
- **Ikon berupa komponen** (`<CloseIcon />`) di dalam tombol tidak memicu warning karena compiler menganggap komponen punya konten. Tombol itu tetap butuh `aria-label`.
- **`for` tanpa `id` yang cocok** lolos dari compiler (yang hanya mengecek keberadaan atribut `for`), tetapi asosiasinya tetap rusak. Pastikan komponen input meneruskan `id` ke elemen `<input>` aslinya.
- **Teks pesan warning berubah antar versi Svelte.** Cocokkan berdasarkan kode (`state_referenced_locally`), bukan teks pesan.

## Rujukan

- Penyebab, kondisi pemicu, dan contoh before/after per kode warning, plus template untuk menambah kode baru: [references/warnings.md](references/warnings.md). Baca bagian kode yang relevan saat langkah 3-4.
- Daftar lengkap kode warning resmi: `https://svelte.dev/docs/svelte/compiler-warnings`
