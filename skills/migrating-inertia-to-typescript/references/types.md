# Fase 2: Type Definitions

## Daftar isi

- Aturan memetakan JSON Laravel ke type
- types/index.ts
- Pagination: dua bentuk berbeda
- types/global.d.ts dengan InertiaConfig
- Mengapa @inertiajs/core
- Fallback: Inertia v2 awal tanpa InertiaConfig
- Generic Inertia yang berguna

## Aturan memetakan JSON Laravel ke type

Type harus menggambarkan JSON yang **diterima browser**, bukan skema database. Sumber kebenarannya, berurutan: API Resource (`toArray`), array di `Inertia::render(...)`, lalu `$hidden`/`$appends`/`$casts` di model.

| Di Laravel | Di TypeScript | Alasan |
|---|---|---|
| Kolom `timestamp`/`date` | `string` | Diserialisasi ke ISO string, bukan `Date` |
| Kolom nullable | `T \| null` | JSON mengirim `null`, bukan `undefined` |
| Cast `decimal:2` | `string` | Laravel mengirim decimal sebagai string agar presisi terjaga |
| Cast `integer`/`float`/`boolean` | `number`/`boolean` | Tanpa cast, MySQL bisa mengirim angka sebagai string |
| Relasi via `with()` | `relation?: T` | Hanya ada bila di-eager-load |
| `withCount('x')` | `x_count?: number` | Hanya ada pada query tertentu |
| Accessor di `$appends` | field biasa | Selalu ikut terserialisasi |
| Kolom enum / status | union literal | Autocomplete dan exhaustive check |
| Field di `$hidden` | tidak ada | Jangan diketik, tidak pernah sampai ke browser |

Bila ragu, lihat JSON aslinya: `dd()` sementara di controller, atau buka tab Network di browser dan periksa response Inertia (`X-Inertia: true`).

## types/index.ts

Struktur dasar. Model auth dan pagination hampir selalu ada; model domain mengikuti aplikasi. Untuk proyek besar, pecah per domain (`types/models/user.ts`, dst.) lalu re-export dari `index.ts`.

```ts
// ============ AUTH & USER ============
export interface Permission {
    id: number;
    name: string;
    guard_name: string;
}

export interface Role {
    id: number;
    name: string;
    guard_name: string;
    permissions?: Permission[];
}

export interface User {
    id: number;
    name: string;
    email: string;
    email_verified_at: string | null;
    avatar: string | null;
    roles?: Role[] | string[];   // objek Role atau hanya nama, tergantung Resource
    created_at: string;
    updated_at: string;
}

// ============ CONTOH MODEL DOMAIN ============
export type ProductStatus = 'draft' | 'active' | 'archived';

export interface ProductImage {
    id: number;
    image_path: string;
    sort_order: number;
}

export interface Category {
    id: number;
    name: string;
    slug: string;
    products_count?: number;      // dari withCount
}

export interface Product {
    id: number;
    name: string;
    slug: string;
    description: string | null;
    price: string;                // cast decimal → string
    stock: number;
    status: ProductStatus;
    category_id: number;
    category?: Category;          // hanya bila di-eager-load
    images: ProductImage[];
    main_image_url: string | null; // accessor di $appends
    reviews_avg_rating?: number;
    created_at: string;
    updated_at: string;
}

// Status dengan banyak nilai: union literal + map label bertipe
export type OrderStatus = 'pending' | 'paid' | 'processing' | 'shipped' | 'completed' | 'cancelled';

export const orderStatusLabel: Record<OrderStatus, string> = {
    pending: 'Menunggu',
    paid: 'Dibayar',
    processing: 'Diproses',
    shipped: 'Dikirim',
    completed: 'Selesai',
    cancelled: 'Dibatalkan',
};

// ============ UTIL ============
export interface SelectOption<V = string> {
    value: V;
    label: string;
}

export interface Flash {
    success?: string;
    error?: string;
    warning?: string;
    info?: string;
}
```

`Record<OrderStatus, string>` membuat compiler menolak bila ada status baru yang lupa diberi label.

## Pagination: dua bentuk berbeda

Laravel mengirim dua bentuk JSON yang berbeda. Periksa mana yang dipakai controller sebelum memilih type.

