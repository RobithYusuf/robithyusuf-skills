---
name: migrating-inertia-to-typescript
description: Memigrasikan frontend Laravel + Inertia.js (Svelte 5, React, atau Vue 3) dari JavaScript ke TypeScript secara bertahap, mulai dari analisis codebase, setup tsconfig dan Vite, type definitions untuk data dari Laravel, augmentasi InertiaConfig di @inertiajs/core untuk shared props, flash, dan error, migrasi file inti, komponen, layout, sampai pages, lalu verifikasi dengan svelte-check, tsc, atau vue-tsc. Gunakan saat pengguna ingin menambahkan TypeScript ke proyek Inertia, mengetik props halaman dari controller, memperbaiki type $page.props atau useForm, atau merencanakan migrasi JS ke TS. Cocok untuk permintaan seperti migrasi ke TypeScript, ubah JS ke TS, tambah TypeScript di Inertia, typing props Inertia, script lang ts svelte, migrate Inertia to TypeScript, convert Laravel Inertia app to TS, type Inertia shared props.
license: MIT
metadata:
  author: robithyusuf
  version: "1.1.0"
---

# Migrasi Laravel + Inertia dari JavaScript ke TypeScript

Hasil akhir: semua kode di `resources/js` bertipe ketat, shared props Inertia ter-typed global, setiap page mendeklarasikan props yang benar-benar dikirim controller, dan build client + SSR tetap jalan di setiap fase. Migrasi dilakukan per fase supaya setiap langkah bisa di-commit dan di-rollback sendiri.

## Cakupan

| Layer | Didukung |
|---|---|
| Backend | Laravel 11+ dengan adapter Inertia |
| Frontend | Svelte 5 (runes), React 18+, Vue 3 |
| Inertia | v2.x dengan `InertiaConfig` (lihat keputusan C bila v2 lama atau v3) |
| Build | Vite 5+ dengan `laravel-vite-plugin` |

| Aspek | Svelte | React | Vue |
|---|---|---|---|
| Penanda TS | `<script lang="ts">` | file `.tsx` | `<script setup lang="ts">` |
| Config tambahan | `svelte.config.js` + `vitePreprocess()` | `jsx: react-jsx` di tsconfig | `vue-tsc` |
| Typing props | `interface Props` + `$props()` | `interface Props` di parameter fungsi | `defineProps<Props>()` |
| Type checker | `svelte-check` | `tsc --noEmit` | `vue-tsc --noEmit` |
| Page object | store `page` → `$page.props` | `usePage()` | `usePage()` |
| `useForm()` | store → `$form.field` | objek langsung | objek reactive |

## Alur kerja

Salin checklist ini dan centang selama bekerja. Jalankan build setelah setiap fase yang menyentuh kode.

```
- [ ] 0. Analisis codebase, tentukan framework dan keputusan A-F
- [ ] 1. Setup infrastruktur TS (deps, tsconfig, vite.config.ts, entry Blade, script check)
- [ ] 2. Buat type definitions (types/index.ts + types/global.d.ts dengan InertiaConfig)
- [ ] 3. Migrasi file JS inti (entry app/ssr, bootstrap, utils, config, stores)
- [ ] 4. Migrasi komponen UI & shared, dari yang paling sederhana
- [ ] 5. Migrasi layout & komponen dashboard
- [ ] 6. Migrasi pages, cocokkan props dengan controller
- [ ] 7. Cleanup import, type check bersih, build, uji runtime
```

### 0. Analisis codebase

Jangan langsung rename file. Kumpulkan fakta dulu dari root proyek (ganti `svelte` dengan `jsx`/`vue` sesuai framework):

```bash
# Framework, adapter, dan versi
grep -E '"(svelte|react|vue|typescript|vite|@inertiajs/[a-z0-9]+|laravel-vite-plugin|ziggy-js)"' package.json
npm ls @inertiajs/core 2>/dev/null | head -5
grep -rl 'interface InertiaConfig' node_modules/@inertiajs/core/ 2>/dev/null | head -1

# File JS non-komponen yang akan di-rename ke .ts
find resources/js -name '*.js' -not -path '*/node_modules/*' | sort

# Jumlah komponen per folder (untuk urutan fase 4-6)
find resources/js -name '*.svelte' | sed 's|/[^/]*$||' | sort | uniq -c

# Komponen yang belum TS
grep -rL 'lang="ts"' --include='*.svelte' resources/js | wc -l     # Svelte
grep -rL 'lang="ts"' --include='*.vue' resources/js | wc -l        # Vue
find resources/js -name '*.jsx' | wc -l                             # React

# Props tanpa type
grep -rn '\$props()' --include='*.svelte' resources/js | grep -v ': Props'   # Svelte
grep -rnE 'defineProps\((\[|\{)' --include='*.vue' resources/js              # Vue runtime props
grep -rln 'propTypes' resources/js                                            # React PropTypes

# Pola yang butuh perhatian khusus
grep -rln '\$bindable(' resources/js
grep -rlnE 'Snippet|children' --include='*.svelte' resources/js
grep -rnE 'window\.[A-Za-z]+\s*=' resources/js
grep -rn 'import.meta.glob' resources/js

# Shared props dari Laravel (sumber kebenaran untuk sharedPageProps)
grep -n -A40 'function share' app/Http/Middleware/HandleInertiaRequests.php

# Routing helper, entry Blade, SSR
grep -E 'ziggy|wayfinder' composer.json package.json
grep -rn '@vite' resources/views
ls resources/js/ssr.* 2>/dev/null

# Kebersihan import
grep -rnE "from '[^']+\.js'" resources/js | wc -l
grep -rnE "from '(\.\./){2,}" resources/js | wc -l
```

