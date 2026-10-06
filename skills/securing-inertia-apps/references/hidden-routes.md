# Menyembunyikan Halaman Internal dari Bundle Vite

Detail untuk memecah bundle Inertia + Vite per role sehingga pengunjung publik tidak menerima daftar halaman admin/internal. Berlaku untuk Laravel + Inertia v1/v2 + Vite dengan React, Vue, atau Svelte.

## Daftar isi

- Cakupan stack
- Akar masalah dan apa yang terekspos
- Arsitektur: 2 entrypoint atau 3+
- Role-to-bundle mapping (wajib dibaca)
- Langkah implementasi
- URL auth per package
- Navigasi lintas bundle
- Diagnosis mismatch bundle
- Maintenance
- Verifikasi
- Sumber

## Cakupan stack

| Stack | Berlaku? |
|---|---|
| Laravel + Inertia + Vite + React/Vue/Svelte | Ya |
| Laravel + Inertia + Webpack (Mix) | Konsep sama, pakai `require.context` alih-alih `import.meta.glob` |
| Rails/Django + Inertia | Konsep sama; ganti `rootView()` dan Blade dengan mekanisme layout framework itu |
| Next.js, Nuxt, SvelteKit, Livewire | Tidak; routing/bundling berbeda |

Antar framework yang berubah hanya ekstensi dan casing folder di glob:

```typescript
import.meta.glob('./pages/**/*.tsx')     // React (starter kit baru: lowercase)
import.meta.glob('./Pages/**/*.vue')     // Vue
import.meta.glob('./Pages/**/*.svelte')  // Svelte
```

## Akar masalah dan apa yang terekspos

Starter kit (Breeze/Jetstream/starter kit resmi) me-resolve halaman dengan wildcard `import.meta.glob('./pages/**/*.tsx')`. Vite memang memecah tiap halaman menjadi chunk lazy, tetapi **peta seluruh path halaman beserta nama chunk-nya** tetap tertulis di bundle utama `app-<hash>.js` yang diunduh semua pengunjung.

| Terekspos | Contoh | Dampak |
|---|---|---|
| Path halaman admin | `./pages/admin/posts/index.tsx` | Struktur area admin terbaca |
| Nama chunk | `index-<hash>.js` | Chunk bisa di-fetch langsung tanpa login |
| Isi chunk | Label form, kolom tabel, URL endpoint | Petunjuk model data dan API |
| Dependency map | `__vite__mapDeps([...])` | Library yang dipakai |

Yang **tidak** terekspos: data database, props server, env var/secret, session. Risiko: rendah-sedang, mempermudah reconnaissance. Pemisahan bundle **bukan** kontrol akses; setiap route tetap wajib dilindungi middleware/policy di server.

## Arsitektur: 2 entrypoint atau 3+

Default: dua entrypoint.

```
Pengunjung publik                 User terautentikasi
app.blade.php                     admin.blade.php
  -> resources/js/app.tsx           -> resources/js/admin.tsx
     pages/public/**                   pages/admin/**, pages/auth/**,
                                       pages/dashboard.*, pages/settings/**
```

Multi-role (mis. public, member, admin): satu entrypoint per area.

```
app.blade.php   -> app.tsx    -> pages/public/**
member.blade.php -> member.tsx -> pages/member/**, pages/auth/**, pages/dashboard.*, pages/settings/**
admin.blade.php -> admin.tsx  -> pages/admin/**, pages/superadmin/**
```

```php
public function rootView(Request $request): string
{
    if ($request->is('admin', 'admin/*', 'superadmin', 'superadmin/*')) {
        return 'admin';
    }

    // Auth pages ikut bundle 'member' karena tujuan default setelah login adalah dashboard member.
    if ($request->is(
        'dashboard',
        'member', 'member/*',
        'settings', 'settings/*',
        'login', 'register',
        'forgot-password', 'reset-password/*',
    )) {
        return 'member';
    }

    return 'app';
}
```

## Role-to-bundle mapping (wajib dibaca)

Salah menempatkan halaman ke bundle menghasilkan error yang **hanya muncul setelah `npm run build`**. Dev server menyajikan semua file, jadi lolos dari testing lokal.

**Prinsip utama:** halaman auth (login, register, forgot/reset password) berada di bundle yang sama dengan tujuan redirect setelah auth sukses. Bila tidak, redirect ke `dashboard` me-resolve komponen yang tidak ada di bundle aktif dan muncul blank screen atau "Error undefined".

