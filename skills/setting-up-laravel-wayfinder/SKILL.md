---
name: setting-up-laravel-wayfinder
description: Memasang Laravel Wayfinder (fungsi TypeScript ter-generate dari route dan controller Laravel) di proyek Laravel + Inertia + Svelte/React/Vue + Vite, serta memigrasikan proyek yang sudah memakai Ziggy (route() global, @routes, ziggy-js) ke Wayfinder termasuk penanganan build Docker/CI tanpa PHP. Gunakan saat pengguna ingin menambah Wayfinder, mengganti Ziggy, merapikan pemanggilan route di frontend, atau build gagal karena plugin Wayfinder butuh php artisan. Cocok untuk permintaan seperti pasang wayfinder, migrasi ziggy ke wayfinder, hapus ziggy, ganti route() dengan wayfinder, type-safe route laravel, install laravel wayfinder, migrate from ziggy, wayfinder docker build failed, Cannot find module @/actions.
license: MIT
metadata:
  author: robithyusuf
  version: "1.0.0"
---

# Memasang Laravel Wayfinder

Wayfinder menjalankan `php artisan wayfinder:generate` untuk menghasilkan fungsi TypeScript dari route dan controller Laravel. Berbeda dengan Ziggy, tidak ada daftar route yang dikirim ke browser: URL di-bake ke kode, tree-shakeable, bertipe, dan jalan di SSR tanpa setup khusus.

Wayfinder masih **beta** (API bisa berubah sebelum v1.0.0). Bila perilaku yang ditemui berbeda dari skill ini, cek README resmi `laravel/wayfinder` dan `laravel/vite-plugin-wayfinder`, lalu ikuti yang resmi.

## Tentukan alur dulu

Periksa proyek sebelum mengubah apa pun:

```bash
grep -n "ziggy" composer.json package.json
grep -rn "@routes" resources/views/
grep -rnE "\broute\(" resources/js/ | wc -l
ls Dockerfile* docker-compose*.yml 2>/dev/null
```

- **Tidak ada Ziggy** → alur *Fresh setup* (langkah 1-4, lalu verifikasi).
- **Ada Ziggy** → alur *Migrasi*: langkah 1-4, lalu langkah 5-7. Rincian per file ada di [references/migrating-from-ziggy.md](references/migrating-from-ziggy.md).
- **Frontend di-build di stage Docker/CI tanpa PHP** → wajib baca [references/docker-and-ci.md](references/docker-and-ci.md) sebelum langkah 2 dan 3, karena keputusan `.gitignore` dan konfigurasi plugin bergantung padanya.

## Alur kerja

Salin checklist ini dan centang selama bekerja:

```
- [ ] 1. Install paket PHP + Vite plugin, generate pertama kali
- [ ] 2. Tambah plugin ke vite.config (kondisional bila build tanpa PHP)
- [ ] 3. Putuskan: gitignore file ter-generate atau commit
- [ ] 4. Pastikan alias @ ada di Vite dan tsconfig
- [ ] 5. (Migrasi) Inventaris pemakaian Ziggy
- [ ] 6. (Migrasi) Ganti setiap route() dengan import Wayfinder
- [ ] 7. (Migrasi) Bongkar infrastruktur Ziggy, composer remove
- [ ] 8. Verifikasi (build, SSR, grep, halaman)
```

**1. Install.**

```bash
composer require laravel/wayfinder
npm install -D @laravel/vite-plugin-wayfinder
php artisan wayfinder:generate
```

Hasilnya tiga direktori di `resources/js/`: `actions/` (per controller, mis. `actions/App/Http/Controllers/PostController.ts`), `routes/` (per named route, mis. `routes/post.ts`), dan `wayfinder/` (helper internal). Pastikan ketiganya muncul sebelum lanjut.

**2. Vite plugin.** Letakkan `wayfinder()` setelah `laravel()` dan sebelum plugin framework. Plugin menjalankan `wayfinder:generate` saat `vite dev`/`vite build` dan me-regenerate saat route atau controller berubah.

