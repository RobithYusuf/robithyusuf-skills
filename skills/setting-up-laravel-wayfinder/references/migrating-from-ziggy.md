# Migrasi dari Ziggy ke Wayfinder

Kerjakan setelah langkah 1-4 di SKILL.md (Wayfinder terpasang dan sudah di-generate), supaya setiap `route()` yang diganti bisa langsung dicek tipenya.

## Daftar isi

- Ziggy vs Wayfinder
- Langkah 5: inventaris
- Langkah 6: ganti pemanggilan `route()` (pemetaan, actions vs routes, satu method untuk beberapa route, Inertia)
- Langkah 7: bongkar infrastruktur Ziggy
- Checklist migrasi

## Ziggy vs Wayfinder

| Aspek | Ziggy | Wayfinder |
|---|---|---|
| Cara kerja | Serialize route ke JSON, dikirim lewat `@routes` / shared prop | Generate fungsi TypeScript saat build |
| Keamanan | Daftar route terlihat di page source, perlu filter manual | Tidak ada daftar route di browser |
| Bundle | JSON route dimuat tiap halaman | Hanya fungsi yang di-import (tree-shakeable) |
| Tipe | Deklarasi manual | Tipe parameter ter-generate |
| SSR | Perlu data Ziggy di konteks server | Import biasa, tanpa setup |
| Runtime | Butuh library Ziggy di browser | Tanpa dependensi runtime |
| Pemanggilan | `route('posts.show', { post: 1 })` | `show.url(1)` atau `show.url({ post: 1 })` |

## Langkah 5: inventaris

Kumpulkan semua titik sentuh Ziggy sebelum mengubah apa pun, lalu tulis daftarnya (file:baris) supaya tidak ada yang terlewat:

```bash
# Paket
grep -n "ziggy" composer.json package.json

# Pemanggilan di frontend
grep -rnE "\broute\(" resources/js/
grep -rnE "route\(\)\.current|route\(\)\.has|route\(\)\.params" resources/js/

# Infrastruktur
grep -rn "@routes" resources/views/
grep -rn "Ziggy\|ziggy" app/ config/ resources/js/ routes/
ls config/ziggy.php 2>/dev/null
```

Titik sentuh yang umum:

| Lokasi | Isi khas |
|---|---|
| Layout Blade utama (mis. `resources/views/app.blade.php`) | `@routes`, kadang `@routes('group')` bercabang per role |
| `app/Http/Middleware/HandleInertiaRequests.php` | `use Tighten\Ziggy\Ziggy;`, shared prop `'ziggy' => ...`, method helper untuk memfilter route |
| `config/ziggy.php` | Group / only / except route |
| `resources/js/types/*.d.ts` | `declare function route(...)`, `Window.route` |
| Entry JS (`resources/js/app.ts`, `ssr.ts`) | Fallback `window.route = ...`, `ZiggyVue` / `route` dari `ziggy-js`, pemasangan `Ziggy` di SSR |
| Komponen / halaman | `route('nama', params)`, `route().current('nama')` |

## Langkah 6: ganti pemanggilan `route()`

### Actions vs routes

Nama route Ziggy (`admin.user.index`) dipetakan paling jelas ke `@/routes/...` (`import { index } from '@/routes/admin/user'`). Pakai `@/actions/App/Http/Controllers/...` untuk route tanpa nama. Pakai `@/routes/...` juga bila satu method controller dipakai beberapa route (lihat di bawah). Bentrok nama antar-import diatasi dengan alias: `import { edit as profileEdit } from '@/routes/admin/profile'`.

### Pemetaan

| Ziggy | Wayfinder |
|---|---|
| `route('admin.dashboard')` | `import { dashboard } from '@/routes/admin'` → `dashboard.url()` |
| `route('posts.show', post.id)` | `import { show } from '@/routes/posts'` → `show.url(post.id)` |
| `route('posts.show', post.slug)` (route `/posts/{post:slug}`) | `show.url(post.slug)` atau `show.url({ slug: post.slug })` |
| `route('posts.update', { post: 1, author: 2 })` | `update.url({ post: 1, author: 2 })` atau berurutan `update.url([1, 2])` |
| `route('posts.index', { page: 2 })` (param di luar URI jadi query) | `index.url({ query: { page: 2 } })` |
| `route('posts.index', { ...route().params, page: 2 })` | `index.url({ mergeQuery: { page: 2 } })`; nilai `null`/`undefined` menghapus parameter |
| `route('posts.show', 1, true)` (absolute) | `` `${window.location.origin}${show.url(1)}` `` atau kirim URL absolut dari server |
| `route().current('posts.*')` | Tidak ada padanan langsung. Bandingkan `page.url` Inertia dengan `index.url()` (`startsWith`), atau kirim flag aktif dari server |
| `<form action={route('posts.store')} method="post">` (form HTML non-Inertia) | `<form {...store.form()}>` (Vue: `v-bind`), butuh form variant: `wayfinder({ formVariants: true })` dan `--with-form` saat generate manual, keduanya disamakan supaya file ter-generate tidak berganti-ganti |

