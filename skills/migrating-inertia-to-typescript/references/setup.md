# Fase 1: Setup Infrastruktur TypeScript

## Daftar isi

- Dependensi per framework
- tsconfig.json
- svelte.config.js (khusus Svelte)
- vite.config.ts
- Entry Blade
- Script package.json
- pnpm dan Docker

## Dependensi per framework

```bash
# Svelte 5
npm install -D typescript @tsconfig/svelte svelte-check

# React
npm install -D typescript @types/react @types/react-dom

# Vue 3
npm install -D typescript vue-tsc
```

Tambahkan `@types/node` bila `vite.config.ts` memakai `path`/`node:url`.

## tsconfig.json

Basis untuk Svelte. Opsi yang sengaja dipilih:
- `strict: true`: jangan menumpuk technical debt.
- `moduleResolution: "bundler"`: sesuai cara Vite me-resolve import.
- `verbatimModuleSyntax: false`: `import type` dianjurkan tapi tidak wajib, supaya migrasi tidak macet karena gaya import.
- `paths` `@/*` harus sama dengan `resolve.alias` di Vite.
- `include` wajib memuat `**/*.d.ts`, kalau tidak augmentasi Inertia tidak terbaca.

```json
{
    "extends": "@tsconfig/svelte/tsconfig.json",
    "compilerOptions": {
        "target": "ESNext",
        "module": "ESNext",
        "moduleResolution": "bundler",
        "strict": true,
        "noEmit": true,
        "isolatedModules": true,
        "esModuleInterop": true,
        "skipLibCheck": true,
        "forceConsistentCasingInFileNames": true,
        "resolveJsonModule": true,
        "allowImportingTsExtensions": true,
        "verbatimModuleSyntax": false,
        "baseUrl": ".",
        "paths": {
            "@/*": ["resources/js/*"]
        },
        "types": ["vite/client"]
    },
    "include": [
        "resources/js/**/*.ts",
        "resources/js/**/*.svelte",
        "resources/js/**/*.d.ts",
        "vite.config.ts"
    ],
    "exclude": ["node_modules", "public", "vendor"]
}
```

**React:** hapus `extends`, tambahkan `"jsx": "react-jsx"` dan `"lib": ["DOM", "DOM.Iterable", "ESNext"]`, ganti pola include `*.svelte` menjadi `resources/js/**/*.tsx`.

**Vue:** hapus `extends`, tambahkan `"jsx": "preserve"` dan `"lib": ["DOM", "DOM.Iterable", "ESNext"]`, ganti pola include `*.svelte` menjadi `resources/js/**/*.vue`. `vue-tsc` sudah memahami file `.vue`; shim berikut hanya perlu bila ada tool lain (mis. `tsc` biasa) yang ikut membaca import `.vue`:

```ts
// resources/js/types/vue-shim.d.ts
declare module '*.vue' {
    import type { DefineComponent } from 'vue';
    const component: DefineComponent<object, object, unknown>;
    export default component;
}
```

**Migrasi bertahap:** bila file `.js` lama masih harus di-import selama transisi, tambahkan sementara `"allowJs": true` dan `"checkJs": false`. Hapus di fase 7.

## svelte.config.js (khusus Svelte)

```js
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

export default {
    preprocess: vitePreprocess(),
};
```

Tanpa `vitePreprocess()`, compiler Svelte tidak bisa memproses blok `<script lang="ts">` dan build gagal di komponen pertama yang dimigrasi.

## vite.config.ts

Rename `vite.config.js` → `vite.config.ts` dan ubah entry ke `.ts`. Contoh Svelte dengan SSR:

```ts
import { defineConfig } from 'vite';
import laravel from 'laravel-vite-plugin';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
    plugins: [
        laravel({
            input: ['resources/css/app.css', 'resources/js/app.ts'],
            ssr: 'resources/js/ssr.ts',
            refresh: true,
        }),
        svelte(),
    ],
    resolve: {
        alias: {
            '@': '/resources/js',
        },
    },
    ssr: {
        noExternal: true,
    },
});
```

Pertahankan plugin lain yang sudah ada (Tailwind, Wayfinder, dll.). Perbedaan per framework:

| Framework | Plugin | Entry |
|---|---|---|
| Svelte | `svelte()` dari `@sveltejs/vite-plugin-svelte` | `app.ts`, `ssr.ts` |
| React | `react()` dari `@vitejs/plugin-react` | `app.tsx`, `ssr.tsx` |
| Vue | `vue({ template: { transformAssetUrls: { base: null, includeAbsolute: false } } })` dari `@vitejs/plugin-vue` | `app.ts`, `ssr.ts` |

## Entry Blade

Ubah entry di layout Blade root (biasanya `resources/views/app.blade.php`):

```diff
- @vite(['resources/css/app.css', 'resources/js/app.js'])
+ @vite(['resources/css/app.css', 'resources/js/app.ts'])
```

React memakai `app.tsx` dan butuh `@viteReactRefresh` sebelum `@vite(...)`. Bila Blade juga me-preload file page (`resources/js/Pages/{$page['component']}.jsx`), ubah ekstensinya juga.

## Script package.json

```json
{
    "scripts": {
        "dev": "vite",
        "build": "vite build && vite build --ssr",
        "check": "svelte-check --tsconfig ./tsconfig.json",
        "check:watch": "svelte-check --tsconfig ./tsconfig.json --watch"
    }
}
```

Ganti `check` dengan `tsc --noEmit` (React) atau `vue-tsc --noEmit` (Vue). Hapus `&& vite build --ssr` bila proyek tidak memakai SSR. Pertimbangkan menjalankan `npm run check` di CI agar regresi type tertangkap sebelum merge.

## pnpm dan Docker

- **pnpm:** `@inertiajs/core` tidak di-hoist, sehingga `declare module '@inertiajs/core'` tidak ter-resolve. Tambahkan ke `.npmrc` lalu `pnpm install`:
  ```
  public-hoist-pattern[]=@inertiajs/core
  ```
  atau `pnpm add @inertiajs/core`.
- **Docker/CI:** pastikan `tsconfig.json`, `svelte.config.js`, dan `vite.config.ts` ikut di-`COPY` ke stage build Node, dan entrypoint SSR menunjuk file hasil build yang baru (`bootstrap/ssr/ssr.js` tetap `.js` karena itu output build).
