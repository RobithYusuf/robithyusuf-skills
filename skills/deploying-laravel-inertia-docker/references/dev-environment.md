# Development Environment (hot-reload)

File terkait: `Dockerfile.dev`, `docker-compose.dev.yml`, `docker/nginx-dev.conf`,
`docker/supervisord-dev.conf`, `docker/entrypoint-dev.sh` (semua ada di `assets/`).

## Daftar isi

- Cara kerja
- Topologi & port
- Alur hot-reload dan kapan perlu rebuild
- Urutan entrypoint dev
- Proses Supervisor dev
- Beda dengan production
- Perintah harian

## Cara kerja

1. **Source di-mount** (`.:/var/www/html`): perubahan file di host langsung terlihat di container.
2. **Anonymous volume** untuk `vendor/` dan `node_modules/`: dependency di-install di dalam container
   (binary native sesuai Alpine/musl, tidak tertimpa folder host dari macOS/Windows).
3. **Vite dev server** di port 5173 dengan HMR; tidak ada `npm run build`.
4. **Tanpa cache Laravel**: config/route/view/event cache dihapus setiap start.
5. **Auto-install deps**: entrypoint memasang dependency bila `vendor/` atau `node_modules/` kosong.
6. **SSR dimatikan** (`INERTIA_SSR_ENABLED=false`): Vite dev server yang melayani aset.

## Topologi & port

```
Browser ──► localhost:8080 ──► container app (Supervisor)
            localhost:5173       ├─ Nginx :80 ──► PHP-FPM :9000
                                 ├─ Vite HMR :5173
                                 ├─ Queue worker x1
                                 └─ Scheduler
            localhost:3307 ──► container db (MySQL 8.0, :3306)
```

| Host | Container | Service |
|---|---|---|
| 8080 | 80 | Nginx → PHP-FPM (app) |
| 5173 | 5173 | Vite dev server (HMR) |
| 3307 | 3306 | MySQL (akses dari DB client di host) |

Port host 3307 dipilih agar tidak bentrok dengan MySQL lokal di 3306.

## Alur hot-reload dan kapan perlu rebuild

```
Edit .svelte/.tsx/.vue/.ts/.css di host
  → (volume mount) file berubah di container
  → Vite mendeteksi perubahan
  → browser update via WebSocket :5173
```

| Perubahan | Perlu rebuild? |
|---|---|
| `.svelte`/`.tsx`/`.vue`, `.ts`, `.css` | Tidak (HMR) |
| File PHP (controller, model), Blade | Tidak (tanpa OPcache & cache) |
| `composer.json` | Ya, atau `docker exec app composer install` |
| `package.json` | Ya, atau `docker exec app npm install` lalu `supervisorctl restart vite-dev` |
| File di `docker/`, `Dockerfile.dev` | Ya: `docker compose -f docker-compose.dev.yml up --build -d` |

Catatan: karena `vendor/` dan `node_modules/` adalah anonymous volume, `up --build` saja tidak
mengosongkannya. Untuk dependency yang benar-benar baru dari nol, pakai `down -v` (ikut menghapus DB dev).

## Urutan entrypoint dev

1. Buat direktori `storage/` dan `bootstrap/cache`.
2. Set permission `www-data`, `775`.
3. `npm install` bila `node_modules/.package-lock.json` tidak ada.
4. `composer install` bila `vendor/autoload.php` tidak ada.
5. Pastikan `node_modules/.vite` bisa ditulis.
6. Tunggu DB dengan **PDO mentah** dan `MYSQL_ATTR_SSL_VERIFY_SERVER_CERT=false`
   (sertifikat MySQL di container self-signed; cek lewat artisan bisa gagal karena itu).
7. `migrate --force`, lalu `db:seed --force` bila `RUN_SEEDERS=true`. Seeder jalan **setiap start**,
   jadi wajib idempotent.
8. `php artisan optimize:clear` (menghapus cache, bukan membuatnya).
9. `storage:link`.
10. `exec supervisord`.

Start pertama butuh ~1-2 menit (install deps + migrate + seed). Pantau dengan `docker logs -f app`.

## Proses Supervisor dev

| Program | Command | Instance | User |
|---|---|---|---|
| `php-fpm` | `php-fpm -F` | 1 | root |
| `nginx` | `nginx -g "daemon off;"` | 1 | root |
| `vite-dev` | `npm run dev -- --host 0.0.0.0` | 1 | **root** |
| `laravel-queue` | `artisan queue:work --tries=3` | 1 | www-data |
| `laravel-scheduler` | loop `schedule:run` tiap 60 detik | 1 | www-data |

`vite-dev` jalan sebagai root karena `www-data` tidak punya izin menulis cache `node_modules/.vite`.
`--host 0.0.0.0` wajib agar port 5173 bisa diakses dari luar container.

## Beda dengan production

| Aspek | Dev | Production |
|---|---|---|
| Image | `Dockerfile.dev` single-stage, tanpa build aset | `Dockerfile` multi-stage |
| Dependency | di-install entrypoint (volume mount) | di-install saat build |
| Cache Laravel | dihapus | dibuat (config/route/view/event) |
| OPcache config | tidak dimuat | `opcache.ini` (JIT, tanpa revalidasi) |
| Aset | Vite dev server :5173 | `public/build` statis |
| SSR | mati | `inertia:start-ssr` :13714 |
| Cek DB | PDO mentah, SSL verify off | `artisan tinker` |
| Nginx | minimal | gzip, cache aset 1 tahun, buffer FastCGI |

## Perintah harian

```bash
docker compose -f docker-compose.dev.yml up --build -d   # start
docker logs -f app                                       # pantau start pertama
docker exec -it app sh                                   # shell
docker exec app php artisan migrate                      # artisan apa pun
docker compose -f docker-compose.dev.yml down            # stop
docker compose -f docker-compose.dev.yml down -v         # stop + hapus DB & anonymous volume
```

Reset total: `down -v` lalu `up --build -d`.