```typescript
import { defineConfig } from 'vite';
import laravel from 'laravel-vite-plugin';
import { svelte } from '@sveltejs/vite-plugin-svelte'; // React: @vitejs/plugin-react, Vue: @vitejs/plugin-vue
import { wayfinder } from '@laravel/vite-plugin-wayfinder';

// Lewati plugin bila build berjalan tanpa PHP (lihat references/docker-and-ci.md)
const skipWayfinder = process.env.DOCKER === 'true';

export default defineConfig({
    plugins: [
        laravel({ input: ['resources/css/app.css', 'resources/js/app.ts'], ssr: 'resources/js/ssr.ts', refresh: true }),
        ...(skipWayfinder ? [] : [wayfinder()]),
        svelte(), // react() / vue()
    ],
});
```

Pakai `wayfinder()` biasa bila semua lingkungan build punya PHP. Opsi plugin (semua opsional):

```typescript
wayfinder({
    path: 'resources/js',                              // lokasi output
    command: 'php artisan wayfinder:generate',         // mis. 'herd php artisan ...' atau 'sail artisan ...'
    routes: true,                                      // generate routes/
    actions: true,                                     // generate actions/
    formVariants: false,                               // true = helper .form() untuk <form>
    patterns: ['resources/**/routes/*.php'],           // file tambahan yang di-watch
})
```

Flag CLI padanannya: `--path=...`, `--skip-actions`, `--skip-routes`, `--with-form`. Samakan `formVariants` dengan `--with-form` bila file kadang di-generate manual, supaya hasilnya tidak berganti-ganti.

**3. `.gitignore`.** Default: abaikan file ter-generate, karena di-regenerate tiap build.

```gitignore
/resources/js/actions/
/resources/js/routes/
/resources/js/wayfinder/
```

Pengecualian: bila frontend di-build di lingkungan tanpa PHP dan Anda memilih strategi "commit file ter-generate", **jangan** gitignore. Lihat [references/docker-and-ci.md](references/docker-and-ci.md).

Hati-hati bila proyek sudah punya `resources/js/routes/` atau `resources/js/actions/` buatan tangan. Wayfinder akan menulis ke sana dan pola gitignore di atas ikut mengabaikannya. Pindahkan file lama atau pakai opsi `path` yang berbeda.

**4. Alias `@`.** Import Wayfinder ditulis `@/actions/...` dan `@/routes/...`. Pastikan `resolve.alias` di Vite (`'@': '/resources/js'`) dan `compilerOptions.paths` di `tsconfig.json` (`"@/*": ["./resources/js/*"]`) sudah ada. Starter kit Laravel biasanya sudah menyediakannya.

**5-7. Migrasi dari Ziggy.** Ringkasnya:
- Inventaris semua `route(...)`, `route().current(...)`, `@routes`, `ziggy` di PHP/JS/Blade.
- Ganti `route('posts.show', id)` → `show.url(id)` dari `@/routes/posts` (named route) atau `@/actions/...` (controller).
- Hapus `@routes`, shared prop `ziggy` di `HandleInertiaRequests`, `config/ziggy.php`, deklarasi tipe `route()`, fallback `window.route`, plugin `ZiggyVue`/paket `ziggy-js`, lalu `composer remove tightenco/ziggy`.
- Filter route berbasis role (mis. `@routes('admin')` vs `@routes('public')`) tidak diperlukan lagi karena tidak ada daftar route di browser. Ini bukan pengganti otorisasi di server.

Langkah lengkap, tabel pemetaan, dan contoh sebelum/sesudah: [references/migrating-from-ziggy.md](references/migrating-from-ziggy.md).

## Pemakaian inti

Setiap fungsi mengembalikan `{ url, method }`; `.url()` hanya string.

