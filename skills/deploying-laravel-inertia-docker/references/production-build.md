# Production Image & Runtime

File terkait: `Dockerfile`, `docker-compose.yml`, `docker-compose.local.yml`, `docker/nginx.conf`,
`docker/php.ini`, `docker/opcache.ini`, `docker/supervisord.conf`, `docker/entrypoint.sh`.

## Daftar isi

- Arsitektur container
- Multi-stage build
- Adaptasi per framework & Wayfinder
- Perbandingan tiga file compose
- Nginx, PHP, OPcache
- Supervisor production
- Urutan entrypoint production
- Environment variables

## Arsitektur container

```
Internet ──► Traefik (80/443, Let's Encrypt)  ── network: dokploy-network
                │ (routing lewat label)
                ▼
  container app (Supervisor)
   ├─ Nginx :80 ──► PHP-FPM :9000 ──► Laravel ──► Inertia SSR :13714 (Node)
   ├─ Queue worker x2
   └─ Scheduler (loop schedule:run)
                │  network: app-network
                ▼
  container db (MySQL 8.0)

Volumes: db-data, app-storage (storage/), app-logs (/var/log/supervisor)
```

Satu container menjalankan semua proses PHP lewat Supervisor: sederhana untuk VPS tunggal.
Bila perlu scale horizontal, pecah queue/scheduler ke service terpisah dengan image yang sama.

## Multi-stage build

```
Stage 1 frontend (node:20-alpine)   npm ci → npm run build
                                    output: public/build/, bootstrap/ssr/ssr.js
Stage 2 base (php:8.2-fpm-alpine)   nginx, supervisor, ekstensi PHP, nodejs, composer
Stage 3 production (FROM base)      composer install --no-dev → COPY source
                                    → COPY hasil build stage 1 → config docker/ → entrypoint
```

- `composer.json`/`composer.lock` di-COPY dulu sebelum source supaya layer dependency ter-cache.
- `composer install --no-scripts --no-autoloader`, lalu `dump-autoload --optimize` setelah source ada.
- **nodejs wajib ada di stage runtime**: `inertia:start-ssr` menjalankan `bootstrap/ssr/ssr.js` dengan node.
- `storage/` disalin ke `/var/www/storage-init` agar entrypoint bisa mengisi named volume yang masih kosong.
- Ekstensi PHP: `pdo pdo_mysql pdo_sqlite mbstring zip bcmath opcache intl gd(freetype,jpeg) pcntl exif`.
- Estimasi ukuran image: ~200-250 MB (Alpine).

## Adaptasi per framework & Wayfinder

Yang berubah di stage 1 hanya file config yang di-COPY:

```dockerfile
# Svelte
COPY vite.config.ts svelte.config.js tsconfig.json ./
# React / Vue
COPY vite.config.ts tsconfig.json ./
```

Proyek JavaScript (tanpa TS): ganti `vite.config.ts` → `vite.config.js` dan hapus `tsconfig.json`.

**Wayfinder** (atau plugin Vite lain yang memanggil `php artisan`) gagal di stage Node-only.
Solusi: skip plugin saat build Docker dan commit file hasil generate.

```dockerfile
ENV DOCKER=true
RUN npm run build
```

```typescript
// vite.config.ts
const isCI = process.env.CI === 'true' || process.env.DOCKER === 'true';
plugins: [
    ...(!isCI ? [wayfinder()] : []),
]
```

## Perbandingan tiga file compose

| | `docker-compose.yml` | `docker-compose.dev.yml` | `docker-compose.local.yml` |
|---|---|---|---|
| Tujuan | Production (Dokploy) | Dev hot-reload | Uji lokal ala production |
| Dockerfile | `Dockerfile` | `Dockerfile.dev` | `Dockerfile` |
| Port app | internal (Traefik) | 8080:80 | 8080:80 |
| Port Vite | - | 5173:5173 | - |
| Port MySQL | internal | 3307:3306 | 3307:3306 |
| Volume | named | mount source | named |
| Label Traefik | ya | tidak | tidak |
| Network | app-network + dokploy-network | default | default |
| APP_ENV / DEBUG | production / false | local / true | local / true |
| Cache Laravel | penuh | dimatikan | penuh |
| SSR | ya | tidak | ya |
| Queue worker | 2 | 1 | 2 |

`docker-compose.local.yml` dipakai untuk menangkap masalah build/SSR/cache sebelum push ke server.

