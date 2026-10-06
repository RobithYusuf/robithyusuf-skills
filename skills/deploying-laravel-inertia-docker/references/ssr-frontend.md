# Inertia SSR & Konfigurasi Frontend

## Daftar isi

- Perbedaan per framework
- vite.config.ts
- svelte.config.js & tsconfig.json
- Entry SSR per framework
- Konfigurasi Laravel (config/inertia.php)
- Alur request SSR
- Perintah SSR
- SEO & meta tags
- Verifikasi

## Perbedaan per framework

| Aspek | Svelte | React | Vue |
|---|---|---|---|
| Vite plugin | `@sveltejs/vite-plugin-svelte` | `@vitejs/plugin-react` | `@vitejs/plugin-vue` |
| Client entry | `resources/js/app.ts` | `resources/js/app.tsx` | `resources/js/app.ts` |
| SSR entry | `resources/js/ssr.ts` | `resources/js/ssr.tsx` | `resources/js/ssr.ts` |
| Inertia adapter | `@inertiajs/svelte` | `@inertiajs/react` | `@inertiajs/vue3` |
| SSR render | `createServer` dari `@inertiajs/svelte/server` | `createServer` + `ReactDOMServer.renderToString` | `createSSRApp` + `renderToString` |
| Config tambahan | `svelte.config.js` | - | - |

**`ssr: { noExternal: true }` wajib di semua framework.** Tanpanya dependency tidak ter-bundle ke
`bootstrap/ssr/ssr.js`, dan SSR server crash loop di image production karena tidak ada `node_modules`.

## vite.config.ts

```typescript
import { defineConfig } from 'vite';
import laravel from 'laravel-vite-plugin';
import tailwindcss from '@tailwindcss/vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';   // React: import react from '@vitejs/plugin-react'
                                                         // Vue:   import vue from '@vitejs/plugin-vue'
export default defineConfig({
    plugins: [
        laravel({
            input: ['resources/css/app.css', 'resources/js/app.ts'],   // React: app.tsx
            ssr: 'resources/js/ssr.ts',                                // React: ssr.tsx
            refresh: true,
        }),
        tailwindcss(),
        svelte(),                                                      // React: react() | Vue: vue()
    ],
    resolve: { alias: { '@': '/resources/js' } },
    ssr: { noExternal: true },   // bundle SEMUA deps ke ssr.js
});
```

`npm run build` harus menghasilkan `public/build/` (client + manifest) **dan** `bootstrap/ssr/ssr.js`.
Bila script `build` hanya `vite build`, ubah menjadi `vite build && vite build --ssr`.

Blade entry (`resources/views/app.blade.php`) harus merujuk entry yang sama:
`@vite(['resources/css/app.css', 'resources/js/app.ts'])` serta `@inertiaHead` di `<head>`.

## svelte.config.js & tsconfig.json

```javascript
// svelte.config.js — agar <script lang="ts"> di .svelte diproses
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
export default { preprocess: vitePreprocess() };
```

```json
{
    "extends": "@tsconfig/svelte/tsconfig.json",
    "compilerOptions": {
        "target": "ESNext",
        "module": "ESNext",
        "moduleResolution": "bundler",
        "strict": true,
        "noEmit": true,
        "baseUrl": ".",
        "paths": { "@/*": ["resources/js/*"] },
        "types": ["vite/client"]
    },
    "include": ["resources/js/**/*.ts", "resources/js/**/*.svelte", "resources/js/types/**/*.d.ts", "vite.config.ts"]
}
```

React/Vue: hapus `extends` Svelte, tambahkan `"jsx": "react-jsx"` (React) atau include `**/*.vue` (Vue).
Type check: `npm run check` (Svelte: `svelte-check`; React/Vue: `tsc --noEmit` / `vue-tsc --noEmit`).

## Entry SSR per framework

**Svelte** (`resources/js/ssr.ts`):

```typescript
import { createInertiaApp } from '@inertiajs/svelte';
import createServer from '@inertiajs/svelte/server';

createServer((page) =>
    createInertiaApp({
        page,
        resolve: (name) => {
            const pages = import.meta.glob('./Pages/**/*.svelte', { eager: true });
            return pages[`./Pages/${name}.svelte`];
        },
    })
);
```

