# API Fungsi Wayfinder

Kode hasil generate adalah TypeScript biasa, jadi cara import dan pemanggilannya sama di Svelte, React, dan Vue. Yang berbeda hanya adapter Inertia dan sintaks template.

## Daftar isi

- Actions vs routes
- Nilai kembali dan method variant
- Parameter
- Query parameter
- Invokable controller dan import seluruh controller
- Satu method untuk beberapa route
- Form variant
- Integrasi Inertia (Svelte, React, Vue)
- Fitur branch `next`

## Actions vs routes

```typescript
// Berdasarkan controller: resources/js/actions/App/Http/Controllers/PostController.ts
import { show, index, store } from '@/actions/App/Http/Controllers/PostController';

// Berdasarkan named route: post.show → resources/js/routes/post.ts
import { show } from '@/routes/post';
import { index } from '@/routes/admin/user';   // admin.user.index
```

Pilih `@/routes/...` bila route punya nama dan padanannya dengan `route('nama')` Ziggy perlu jelas, atau bila controller method dipakai lebih dari satu route. Pilih `@/actions/...` bila route tidak diberi nama. Bentrok nama antar-import diatasi dengan alias: `import { edit as profileEdit } from '@/routes/admin/profile'`.

## Nilai kembali dan method variant

```typescript
show(1);          // { url: '/posts/1', method: 'get' }
show.url(1);      // '/posts/1'
show.get(1);      // { url: '/posts/1', method: 'get' }
show.head(1);     // { url: '/posts/1', method: 'head' }
```

## Parameter

```typescript
// Satu parameter
show(1);
show({ id: 1 });

// Beberapa parameter: array (urutan) atau object (nama)
update([1, 2]);
update({ post: 1, author: 2 });
update({ post: { id: 1 }, author: { id: 2 } });   // object model

// Route dengan binding key, mis. /posts/{post:slug}
show('my-post-slug');
show({ slug: 'my-post-slug' });
```

Bila ragu bentuk parameternya, buka file ter-generate dan baca tipe argumennya.

## Query parameter

Argumen terakhir (opsional) adalah `options`:

```typescript
index({ query: { page: 1, sort_by: 'name' } });   // { url: '/posts?page=1&sort_by=name', method: 'get' }
show.url(1, { query: { page: 2 } });              // '/posts/1?page=2'
```

`mergeQuery` menggabungkan dengan query di URL saat ini (`window.location.search`). Nilai `null`/`undefined` menghapus parameter:

```typescript
// window.location.search = '?page=1&sort_by=category&q=shirt'
show.url(1, { mergeQuery: { page: 2, sort_by: 'name' } });  // '/posts/1?page=2&sort_by=name&q=shirt'
show.url(1, { mergeQuery: { page: 2, sort_by: null } });    // '/posts/1?page=2&q=shirt'
```

`mergeQuery` membaca `window`, jadi jangan dipakai di kode yang dieksekusi saat SSR.

## Invokable controller dan import seluruh controller

```typescript
import StorePostController from '@/actions/App/Http/Controllers/StorePostController';
StorePostController();            // { url: '/posts', method: 'post' }

import PostController from '@/actions/App/Http/Controllers/PostController';
PostController.show(1);           // bekerja, tetapi semua action ikut masuk bundle
```

Reserved word JS sebagai nama method (`delete`, `import`, dst.) diberi akhiran `Method`: `deleteMethod()`, `importMethod()`.

## Satu method untuk beberapa route

Bila dua route atau lebih menunjuk ke method controller yang sama, export di `actions/` menjadi dictionary ber-key URI, bukan fungsi:

```php
Route::get('clients/{client}/payments', [ClientPaymentsController::class, 'index'])->name('clients.payments.index');
Route::get('clients/{client}/payments-archive', [ClientPaymentsController::class, 'index'])->name('clients.payments.archive');
```

```typescript
import { index } from '@/actions/App/Http/Controllers/ClientPaymentsController';
index['/clients/{client}/payments']({ client: 1 });

// Lebih mudah: pakai named route
import { index as paymentsIndex } from '@/routes/clients/payments';
paymentsIndex({ client: 1 });   // { url: '/clients/1/payments', method: 'get' }
```

