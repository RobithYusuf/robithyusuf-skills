# Wayfinder di Docker, CI, dan Deploy

## Daftar isi

- Masalah
- Pilih strategi
- Strategi A: commit file ter-generate, skip plugin
- Strategi B: generate di stage PHP
- Strategi C: build frontend di lingkungan yang punya PHP
- Route cache saat deploy
- CI: cegah file ter-generate basi

## Masalah

Vite plugin menjalankan `php artisan wayfinder:generate` saat `npm run build`. Pada Docker multi-stage, stage frontend biasanya hanya berisi Node, sehingga build gagal dengan error kira-kira:

```
ERROR: process "/bin/sh -c npm run build" did not complete successfully: exit code: 1
    at runCommand (file:///.../vite-plugin-wayfinder/dist/index.mjs:...)
```

Hal yang sama terjadi di job CI yang hanya memasang Node.

## Pilih strategi

| Strategi | Kapan dipakai | Biaya |
|---|---|---|
| A. Commit file ter-generate, skip plugin | Default untuk Dockerfile Node-only yang sudah ada | Developer wajib regenerate + commit saat route berubah |
| B. Generate di stage PHP | Tidak mau ada file ter-generate di repo | Satu stage tambahan, build lebih lambat |
| C. Build frontend di image yang punya PHP | Image app sudah berisi PHP + Node | Image build lebih besar |

Tanyakan pengguna bila tidak jelas. Jangan campur A dan B: bila B dipakai, file ter-generate tetap di-gitignore.

## Strategi A: commit file ter-generate, skip plugin

**1. Skip plugin secara kondisional** di `vite.config.ts`:

```typescript
import { wayfinder } from '@laravel/vite-plugin-wayfinder';

const skipWayfinder = process.env.DOCKER === 'true';

export default defineConfig({
    plugins: [
        laravel({ /* ... */ }),
        ...(skipWayfinder ? [] : [wayfinder()]),
        svelte(), // react() / vue()
    ],
});
```

Hindari memakai `process.env.CI === 'true'` sebagai satu-satunya pemicu. Banyak penyedia CI menyetel `CI=true` otomatis, sehingga job CI yang punya PHP diam-diam memakai file commit yang mungkin basi. Pakai variabel khusus (`DOCKER`, atau nama lain yang jelas seperti `SKIP_WAYFINDER`) yang hanya diset di lingkungan tanpa PHP.

**2. Set variabel di stage frontend:**

```dockerfile
FROM node:20-alpine AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm ci --prefer-offline --no-audit
COPY vite.config.ts tsconfig.json ./
# tambahkan config framework bila ada: svelte.config.js, dll.
COPY resources ./resources
COPY public ./public
RUN mkdir -p bootstrap/ssr

# File Wayfinder sudah ada di resources/js (di-commit), jadi plugin dilewati
ENV DOCKER=true
RUN npm run build
```

Pastikan `.dockerignore` tidak mengecualikan `resources/js/actions`, `resources/js/routes`, atau `resources/js/wayfinder`.

**3. Jangan gitignore file ter-generate:**

```gitignore
# Wayfinder: di-commit karena build Docker tidak punya PHP
# /resources/js/actions/
# /resources/js/routes/
# /resources/js/wayfinder/
```

**4. Regenerate dan commit setiap kali route/controller berubah:**

```bash
php artisan wayfinder:generate
git add resources/js/actions/ resources/js/routes/ resources/js/wayfinder/
git commit -m "chore: regenerate wayfinder definitions"
```

Saat `vite dev` berjalan lokal, plugin sudah me-regenerate otomatis. Tinggal pastikan perubahannya ikut di-commit. Opsi `formVariants` di plugin harus sama dengan flag `--with-form` saat generate manual, supaya isi file tidak berganti-ganti di setiap commit.

Alur ringkas:

```
Lokal:      vite dev → plugin aktif → auto-generate saat route berubah → commit hasilnya
Produksi:   docker build → DOCKER=true → plugin di-skip → pakai file dari repo → npm run build sukses
```

## Strategi B: generate di stage PHP

```dockerfile
# Stage 1: generate Wayfinder (PHP + Composer)
FROM php:8.3-cli-alpine AS wayfinder
WORKDIR /app
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-scripts --no-interaction --prefer-dist
COPY . .
RUN php artisan wayfinder:generate

# Stage 2: build frontend (Node saja)
FROM node:20-alpine AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm ci --prefer-offline --no-audit
COPY vite.config.ts tsconfig.json ./
COPY resources ./resources
COPY --from=wayfinder /app/resources/js/actions ./resources/js/actions
COPY --from=wayfinder /app/resources/js/routes ./resources/js/routes
COPY --from=wayfinder /app/resources/js/wayfinder ./resources/js/wayfinder
COPY public ./public
RUN mkdir -p bootstrap/ssr
ENV DOCKER=true
RUN npm run build
```

Catatan untuk stage PHP:
- `artisan` harus bisa boot tanpa database/Redis. Bila service provider menyentuh DB saat boot, sediakan `.env` minimal untuk build (mis. `cp .env.example .env && php artisan key:generate`) atau perbaiki provider-nya. Jangan menyalin `.env` berisi kredensial asli ke image build.
- Ekstensi PHP yang dibutuhkan `composer install` harus terpasang di image tersebut. Bila gagal, tambahkan `--ignore-platform-reqs` hanya untuk stage ini.
- Bila `wayfinder` hanya ada di `require-dev`, jangan pakai `--no-dev` di stage ini.

## Strategi C: build frontend di lingkungan yang punya PHP

Bila image atau runner sudah berisi PHP dan Node, cukup pastikan `composer install` jalan sebelum `npm run build`. Plugin tidak perlu di-skip dan file ter-generate boleh di-gitignore.

## Route cache saat deploy

Wayfinder membaca route dari router yang terdaftar. Bila deploy sebelumnya menjalankan `php artisan optimize` atau `route:cache`, generate berikutnya membaca cache lama dan route baru hilang dari hasil generate. Gejalanya Vite gagal dengan `Could not load resources/js/routes/<name>`. Urutan yang aman di skrip deploy:

```bash
php artisan route:clear
npm run build                 # plugin menjalankan wayfinder:generate di sini
php artisan optimize          # cache ulang setelah build
```

## CI: cegah file ter-generate basi

Untuk strategi A, tambahkan job CI (yang punya PHP) yang gagal bila file commit tidak sama dengan hasil generate:

```bash
composer install --no-interaction --prefer-dist
php artisan route:clear
php artisan wayfinder:generate
test -z "$(git status --porcelain -- resources/js/actions resources/js/routes resources/js/wayfinder)" \
  || { echo "File Wayfinder basi: jalankan php artisan wayfinder:generate lalu commit"; exit 1; }
```

`git status --porcelain` dipakai (bukan `git diff`) supaya file baru yang belum di-commit juga terdeteksi.

Untuk strategi B/C, cukup pastikan job CI menjalankan type-check dan `npm run build` setelah generate.
