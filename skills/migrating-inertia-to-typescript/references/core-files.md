# Fase 3: Migrasi File JS Inti

## Daftar isi

- Peta file
- Entry app per framework
- Entry SSR
- bootstrap.ts
- Utils dan formatter
- Config statis
- Store dengan guard SSR

## Peta file

Rename `.js` → `.ts` (React: `.jsx` → `.tsx`) satu per satu, lalu tambahkan type. Kategori yang umum ditemukan:

| File | Perubahan kunci |
|---|---|
| `app.js` | Typed `import.meta.glob`, typed resolver, hapus akses `window.*` yang tidak bertipe |
| `ssr.js` | Sama dengan `app`, ditambah resolver server |
| `bootstrap.js` | `window.axios` lewat deklarasi `Window` di `global.d.ts` |
| `Utils/*.js` | Type parameter dan return di setiap fungsi export |
| `Config/*.js` (menu, link) | Interface item + `satisfies` |
| `Stores/*.js` | Interface state, store generic, guard SSR |
| Svelte action (`use:portal`) | `ActionReturn`/`Action` dari `svelte/action` |

Setelah semua file inti selesai, jalankan type checker dan build sebelum menyentuh komponen.

## Entry app per framework

Type resolver dengan `ResolvedComponent` (Svelte/React) atau `DefineComponent` (Vue) agar hasil `import.meta.glob` tidak `unknown`.

**Svelte (`app.ts`):**

```ts
import './bootstrap';
import { createInertiaApp, type ResolvedComponent } from '@inertiajs/svelte';
import { hydrate, mount } from 'svelte';

createInertiaApp({
    resolve: (name: string) => {
        const pages = import.meta.glob<ResolvedComponent>('./Pages/**/*.svelte', { eager: true });
        const page = pages[`./Pages/${name}.svelte`];
        if (!page) throw new Error(`Page not found: ${name}`);
        return page;
    },
    setup({ el, App, props }) {
        if (!el) return;
        if (el.dataset.serverRendered === 'true') {
            hydrate(App, { target: el, props });
        } else {
            mount(App, { target: el, props });
        }
    },
    progress: { color: '#4b5563' },
});
```

Bila aplikasi lama punya fallback ke halaman error (mis. `pages['./Pages/Error.svelte']`) atau sengaja mengosongkan `el` lalu `mount` sebagai workaround hydration mismatch, pertahankan perilaku itu; migrasi TS tidak boleh mengubah perilaku runtime.

**React (`app.tsx`):**

```tsx
import './bootstrap';
import { createInertiaApp, type ResolvedComponent } from '@inertiajs/react';
import { createRoot, hydrateRoot } from 'react-dom/client';

createInertiaApp({
    resolve: (name) => {
        const pages = import.meta.glob<ResolvedComponent>('./Pages/**/*.tsx', { eager: true });
        return pages[`./Pages/${name}.tsx`];
    },
    setup({ el, App, props }) {
        if (el.hasChildNodes()) {
            hydrateRoot(el, <App {...props} />);
        } else {
            createRoot(el).render(<App {...props} />);
        }
    },
});
```

**Vue (`app.ts`):**

```ts
import './bootstrap';
import { createApp, h, type DefineComponent } from 'vue';
import { createInertiaApp } from '@inertiajs/vue3';

createInertiaApp({
    resolve: (name) => {
        const pages = import.meta.glob<DefineComponent>('./Pages/**/*.vue', { eager: true });
        return pages[`./Pages/${name}.vue`];
    },
    setup({ el, App, props, plugin }) {
        createApp({ render: () => h(App, props) }).use(plugin).mount(el);
    },
});
```

Untuk `import.meta.glob` non-eager (lazy), generic-nya sama: `import.meta.glob<ResolvedComponent>(...)` menghasilkan `Record<string, () => Promise<ResolvedComponent>>`. Helper `resolvePageComponent` dari `laravel-vite-plugin/inertia-helpers` juga menerima generic.

## Entry SSR

Pola resolver sama dengan entry client. Perbedaannya hanya pada `createServer` dan fungsi render dari adapter. Jangan import modul yang menyentuh `window`/`document` di level atas, karena `ssr.ts` dieksekusi di Node.

## bootstrap.ts

```ts
import axios from 'axios';

window.axios = axios;
window.axios.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
```

`window.axios` hanya valid bila `Window` sudah di-augment di `types/global.d.ts`. Untuk kode baru, lebih baik import `axios` langsung daripada lewat `window`.

## Utils dan formatter