Ziggy memperlakukan parameter yang tidak ada di URI sebagai query string. Wayfinder tidak, jadi pindahkan ke `{ query: {...} }`. `mergeQuery` membaca `window.location.search`, jadi jangan dipakai di kode yang dieksekusi saat SSR.

### Inertia: `.url()` sebagai pengganti langsung

`route(...)` menghasilkan string, jadi pengganti paling aman adalah `.url()` (juga string) untuk `router.visit`, `form.post/delete(...)`, dan `href`. Ini bekerja di semua versi Inertia. Bentuk objek (`form.submit(store())`, `<Link href={show(1)}>`) hanya untuk versi `@inertiajs/*` yang sudah mendukung Wayfinder, cek versinya sebelum memakainya. Sintaks per stack tidak berubah dari versi Ziggy: Svelte `$form.delete(...)`, React `delete` dari hook `useForm`, Vue `form.delete(...)` dan `:href="..."`.

### Satu method controller untuk beberapa route

Bila dua route atau lebih menunjuk ke method controller yang sama (mis. `ProfileController@edit` untuk `/profile` dan `/admin/profile`), export di `actions/` menjadi dictionary ber-key URI, bukan fungsi:

```php
Route::get('clients/{client}/payments', [ClientPaymentsController::class, 'index'])->name('clients.payments.index');
Route::get('clients/{client}/payments-archive', [ClientPaymentsController::class, 'index'])->name('clients.payments.archive');
```

```typescript
import { index } from '@/actions/App/Http/Controllers/ClientPaymentsController';
index['/clients/{client}/payments']({ client: 1 });

// Lebih mudah, dan padanannya dengan nama route Ziggy langsung terlihat:
import { index as paymentsIndex } from '@/routes/clients/payments';
paymentsIndex.url({ client: 1 });   // '/clients/1/payments'
```

Bila URI sama dan hanya beda verb, key diberi prefix verb (`'get /exports/{report}'`, `'post /exports/{report}'`, atau `'put|patch ...'`). Bentuk export untuk kasus ini pernah berubah antar versi beta (versi lebih lama menghasilkan nama ber-hash), jadi bila yang terlihat berbeda, ikuti file ter-generate.

### Contoh sebelum/sesudah

Svelte; React/Vue sama polanya:

```svelte
<!-- SEBELUM -->
<script lang="ts">
  function logoutSession() {
    $logoutForm.delete(route('sessions.destroy', selectedSessionId!), {
      preserveScroll: true,
      onSuccess: () => { showLogoutModal = false; },
    });
  }
  function logoutOtherSessions() {
    $logoutOthersForm.delete(route('sessions.destroy-others'), { preserveScroll: true });
  }
  const breadcrumbs = [
    { label: 'Dashboard', href: route('admin.dashboard') },
    { label: 'Profile', href: route('admin.profile.edit') },
  ];
</script>

<!-- SESUDAH -->
<script lang="ts">
  // Controller tanpa bentrok → actions
  import { destroy, destroyOthers } from '@/actions/App/Http/Controllers/SessionController';
  // ProfileController dipakai di /profile dan /admin/profile → named routes
  import { dashboard } from '@/routes/admin';
  import { edit as profileEdit } from '@/routes/admin/profile';

  function logoutSession() {
    $logoutForm.delete(destroy.url(selectedSessionId!), {
      preserveScroll: true,
      onSuccess: () => { showLogoutModal = false; },
    });
  }
  function logoutOtherSessions() {
    $logoutOthersForm.delete(destroyOthers.url(), { preserveScroll: true });
  }
  const breadcrumbs = [
    { label: 'Dashboard', href: dashboard.url() },
    { label: 'Profile', href: profileEdit.url() },
  ];
</script>
```

Catatan:
- Nama fungsi di `actions/` mengikuti nama method controller dalam camelCase (`destroyOthers`), sedangkan di `routes/` mengikuti segmen terakhir nama route. Cek file ter-generate bila ragu, terutama untuk nama route ber-tanda hubung.
- Method bernama reserved word JS diberi akhiran `Method` (`delete` → `deleteMethod`, `import` → `importMethod`); `destroy` tetap `destroy`. Invokable controller di-import sebagai default export lalu dipanggil langsung: `import StorePostController from '@/actions/App/Http/Controllers/StorePostController'` → `StorePostController.url()`.
- Kerjakan per file, lalu jalankan type-check (`npx tsc --noEmit` / `svelte-check` / `vue-tsc`) setelah tiap file. Hapus deklarasi global `route()` di langkah 7 justru membantu: setiap sisa pemanggilan akan muncul sebagai error tipe.