**React** (`resources/js/ssr.tsx`):

```tsx
import { createInertiaApp } from '@inertiajs/react';
import createServer from '@inertiajs/react/server';
import ReactDOMServer from 'react-dom/server';

createServer((page) =>
    createInertiaApp({
        page,
        render: ReactDOMServer.renderToString,
        resolve: (name) => {
            const pages = import.meta.glob('./Pages/**/*.tsx', { eager: true });
            return pages[`./Pages/${name}.tsx`];
        },
        setup: ({ App, props }) => <App {...props} />,
    })
);
```

**Vue** (`resources/js/ssr.ts`):

```typescript
import { createInertiaApp } from '@inertiajs/vue3';
import createServer from '@inertiajs/vue3/server';
import { renderToString } from '@vue/server-renderer';
import { createSSRApp, h } from 'vue';

createServer((page) =>
    createInertiaApp({
        page,
        render: renderToString,
        resolve: (name) => {
            const pages = import.meta.glob('./Pages/**/*.vue', { eager: true });
            return pages[`./Pages/${name}.vue`];
        },
        setup({ App, props, plugin }) {
            return createSSRApp({ render: () => h(App, props) }).use(plugin);
        },
    })
);
```

## Konfigurasi Laravel (config/inertia.php)

Publish bila belum ada: `php artisan vendor:publish --provider="Inertia\ServiceProvider"`.

```php
'ssr' => [
    'enabled' => (bool) env('INERTIA_SSR_ENABLED', true),
    'url' => env('INERTIA_SSR_URL', 'http://127.0.0.1:13714'),
    'bundle' => base_path('bootstrap/ssr/ssr.js'),
],
```

Matikan SSR tanpa rebuild: set `INERTIA_SSR_ENABLED=false` lalu restart container
(config di-cache saat start, jadi perlu restart).

## Alur request SSR

```
Browser → Nginx :80 → PHP-FPM :9000 → Laravel
  → (Inertia) POST page props ke SSR server Node :13714
  → SSR render komponen jadi HTML + head tags
  → HTML lengkap ke browser → hydration di client
```

Bila SSR server mati, Inertia diam-diam fallback ke client-side rendering: halaman tetap jalan,
tetapi meta tags tidak ada di HTML. Karena itu verifikasi SSR harus memeriksa HTML mentah.

## Perintah SSR

```bash
docker exec app php artisan inertia:check-ssr          # status
docker exec app php artisan inertia:stop-ssr           # stop; Supervisor menyalakan ulang otomatis
docker exec app tail -f /var/log/supervisor/ssr.log    # log
docker exec app node bootstrap/ssr/ssr.js              # jalankan bundle langsung untuk melihat error
docker exec app supervisorctl status inertia-ssr
```

## SEO & meta tags

Taruh meta di layout publik supaya ikut di-render SSR. Contoh Svelte 5:

```svelte
<script lang="ts">
    let { title = '', description = '', image = '/images/og-default.jpg', url = '', children } = $props();
    const siteName = import.meta.env.VITE_APP_NAME;
    const fullTitle = title ? `${title} - ${siteName}` : siteName;
</script>

<svelte:head>
    <title>{fullTitle}</title>
    <meta name="description" content={description} />
    <meta property="og:type" content="website" />
    <meta property="og:title" content={fullTitle} />
    <meta property="og:description" content={description} />
    <meta property="og:image" content={image} />
    <meta property="og:url" content={url} />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="robots" content="index, follow" />
    <link rel="canonical" href={url} />
</svelte:head>

{@render children()}
```

React/Vue: pakai komponen `<Head>` dari adapter Inertia masing-masing.
Kode yang memakai `window`/`document`/`localStorage` harus dijaga (`onMount`, `useEffect`,
`typeof window !== 'undefined'`) agar tidak crash di SSR atau menyebabkan hydration mismatch.

## Verifikasi

```bash
# Meta harus sudah ada di HTML response (bukan diisi JavaScript)
curl -s https://app.example.com | grep -o '<meta property="og:title"[^>]*>'
# Bundle SSR ada di image
docker exec app ls -la bootstrap/ssr/ssr.js
```