Terima input longgar (`number | string | null | undefined`) karena data dari Laravel sering string (cast decimal) atau null, tetapi kembalikan tipe yang pasti.

```ts
type NumberLike = number | string | null | undefined;

function toNumber(value: NumberLike): number | null {
    if (value === null || value === undefined || value === '') return null;
    const num = typeof value === 'string' ? parseFloat(value) : value;
    return Number.isNaN(num) ? null : num;
}

export function formatNumber(value: NumberLike, locale = 'id-ID', options: Intl.NumberFormatOptions = {}): string {
    const num = toNumber(value);
    return num === null ? '0' : num.toLocaleString(locale, options);
}

export function formatCurrency(value: NumberLike, currency = 'IDR', locale = 'id-ID'): string {
    const num = toNumber(value) ?? 0;
    return new Intl.NumberFormat(locale, { style: 'currency', currency, maximumFractionDigits: 0 }).format(num);
}

export function formatDate(
    date: string | Date | null | undefined,
    options: Intl.DateTimeFormatOptions = {},
    locale = 'id-ID',
): string {
    if (!date) return '-';
    return new Date(date).toLocaleDateString(locale, { day: 'numeric', month: 'short', year: 'numeric', ...options });
}
```

Pertahankan nama dan perilaku fungsi lama, termasuk nilai fallback (`'-'`, `'0'`), supaya pemanggil tidak berubah perilaku.

**Svelte action:**

```ts
import type { ActionReturn } from 'svelte/action';

export function portal(node: HTMLElement, target: HTMLElement = document.body): ActionReturn {
    target.appendChild(node);
    return {
        destroy() {
            node.parentNode?.removeChild(node);
        },
    };
}
```

## Config statis

```ts
export interface MenuItem {
    name: string;
    href: string;
    icon?: string;
    children?: MenuItem[];
    roles?: string[];
}

export const publicMenus = [
    { name: 'Beranda', href: '/', icon: 'home' },
    { name: 'Produk', href: '/products', icon: 'box' },
    { name: 'Kontak', href: '/contact', icon: 'mail' },
] satisfies MenuItem[];
```

`satisfies` memvalidasi bentuk tanpa melebarkan tipe literal; pakai anotasi biasa (`: MenuItem[]`) bila array akan dimodifikasi.

## Store dengan guard SSR

Kode di level modul ikut jalan di Node saat SSR. Guard setiap akses `window`, `document`, dan `localStorage`.

```ts
import { writable } from 'svelte/store';

export interface Theme {
    name: string;
    value: string;
    colors: Record<'primary500' | 'primary600' | 'primary700', string>;
}

export const presetThemes: Record<string, Theme> = {
    default: { name: 'Default', value: 'default', colors: { primary500: '#6b7280', primary600: '#4b5563', primary700: '#374151' } },
};

const isBrowser = typeof window !== 'undefined';

function loadTheme(): string {
    if (!isBrowser) return 'default';
    const saved = localStorage.getItem('appTheme');
    return saved && presetThemes[saved] ? saved : 'default';
}

export const currentTheme = writable<string>(loadTheme());

currentTheme.subscribe((theme) => {
    if (!isBrowser) return;
    localStorage.setItem('appTheme', theme);
    const root = document.documentElement;
    if (theme === 'default') root.removeAttribute('data-theme');
    else root.setAttribute('data-theme', theme);
});
```

Untuk store custom (bukan `writable`), tulis interface publiknya dulu, lalu implementasi mengikuti:

```ts
export type AlertType = 'success' | 'error' | 'warning' | 'info';
export type AlertPosition = 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right';

export interface Alert {
    id: number;
    message: string;
    type: AlertType;
    timestamp: number;
}

export interface AlertStore {
    readonly alerts: Alert[];
    readonly position: AlertPosition;
    add(message: string, type?: AlertType, duration?: number): number;
    remove(id: number): void;
    clear(): void;
    setPosition(position: AlertPosition): void;
    success(message: string, duration?: number): number;
    error(message: string, duration?: number): number;
    warning(message: string, duration?: number): number;
    info(message: string, duration?: number): number;
}

const savedPosition = typeof localStorage !== 'undefined' ? localStorage.getItem('alertPosition') : null;
const initialPosition = (savedPosition ?? 'top-center') as AlertPosition;
```

Nilai dari `localStorage` selalu `string | null`; validasi atau cast secara sadar seperti di atas. React dan Vue memakai pola yang sama (context/hook atau composable), guard SSR tetap wajib.