| Halaman | Bundle | Alasan |
|---|---|---|
| `login`, `register`, `forgot-password`, `reset-password` | Bundle tujuan default setelah login | Redirect pasca-auth tetap dalam satu bundle |
| `verify-email`, `confirm-password`, 2FA | Bundle terproteksi | User sudah login |
| `public/**` | `app` | Tanpa auth |
| `dashboard` | Bundle role pemiliknya | Spesifik role |
| `admin/**` | `admin` | |
| `member/**` | `member` | |
| `settings/**` | Bundle role pemilik (duplikasi bila tiap role punya) | |
| `Error` / 404 / 403 | **Semua bundle** | Bisa dirender dari mana saja |

### Kasus yang sering salah

**A. Glob dan middleware tidak sepakat.** `app.tsx` meng-glob `./pages/auth/register.tsx`, tetapi `rootView()` mengembalikan `'member'` untuk `/register`. Yang dimuat adalah `member.tsx`, yang tidak memuat register. Hasil di production: blank screen atau `Cannot find module "./pages/auth/register.tsx"`.

**B. Middleware lupa satu URL.** `member.tsx` memuat register, tetapi `rootView()` hanya mencocokkan `dashboard` dan `member/*`, sehingga `/register` jatuh ke `'app'`. Yang dimuat `app.tsx`; komponen tidak ada; "Error undefined".

Debug cepat bila halaman rusak di production tetapi jalan di dev:
1. URL itu cocok di cabang mana di `rootView()`?
2. Entrypoint bundle itu punya glob yang mencakup komponennya?
3. Entrypoint itu ada di `input` Vite?

### Strategi auth untuk multi-role

| Strategi | Kapan | Trade-off |
|---|---|---|
| A. Auth di bundle role terbanyak (default) | Mayoritas user satu role | Sederhana; role lain mengalami full reload setelah login |
| B. Bundle auth khusus (`auth.tsx`) | Form auth kompleks, banyak role | Tambah entrypoint + Blade + input Vite |
| C. Duplikasi glob auth di beberapa bundle | Hanya 2 role, halaman auth kecil | Sederhana; jalur kode terduplikasi, Error page juga harus diduplikasi |

### Sinkronisasi 3 arah

Setiap menambah/mengubah bundle atau halaman, ketiga titik ini harus cocok:

```
vite.config.ts (input)  <->  rootView() (nama Blade)  <->  <bundle>.tsx (import.meta.glob)
entry terdaftar              return = nama file Blade        glob mencakup semua halaman
                                                             untuk URL yang dipetakan ke sini
```

Contoh sinkron: `input` memuat `resources/js/member.tsx`; `rootView()` mengembalikan `'member'` untuk `/register`; `resources/views/member.blade.php` memuat `member.tsx`; `member.tsx` meng-glob `./pages/auth/**/*.tsx`.

## Langkah implementasi

### 1. Kelompokkan halaman

```bash
find resources/js/pages resources/js/Pages \( -name "*.tsx" -o -name "*.vue" -o -name "*.svelte" \) 2>/dev/null | sort
php artisan route:list --except-vendor
```

Kategorikan: publik, terproteksi, dan (opsional) per role. Bila halaman publik belum berada di subfolder sendiri, pindahkan ke `pages/public/` lalu perbarui nama komponen di controller (`Inertia::render('public/home')`).

### 2. Entrypoint publik

React (`app.tsx`):

```typescript
import '../css/app.css';
import { createInertiaApp } from '@inertiajs/react';
import { resolvePageComponent } from 'laravel-vite-plugin/inertia-helpers';

createInertiaApp({
    resolve: (name) =>
        resolvePageComponent(`./pages/${name}.tsx`, import.meta.glob('./pages/public/**/*.tsx')),
    // setup, progress: seperti semula
});
```

Vue (`app.js`):

```javascript
createInertiaApp({
    resolve: (name) =>
        resolvePageComponent(`./Pages/${name}.vue`, import.meta.glob('./Pages/Public/**/*.vue')),
    // ...
});
```

Svelte (`app.ts`), tanpa `resolvePageComponent`, pakai lookup manual:

```typescript
import { createInertiaApp } from '@inertiajs/svelte';
import { mount, type Component } from 'svelte';

type PageModule = { default: Component };

const pages: Record<string, PageModule> = {
    ...import.meta.glob<PageModule>('./Pages/Public/**/*.svelte', { eager: true }),
    ...import.meta.glob<PageModule>('./Pages/Error.svelte', { eager: true }),
    // Tambahkan './Pages/Auth/**' di sini HANYA bila tujuan pasca-login ada di bundle ini
};

createInertiaApp({
    resolve: (name) => {
        const page = pages[`./Pages/${name}.svelte`];
        if (!page) {
            console.error(`Page not found in this bundle: ${name}`);
            return pages['./Pages/Error.svelte'];
        }
        return page;
    },
    setup({ el, App, props }) {
        mount(App, { target: el!, props });
        delete el!.dataset.page;
    },
});
```

`{ eager: true }` membuat halaman langsung tersedia tanpa dynamic import. Fallback ke Error page mencegah blank screen.