Bila URI sama dan hanya beda verb, key diberi prefix verb (`'get /exports/{report}'`, `'post /exports/{report}'`, atau `'put|patch ...'`). Bentuk export untuk kasus ini pernah berubah antar versi beta (versi lebih lama menghasilkan nama ber-hash), jadi bila yang terlihat berbeda, ikuti file ter-generate.

## Form variant

Aktifkan dengan `php artisan wayfinder:generate --with-form` atau `wayfinder({ formVariants: true })`. Berguna untuk `<form>` HTML biasa (non-Inertia):

```svelte
<script lang="ts">
  import { store, update } from '@/actions/App/Http/Controllers/PostController';
</script>

<form {...store.form()}>          <!-- action="/posts" method="post" -->
  <input name="title" />
  <button type="submit">Create</button>
</form>

<form {...update.form(1)}>        <!-- action="/posts/1?_method=PATCH" method="post" -->
  <input name="title" />
</form>

<form {...update.form.put(1)}>    <!-- action="/posts/1?_method=PUT" method="post" -->
</form>
```

React: `<form {...store.form()}>`. Vue: `<form v-bind="store.form()">`.

## Integrasi Inertia (Svelte, React, Vue)

`.url()` selalu bekerja untuk `router`, `useForm`, dan `<Link>`. Versi Inertia yang punya dukungan Wayfinder juga menerima objek `{ url, method }` langsung, mis. `form.submit(store())` dan `<Link href={show(1)}>`. Cek versi `@inertiajs/*` di proyek sebelum memakai bentuk objek.

### Svelte

```svelte
<script lang="ts">
  import { router, Link, useForm } from '@inertiajs/svelte';
  import { show, store } from '@/actions/App/Http/Controllers/PostController';
  import { destroy } from '@/actions/App/Http/Controllers/SessionController';

  let { sessionId }: { sessionId: number } = $props();

  router.visit(show.url(1));

  const form = useForm({ title: 'My Post' });
  $form.post(store.url());
  $form.delete(destroy.url(sessionId), { preserveScroll: true });
</script>

<Link href={show.url(1)}>View Post</Link>
```

### React

```tsx
import { router, Link, useForm } from '@inertiajs/react';
import { show, store } from '@/actions/App/Http/Controllers/PostController';
import { destroy } from '@/actions/App/Http/Controllers/SessionController';

export default function PostPage({ sessionId }: { sessionId: number }) {
    const { post, delete: formDelete } = useForm({ title: 'My Post' });

    const save = () => post(store.url());
    const logout = () => formDelete(destroy.url(sessionId), { preserveScroll: true });
    const open = () => router.visit(show.url(1));

    return <Link href={show.url(1)}>View Post</Link>;
}
```

### Vue

```vue
<script setup lang="ts">
import { router, Link, useForm } from '@inertiajs/vue3';
import { show, store } from '@/actions/App/Http/Controllers/PostController';
import { destroy } from '@/actions/App/Http/Controllers/SessionController';

const props = defineProps<{ sessionId: number }>();

router.visit(show.url(1));

const form = useForm({ title: 'My Post' });
form.post(store.url());
form.delete(destroy.url(props.sessionId), { preserveScroll: true });
</script>

<template>
    <Link :href="show.url(1)">View Post</Link>
</template>
```

### Perbedaan antar stack

| Aspek | Svelte | React | Vue |
|---|---|---|---|
| Paket Inertia | `@inertiajs/svelte` | `@inertiajs/react` | `@inertiajs/vue3` |
| Akses `useForm` | `$form.post()` (store) | `post()` dari hook | `form.post()` |
| Binding `href` | `href={...}` | `href={...}` | `:href="..."` |
| Import Wayfinder, `.url()`, Vite plugin, Docker/CI | sama | sama | sama |

## Fitur branch `next`

Branch `next` (beta, `composer require laravel/wayfinder:dev-next`) menambahkan generate tipe untuk Form Request (dari rules validasi), atribut/cast model Eloquent, enum PHP (union type + konstanta), props halaman Inertia, channel broadcast, dan `import.meta.env`. Jangan pakai di proyek produksi tanpa persetujuan pengguna karena API-nya belum stabil, dan cek README branch itu untuk nama perintah/opsi terkini.