Rangkum hasilnya ke tabel singkat sebelum mulai: jumlah file `.js`, jumlah komponen per folder, framework + versi adapter, ada tidaknya `InertiaConfig`, Ziggy atau Wayfinder, SSR aktif atau tidak, daftar shared props, pola khusus yang ditemukan (`$bindable`, snippet, callback props, global `window.*`, import campuran alias/relative).

### Keputusan per proyek

**A. Framework.** Menentukan type checker dan rujukan yang dibaca: Svelte → [references/svelte.md](references/svelte.md), React atau Vue → [references/react-vue.md](references/react-vue.md).

**B. Strictness.** Default `"strict": true` sejak awal, karena melonggarkan belakangan hampir tidak pernah terjadi. Pakai `unknown` sebagai default untuk data yang belum jelas; `any` hanya escape hatch sementara dengan komentar `// TODO: type this`. Untuk codebase sangat besar yang harus tetap rilis selama migrasi, tambahkan `"allowJs": true` sementara agar file `.js` lama tetap bisa di-import, lalu hapus di fase 7.

**C. Versi Inertia.** Bila `InertiaConfig` ada di `@inertiajs/core`, pakai augmentasi `InertiaConfig` (cara resmi). Bila tidak ada (v2 awal), pakai augmentasi `PageProps` lama atau upgrade adapter dulu. Bila proyek sudah v3, cek upgrade guide resmi; pola props dan form di skill ini tetap berlaku. Detail di [references/types.md](references/types.md). Sumber kebenaran untuk setup type terbaru tetap [dokumentasi TypeScript resmi Inertia](https://inertiajs.com/docs/v2/advanced/typescript); cek di sana bila contoh di skill ini tidak cocok dengan versi adapter.

**D. Package manager.** Dengan pnpm, augmentasi `@inertiajs/core` tidak ter-resolve karena paket tidak di-hoist. Tambahkan `public-hoist-pattern[]=@inertiajs/core` ke `.npmrc` atau jadikan `@inertiajs/core` dependency langsung.

**E. Routing helper.** Wayfinder sudah menghasilkan fungsi route bertipe, jadi tidak perlu deklarasi global. Ziggy butuh deklarasi `route` di `global.d.ts`.

**F. SSR.** Bila ada `ssr.js`, semua kode yang menyentuh `window`, `document`, atau `localStorage` di level modul harus diberi guard, dan build SSR (`vite build --ssr`) ikut diverifikasi di setiap fase.

### 1. Setup infrastruktur

Instal dependensi, buat `tsconfig.json`, rename `vite.config.js` → `vite.config.ts`, ubah entry di `@vite([...])` Blade ke `.ts`/`.tsx`, tambah script `check`. Semua config per framework ada di [references/setup.md](references/setup.md). Setelah fase ini `npm run build` harus tetap lolos walau belum ada komponen yang dimigrasi.

### 2. Type definitions

Buat `resources/js/types/index.ts` (model, enum sebagai union literal, pagination generic, flash) dan `resources/js/types/global.d.ts` (augmentasi `InertiaConfig`, `Window`). Tulis type berdasarkan apa yang **dikirim** controller atau API Resource, bukan kolom database. Contoh lengkap dan jebakan serialisasi Laravel di [references/types.md](references/types.md). Fase ini tidak mengubah perilaku runtime.

### 3. File JS inti

Rename satu per satu dan beri type parameter + return: entry `app`, `ssr`, `bootstrap`, utils/formatter, config menu, stores. Pola per file di [references/core-files.md](references/core-files.md). Build lagi.

### 4-6. Komponen, layout, pages

Urutan yang paling aman:
1. Komponen UI tanpa dependensi (badge, spinner, skeleton, avatar).
2. Komponen form dan komponen dengan two-way binding (`$bindable`, `v-model`).
3. Komponen kompleks (modal, select, data table, generic list).
4. Layout (akses shared props, flash, sidebar state).
5. Pages: auth (props paling sedikit) → admin/CRUD → halaman publik dan alur kompleks (checkout, wizard multi-step).

Untuk tiap page, buka controller yang me-render-nya (`Inertia::render('Nama/Page', [...])`) dan jadikan array itu `interface Props`. Shared props **tidak** dideklarasi ulang per page karena sudah global lewat `InertiaConfig`.

Commit per kelompok folder agar mudah di-rollback.

### 7. Cleanup dan verifikasi

```bash
# Type check (pilih sesuai framework)
npx svelte-check --tsconfig ./tsconfig.json --threshold error
npx tsc --noEmit
npx vue-tsc --noEmit

# Build client + SSR
npm run build

# Sisa pekerjaan, semua idealnya 0
find resources/js -name '*.js' -o -name '*.jsx' | wc -l
grep -rL 'lang="ts"' --include='*.svelte' --include='*.vue' resources/js | wc -l
grep -rnE "from '[^']+\.js'" resources/js | wc -l
grep -rnE ':\s*any\b|as any' resources/js | wc -l
grep -rnE "from '(\.\./){2,}" resources/js | wc -l
```

Cleanup:
- Hapus ekstensi `.js` di import yang menunjuk file yang kini `.ts`.
- Seragamkan import ke alias `@/` (alias di `tsconfig.json` dan `vite.config.ts` harus sama).
- Hapus `allowJs` bila sempat dipakai.
- Pastikan file config baru (`tsconfig.json`, `svelte.config.js`) ikut ter-copy di Dockerfile atau pipeline CI.

Uji runtime: jalankan `php artisan serve` + `npm run dev`, buka halaman utama tiap area, login/register, minimal satu alur CRUD dengan validasi error, dan alur form paling kompleks. Bila SSR aktif, jalankan `php artisan inertia:start-ssr` dan pastikan halaman ter-render di server (view source berisi HTML, bukan hanya `<div id="app">`).

Bila type check gagal, perbaiki per file dan jalankan ulang sampai bersih. Jangan membungkam error dengan `any` atau `@ts-ignore` kecuali diberi komentar alasan.

## Jebakan umum

- **Augmentasi di paket yang salah.** Augment `@inertiajs/core`, bukan `@inertiajs/svelte`/`react`/`vue3`. File `global.d.ts` harus berupa module (`import '@inertiajs/core'` atau `export {}`), kalau tidak `declare module` justru mengganti definisi aslinya.
- **`.d.ts` tidak ter-include.** `tsconfig.json` harus memuat pola `resources/js/**/*.d.ts`, kalau tidak shared props tetap `unknown`.
- **Type tidak cocok dengan JSON Laravel.** Tanggal datang sebagai string, cast `decimal` datang sebagai string, relasi hanya ada bila di-eager-load. Lihat [references/types.md](references/types.md).
- **Pola SvelteKit atau Next.js disalin mentah.** Inertia tidak punya type generation otomatis untuk props page; `PageData`, `./$types`, atau `getServerSideProps` tidak berlaku.
- **`$page` dan `$form` di Svelte.** Pada adapter Svelte v2, keduanya masih Svelte store, jadi akses tetap dengan prefix `$`. Cek ulang bila adapter sudah di-upgrade.
- **Kode browser di level modul.** Tanpa guard `typeof window !== 'undefined'`, build SSR lolos tetapi proses SSR crash saat runtime.
- **Secret ikut terkirim ke props.** Bila saat menulis type terlihat field seperti API key atau private key di page props, itu kebocoran data ke browser. Laporkan ke pengguna dan hapus dari controller, jangan diberi type.

## Rujukan

- [references/setup.md](references/setup.md): baca di fase 1. Dependensi, `tsconfig.json`, `vite.config.ts`, Blade, dan script per framework.
- [references/types.md](references/types.md): baca di fase 2. Contoh `types/index.ts`, `global.d.ts` dengan `InertiaConfig`, fallback versi lama, aturan memetakan JSON Laravel ke type.
- [references/core-files.md](references/core-files.md): baca di fase 3. Entry `app`/`ssr` per framework, bootstrap axios, formatter, config, store dengan guard SSR.
- [references/svelte.md](references/svelte.md): baca di fase 4-6 untuk Svelte 5. Pola props, snippet, bindable, generic component, `$page`/`$form`, perbedaan dengan SvelteKit.
- [references/react-vue.md](references/react-vue.md): baca di fase 4-6 untuk React atau Vue 3. Props, children/slots, event, `usePage`, `useForm`, layout persisten.