## Nginx, PHP, OPcache

`docker/nginx.conf`: security headers (`X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`,
`Referrer-Policy`), `client_max_body_size 100M`, `fastcgi_read_timeout 300`, buffer FastCGI besar
(header Inertia bisa besar), tolak dotfile kecuali `.well-known`, cache aset 1 tahun `immutable`
(aman karena nama file Vite ber-hash), gzip level 6.

`docker/php.ini`:

| Setting | Nilai | Alasan |
|---|---|---|
| `memory_limit` | 256M | import/export data besar |
| `upload_max_filesize` / `post_max_size` | 100M | sama dengan `client_max_body_size` Nginx |
| `max_execution_time` | 300 | proses panjang |
| `date.timezone` | sesuaikan | samakan dengan `APP_TIMEZONE` |
| `display_errors` / `expose_php` | Off | keamanan |

`docker/opcache.ini` (production saja): `memory_consumption=256`, `max_accelerated_files=20000`,
`validate_timestamps=0`, `jit=1255`, `jit_buffer_size=128M`. Dengan `validate_timestamps=0`
perubahan PHP baru terbaca setelah restart container; aman karena image immutable.

## Supervisor production

| Program | Command | Instance | User |
|---|---|---|---|
| `php-fpm` | `php-fpm -F` | 1 | root |
| `nginx` | `nginx -g "daemon off;"` | 1 | root |
| `laravel-queue` | `artisan queue:work --tries=3` | 2 | www-data |
| `laravel-scheduler` | loop `schedule:run` tiap 60 detik | 1 | www-data |
| `inertia-ssr` | `artisan inertia:start-ssr` | 1 | www-data |

Scale queue: ubah `numprocs` di `[program:laravel-queue]` lalu redeploy.
Log: `/var/log/supervisor/{queue,scheduler,ssr}.log`; php-fpm & nginx ke stdout (`docker logs`).

## Urutan entrypoint production

1. Isi volume `storage/` dari `storage-init` bila kosong; buat subdirektori yang hilang.
2. Permission `www-data:www-data`, `775` untuk `storage` dan `bootstrap/cache`.
3. Tunggu DB: `artisan tinker --execute="DB::connection()->getPdo();"`, maks 30 x 3 detik, lalu exit 1.
4. `migrate --force`.
5. `db:seed --force` bila `RUN_SEEDERS=true`.
6. `config:cache`, `route:cache`, `view:cache`, `event:cache`.
7. `storage:link`.
8. `chown` ulang (artisan jalan sebagai root bisa membuat log milik root → 500), lalu `exec supervisord`.

Cache dibuat di entrypoint, bukan saat build, karena `config:cache` membekukan env yang baru
tersedia saat runtime.

## Environment variables

Template lengkap: `assets/.env.example`. Wajib di production: `APP_KEY`, `APP_DOMAIN`,
`DB_PASSWORD`, `DB_ROOT_PASSWORD` (compose gagal start bila kosong, disengaja).

| Variable | Default | Catatan |
|---|---|---|
| `APP_SLUG` | `app` | nama container & router Traefik; unik per host |
| `APP_DOMAIN` | - | `APP_URL` dibentuk jadi `https://$APP_DOMAIN` |
| `APP_ENV` / `APP_DEBUG` | production / false | |
| `DB_HOST` | `db` | nama service compose |
| `DB_DATABASE` / `DB_USERNAME` | `app` | `DB_USERNAME` tidak boleh `root` (image MySQL menolak) |
| `MYSQL_ATTR_SSL_VERIFY` | true | `false` hanya untuk Docker dev/local |
| `SESSION_DRIVER` / `QUEUE_CONNECTION` / `CACHE_STORE` | database | tanpa Redis |
| `FILESYSTEM_DISK` | local | |
| `RUN_SEEDERS` | false | `true` hanya deploy pertama |
| `INERTIA_SSR_ENABLED` | true | |
| `INERTIA_SSR_URL` | `http://127.0.0.1:13714` | SSR jalan di container yang sama |

API key pihak ketiga (payment gateway, ongkir, dll.) ditambahkan sebagai env var di panel deploy
dan di `environment:` compose; jangan pernah di-hardcode di file compose atau di-bake ke image.

Generate `APP_KEY`: `php artisan key:generate --show` (lokal) atau `docker exec app php artisan key:generate --show`.