```ts
export interface PaginationLink {
    url: string | null;
    label: string;
    active: boolean;
}

// 1) Model::paginate() dikirim langsung → bentuk datar
export interface Paginator<T> {
    data: T[];
    current_page: number;
    last_page: number;
    per_page: number;
    total: number;
    from: number | null;
    to: number | null;
    path: string;
    first_page_url: string;
    last_page_url: string;
    next_page_url: string | null;
    prev_page_url: string | null;
    links: PaginationLink[];
}

// 2) XResource::collection($query->paginate()) → dibungkus meta + links
export interface PaginatedResource<T> {
    data: T[];
    meta: {
        current_page: number;
        from: number | null;
        last_page: number;
        per_page: number;
        to: number | null;
        total: number;
        path: string;
        links: PaginationLink[];
    };
    links: {
        first: string | null;
        last: string | null;
        prev: string | null;
        next: string | null;
    };
}
```

`simplePaginate()` dan `cursorPaginate()` tidak punya `total`/`last_page`; buat type terpisah bila dipakai.

## types/global.d.ts dengan InertiaConfig

Isi `sharedPageProps` disalin dari `share()` di `app/Http/Middleware/HandleInertiaRequests.php`. Setiap key yang di-share di sana harus ada di sini, dan sebaliknya.

```ts
import type { AxiosStatic } from 'axios';
import type { User, Flash } from './index';
import '@inertiajs/core';   // wajib: menjadikan file ini module agar declare module meng-augment, bukan mengganti

declare module '@inertiajs/core' {
    export interface InertiaConfig {
        // Tersedia di semua page lewat page.props
        sharedPageProps: {
            auth: { user: User | null };
            appName: string;
            // ...key lain dari HandleInertiaRequests::share()
        };
        // Type page.props.flash dan router.flash()
        flashDataType: Flash;
        // Default Laravel: satu string per field. Pakai string[] bila memakai multiple errors per field.
        errorValueType: string;
    }
}

declare global {
    interface Window {
        axios: AxiosStatic;
    }
}
```

**Ziggy:** tambahkan deklarasi `route` global:

```ts
import type { route as routeFn } from 'ziggy-js';

declare global {
    var route: typeof routeFn;
    interface Window {
        route: typeof routeFn;
    }
}
```

**Wayfinder:** tidak perlu deklarasi global; fungsi route di-import dari `@/actions/...` atau `@/routes/...` dan sudah bertipe. Versi Wayfinder yang lebih baru bisa ikut menghasilkan type shared props, page props, dan model. Bila tersedia di proyek, pakai hasil generate itu daripada menulis manual.

## Mengapa @inertiajs/core

Inertia v2 menyediakan interface `InertiaConfig` di `@inertiajs/core` khusus untuk declaration merging. Semua adapter (`@inertiajs/svelte`, `@inertiajs/react`, `@inertiajs/vue3`) membaca type dari core, sehingga satu augmentasi berlaku di framework apa pun:

- `sharedPageProps` → di-merge ke `page.props` di seluruh aplikasi.
- `flashDataType` → mengetik `page.props.flash` dan `router.flash()`.
- `errorValueType` → mengetik `page.props.errors` dan `form.errors`.

Augment di paket adapter tidak berpengaruh, dan meng-augment `PageProps` langsung bisa bentrok dengan definisi default di core.

## Fallback: Inertia v2 awal tanpa InertiaConfig

Bila `grep -rl 'interface InertiaConfig' node_modules/@inertiajs/core/` kosong, upgrade adapter lebih dulu bila memungkinkan. Bila tidak, pakai pola lama:

```ts
import type { PageProps as InertiaPageProps } from '@inertiajs/core';
import type { User, Flash } from './index';

export interface SharedProps {
    auth: { user: User | null };
    flash: Flash;
}

declare module '@inertiajs/core' {
    interface PageProps extends InertiaPageProps, SharedProps {}
}
```

Dengan pola ini `usePage<SharedProps & { ... }>()` perlu diberi generic eksplisit di lebih banyak tempat.

## Generic Inertia yang berguna

| API | Contoh | Kegunaan |
|---|---|---|
| `usePage<T>()` | `usePage<{ products: Product[] }>()` | Props page spesifik, di-merge dengan shared props |
| `useForm<T>()` | `useForm<{ name: string; tags: string[] }>({...})` | Field, error key, dan nested key bertipe |
| `useRemember<T>()` | `useRemember<{ search: string }>({ search: '' })` | State filter yang bertahan saat back/forward |
| `router.post<T>()` | `router.post<CreateUserData>('/users', data)` | Mengetik data request |
| `router.restore<T>()` | `router.restore<TableState>('table-state')` | State yang disimpan manual |
| `router.flash<T>()` | `router.flash<{ paymentError: string }>({...})` | Flash lokal di luar `flashDataType` |
| `router.push<T>()` / `replace<T>()` | `router.push<UserPageProps>({ component, url, props })` | Kunjungan client-side |

Rujukan resmi: inertiajs.com/docs/v2/advanced/typescript.