### 3. Entrypoint admin

React (`admin.tsx`):

```typescript
import '../css/app.css';
import { createInertiaApp } from '@inertiajs/react';
import { resolvePageComponent } from 'laravel-vite-plugin/inertia-helpers';

const pages = {
    ...import.meta.glob('./pages/admin/**/*.tsx'),
    ...import.meta.glob('./pages/auth/**/*.tsx'),
    ...import.meta.glob('./pages/dashboard.tsx'),
    ...import.meta.glob('./pages/settings/**/*.tsx'),
};

createInertiaApp({
    resolve: (name) => resolvePageComponent(`./pages/${name}.tsx`, pages),
    // setup sama dengan app.tsx
});
```

Vue (`admin.js`): pola yang sama dengan `./Pages/Admin/**/*.vue`, `./Pages/Auth/**/*.vue`, `./Pages/Dashboard.vue`, `./Pages/Settings/**/*.vue`.

Svelte (`admin.ts`): salin entrypoint publik, ganti isi `pages` dengan glob `./Pages/Admin/**`, `./Pages/Auth/**`, dan `./Pages/Error.svelte`.

Import yang khusus admin (inisialisasi tabel, editor, hook admin) hanya boleh ada di `admin.*`.

### 4. Blade layout admin

`resources/views/admin.blade.php`: salinan `app.blade.php` yang memuat entrypoint admin, menambah `noindex`, dan membuang meta OG/SEO.

```blade
<!DOCTYPE html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="robots" content="noindex, nofollow">
        <title inertia>{{ config('app.name') }}</title>
        @viteReactRefresh {{-- hanya React; hapus untuk Vue/Svelte --}}
        @vite(['resources/css/app.css', 'resources/js/admin.tsx'])
        @inertiaHead
    </head>
    <body class="font-sans antialiased">
        @inertia
    </body>
</html>
```

Jangan menambahkan `"resources/js/pages/{$page['component']}.tsx"` ke `@vite()`; split sudah dilakukan per entrypoint.

### 5. Arahkan layout lewat middleware

```php
// app/Http/Middleware/HandleInertiaRequests.php
public function rootView(Request $request): string
{
    // Auth pages ikut bundle tujuan pasca-login (di sini: dashboard di bundle admin).
    if ($request->is(
        'dashboard',
        'admin', 'admin/*',
        'login', 'register',
        'forgot-password', 'reset-password/*',
        'settings', 'settings/*',
    )) {
        return 'admin';
    }

    return 'app';
}
```

Pakai `$request->is()` (path URL), bukan `routeIs()`, karena nama route dari Fortify/Breeze/Jetstream berbeda-beda. Setelah mengubah `rootView()`, cek ulang sinkronisasi 3 arah.

### 6. Vite config

```typescript
laravel({
    input: [
        'resources/css/app.css',
        'resources/js/app.tsx',
        'resources/js/admin.tsx',
    ],
    ssr: 'resources/js/ssr.tsx',
    refresh: true,
}),
```

### 7. SSR (bila ada)

Bundle SSR berjalan di server dan tidak diunduh browser, jadi tetap pakai wildcard agar semua halaman bisa dirender:

```typescript
// resources/js/ssr.tsx
createServer((page) =>
    createInertiaApp({
        page,
        resolve: (name) =>
            resolvePageComponent(`./pages/${name}.tsx`, import.meta.glob('./pages/**/*.tsx')),
        // ...
    }),
);
```

Pastikan direktori output SSR (`bootstrap/ssr`) tidak disajikan secara publik.

## URL auth per package

Path yang perlu dimasukkan ke `rootView()`:

```php
// Breeze
'login', 'register', 'forgot-password', 'reset-password/*', 'verify-email', 'verify-email/*', 'confirm-password',

// Fortify (+ Jetstream)
'login', 'register', 'forgot-password', 'reset-password/*', 'email/verify', 'email/verify/*',
'user/confirm-password', 'user/two-factor-authentication', 'two-factor-challenge',
```

Auth custom: cek path aktual.

```bash
php artisan route:list --columns=uri,name | grep -E "login|register|password|verify|two-factor"
```

## Navigasi lintas bundle

Saat Inertia berpindah via XHR ke halaman milik bundle lain (login publik ke dashboard admin, logout dari admin ke beranda, link publik di sidebar admin), komponen tujuan tidak ada di bundle aktif. Harus dipaksa full page load agar server mengirim Blade dan bundle yang benar.

**Cara utama: bedakan asset version per root view.** Inertia membandingkan header `X-Inertia-Version` pada setiap kunjungan GET; bila beda, server membalas 409 + `X-Inertia-Location` dan client melakukan full page load ke URL tujuan. Dengan memasukkan nama root view ke version, setiap perpindahan bundle otomatis menjadi full reload, termasuk redirect setelah POST login/logout:

```php
public function version(Request $request): ?string
{
    return parent::version($request).'|'.$this->rootView($request);
}
```

**Jaring pengaman di setiap entrypoint:** bila komponen tetap tidak ditemukan, jangan diam-diam blank.

```typescript
resolve: (name) => {
    const page = pages[`./Pages/${name}.svelte`];
    if (!page) {
        window.location.reload(); // biarkan server memilih bundle lewat rootView()
        return pages['./Pages/Error.svelte'];
    }
    return page;
},
```

`reload()` memuat ulang URL yang sedang aktif (saat `resolve` dipanggil, history belum berpindah). Itu bekerja untuk redirect pasca-login (halaman `/login` me-redirect user yang sudah login), tetapi tidak untuk klik link biasa ke bundle lain, sehingga pendekatan version tetap yang utama. Untuk link yang sengaja lintas bundle, pakai `<a href>` biasa, bukan `<Link>` Inertia.

Skenario yang wajib diuji di build production:

| Dari | Ke | Pemicu |
|---|---|---|
| Halaman login | Dashboard (bundle lain) | Login sukses |
| Bundle admin | Beranda publik | Logout |
| Bundle admin | Halaman publik | Klik link |
| Bundle publik | Halaman admin | Deep link/bookmark |

## Diagnosis mismatch bundle

| Gejala | Kemungkinan penyebab |
|---|---|
| Blank screen di halaman tertentu (production saja) | Komponen tidak ada di bundle yang dipilih `rootView()` |
| `Cannot find module "./pages/xxx.tsx"` | `rootView()` mengarah ke bundle yang glob-nya tidak mencakup halaman ini |
| "Error undefined" setelah submit login/register/reset | Tujuan redirect ada di bundle lain tanpa full reload |
| Halaman muncul sebentar lalu blank | Resolve gagal saat navigasi SPA |
| Jalan di `npm run dev`, rusak setelah `npm run build` | Dev menyajikan semua file; build memecah ketat per entrypoint |
| `admin-*.js` termuat di halaman publik | `rootView()` mengembalikan layout yang salah untuk URL itu |

Alur diagnosis: DevTools > Network > filter JS > refresh halaman bermasalah > lihat bundle yang termuat > cocokkan dengan cabang `rootView()` > buka entrypoint itu dan cek glob > perbaiki glob, pindahkan halaman, atau ubah pemetaan URL.

## Maintenance

| Skenario | Tindakan |
|---|---|
| Halaman publik baru di `pages/public/` | Otomatis tercakup glob |
| Halaman admin baru di folder admin yang sudah ada | Otomatis tercakup glob |
| Halaman di folder baru (`pages/reports/`) | Tambah glob di entrypoint tujuan + pola URL di `rootView()` |
| Route terproteksi baru | Pastikan pola URL ada di `rootView()` dan halamannya ada di glob bundle itu |

Jebakan lain:
- Kedua entrypoint harus meng-import CSS yang sama agar tampilan konsisten.
- Komponen bersama (layout, UI kit) boleh di-import dari kedua bundle; yang dihindari adalah halaman dan modul khusus admin di bundle publik.
- `@viteReactRefresh` hanya untuk React.

## Verifikasi

Setelah `npm run build` (lokal dengan `APP_ENV=production` atau di staging):

```bash
# 1. Ambil bundle publik yang dimuat halaman beranda (tanpa login)
curl -s https://example.com/ | grep -oE '/build/assets/[A-Za-z0-9_.-]+\.js' | sort -u

# 2. Cari jejak area internal di bundle publik; seharusnya tidak ada hasil
curl -s https://example.com/build/assets/app-<hash>.js | grep -oE '\./[Pp]ages/(admin|Admin|dashboard|settings)[^"]*' | sort -u

# 3. Atau langsung di hasil build lokal
grep -lE '[Pp]ages/(admin|Admin)/' public/build/assets/app-*.js
```

Lalu di browser: buka situs tanpa login dan pastikan hanya `app-*.js` yang termuat; login dan pastikan `admin-*.js` termuat dan semua menu admin berfungsi; jalankan tabel skenario lintas bundle di atas.

## Sumber

- [Inertia: Code splitting](https://inertiajs.com/code-splitting)
- [Inertia: Server-side setup, root template](https://inertiajs.com/server-side-setup#root-template)
- [Inertia: Asset versioning](https://inertiajs.com/asset-versioning)
- [Vite: Glob import](https://vite.dev/guide/features.html#glob-import)
- [Laravel: Vite](https://laravel.com/docs/vite)
- [laravel/vite-plugin#97: multiple entrypoints](https://github.com/laravel/vite-plugin/issues/97)
- [OWASP WSTG: Information gathering](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/)