## Langkah 7: bongkar infrastruktur Ziggy

**Blade.** Hapus seluruh blok `@routes`, termasuk percabangan per role:

```diff
  <!-- Scripts -->
- @auth
-     @if(auth()->user()->hasRole('admin'))
-         @routes('admin')
-     @else
-         @routes('public')
-     @endif
- @else
-     @routes('public')
- @endauth
  @vite(['resources/css/app.css', 'resources/js/app.ts'])
  @inertiaHead
```

Filter route per role di Ziggy berfungsi menyembunyikan *nama dan URL* route admin dari pengguna biasa. Dengan Wayfinder, URL hanya ada di chunk JS yang meng-import-nya. Halaman admin yang di-code-split per halaman (pola default Inertia `resolvePageComponent` / `import.meta.glob`) tidak termuat untuk pengguna non-admin. Akses tetap harus dijaga middleware/policy di server.

**Middleware.**

```diff
  namespace App\Http\Middleware;

  use Illuminate\Http\Request;
  use Inertia\Middleware;
- use Tighten\Ziggy\Ziggy;

  // di share():
-     'ziggy' => fn () => [...(new Ziggy)->toArray(), 'location' => $request->url()],
  // atau:
-     'ziggy' => fn () => $this->getZiggyData($request),

- // hapus juga method helper Ziggy (mis. getZiggyData())
```

Bila frontend membaca `page.props.ziggy.location` untuk URL saat ini, ganti dengan `page.url` dari Inertia.

**Tipe global** (mis. `resources/js/types/global.d.ts`):

```diff
  declare global {
-     function route(name: string, params?: Record<string, unknown> | number | string, absolute?: boolean): string;
-     function route(): { current: (name: string) => boolean };
      interface Window {
-         route: typeof route;
          axios: AxiosStatic;   // pertahankan bila axios masih dipakai
      }
  }
```

Hapus juga tipe `ziggy` dari interface page props bila ada.

**Entry JS** (`app.ts`, `ssr.ts`):

```diff
- window.route = window.route || function (): string {
-     console.warn('Route function not available. Make sure Ziggy is loaded.');
-     return '#';
- };
```

Setup berbasis `ziggy-js` (umum di starter kit Vue/React lama):

```diff
- import { ZiggyVue } from 'ziggy-js';
  createApp({ render: () => h(App, props) })
      .use(plugin)
-     .use(ZiggyVue)
      .mount(el);
```

Di `ssr.ts`, hapus pemasangan Ziggy (`.use(ZiggyVue, { ...page.props.ziggy, location: ... })` atau `global.route = ...`).

**Paket dan config.**

```bash
rm -f config/ziggy.php
composer remove tightenco/ziggy
npm uninstall ziggy-js        # hanya bila ada di package.json
```

Hapus juga alias Vite ke `vendor/tightenco/ziggy` bila ada.

**Dokumentasi proyek.** Perbarui README/AGENTS.md/CONTRIBUTING yang masih menyebut `route()` atau Ziggy.

## Checklist migrasi

```
- [ ] composer require laravel/wayfinder && npm install -D @laravel/vite-plugin-wayfinder
- [ ] php artisan wayfinder:generate (cek resources/js/actions/ dan routes/)
- [ ] vite.config: wayfinder() (kondisional bila ada build tanpa PHP)
- [ ] .gitignore sesuai strategi build
- [ ] Inventaris semua route(), route().current, @routes, ziggy
- [ ] Ganti setiap route() di resources/js/ dengan import Wayfinder
- [ ] Ganti route().current dan props.ziggy.location
- [ ] Hapus @routes dari Blade
- [ ] Hapus import Ziggy, shared prop ziggy, dan helper-nya dari HandleInertiaRequests
- [ ] Hapus deklarasi route() / Window.route / tipe ziggy
- [ ] Hapus fallback window.route, ZiggyVue, setup Ziggy di SSR
- [ ] rm config/ziggy.php; composer remove tightenco/ziggy; npm uninstall ziggy-js (bila ada)
- [ ] Type-check + npm run build (+ DOCKER=true npm run build bila dipakai)
- [ ] SSR jalan tanpa error
- [ ] grep: tidak ada route( di resources/js/, tidak ada ziggy/@routes tersisa
- [ ] Uji manual semua halaman yang memakai link/form
- [ ] Update Dockerfile/CI dan dokumentasi proyek
```