```typescript
import { show, store } from '@/actions/App/Http/Controllers/PostController'; // per controller
import { dashboard } from '@/routes/admin';                                  // per named route admin.dashboard

show(1);                               // { url: '/posts/1', method: 'get' }
show.url(1);                           // '/posts/1'
show.url(1, { query: { page: 2 } });   // '/posts/1?page=2'
```

Aturan yang sering terlewat:
- Untuk `router.visit`, `form.post/delete(...)`, dan `href`, pakai `.url()`. Itu selalu bekerja di semua versi Inertia. Versi Inertia yang mendukung Wayfinder juga menerima objeknya langsung (`form.submit(store())`, `<Link href={show(1)}>`).
- Import fungsi spesifik (`{ show }`), bukan default export controller, agar tree-shaking bekerja.
- Method controller bernama reserved word JS diberi akhiran `Method` (`delete` → `deleteMethod`). `destroy` tetap `destroy`.
- Satu controller method yang dipakai beberapa route (mis. `ProfileController@edit` untuk `/profile` dan `/admin/profile`) membuat export di `actions/` jadi dictionary per URI, bukan fungsi. Pakai import dari `@/routes/...` untuk kasus itu.

Parameter, query, form variant, invokable controller, contoh Inertia untuk Svelte/React/Vue, dan fitur branch `next`: [references/api.md](references/api.md).

## Verifikasi

```bash
php artisan route:clear                 # hindari generate dari route cache lama
php artisan wayfinder:generate
npx tsc --noEmit                        # atau svelte-check / vue-tsc sesuai stack
npm run build
DOCKER=true npm run build               # bila memakai skip kondisional
php artisan inertia:start-ssr           # bila SSR aktif; hentikan setelah halaman ter-render
grep -rnE "\broute\(" resources/js/                       # harus kosong (migrasi)
grep -rniE "ziggy|@routes" resources/ app/ config/ composer.json package.json   # harus kosong (migrasi)
```

Lalu buka setiap halaman yang memakai link/form/redirect dan pastikan tidak ada error di console. `route()` di Blade dan PHP adalah helper Laravel, bukan Ziggy, jadi biarkan. Bila grep di `resources/js/` masih menemukan `route(`, periksa apakah itu sisa Ziggy atau fungsi lain bernama sama.

## Troubleshooting

| Gejala | Penyebab | Solusi |
|---|---|---|
| `Cannot find module '@/actions/...'` | Belum di-generate, atau alias `@` belum ada | `php artisan wayfinder:generate`; cek alias Vite + tsconfig |
| `npm run build` gagal di stage Docker, stack trace dari `vite-plugin-wayfinder` | Plugin memanggil `php artisan`, stage hanya punya Node | [references/docker-and-ci.md](references/docker-and-ci.md) |
| `Could not load resources/js/routes/<name>` setelah deploy | Generate membaca route cache lama | `php artisan route:clear` sebelum `npm run build` |
| Export di `actions/` berupa objek ber-key URI, tidak bisa dipanggil | Satu method dipakai beberapa route | Import dari `@/routes/...` |
| Nama `deleteMethod`, bukan `delete` | `delete` reserved word JS | Pakai `deleteMethod()` |
| Route berubah tapi TypeScript tidak ikut | Dev server tidak jalan / plugin di-skip | Restart `vite dev` atau generate manual |
| Parameter salah / `.url()` tidak sesuai harapan | Signature berbeda dari dugaan | Baca file ter-generate untuk signature sebenarnya |

## Rujukan

- [references/api.md](references/api.md): baca saat menulis kode frontend yang memakai fungsi Wayfinder (parameter, query, form, Inertia per stack).
- [references/migrating-from-ziggy.md](references/migrating-from-ziggy.md): baca saat proyek sudah memakai Ziggy.
- [references/docker-and-ci.md](references/docker-and-ci.md): baca saat build frontend berjalan di Docker multi-stage atau CI tanpa PHP, atau saat menyiapkan skrip deploy.
