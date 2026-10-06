# Troubleshooting & Maintenance

Ganti `app` / `app-db` dengan `$APP_SLUG` / `$APP_SLUG-db` bila berbeda.

## Daftar isi

- 502 Bad Gateway
- Container restart loop
- Database connection failed
- MySQL SSL error (Docker dev)
- Storage permission error
- SSR crash loop / tidak jalan / hydration mismatch
- Vite HMR tidak jalan (dev)
- Perubahan tidak muncul (cache)
- Sertifikat SSL tidak terbit
- Git mendeteksi perubahan permission
- Maintenance: backup, restore, log, reset

## 502 Bad Gateway

```bash
docker ps -a | grep app
docker logs app --tail 100
docker network inspect dokploy-network   # container app harus ada di sini
```

Penyebab umum: container belum lolos entrypoint (masih menunggu DB/migrate), label
`traefik.docker.network` tidak ada sehingga Traefik memakai network yang salah, atau
`loadbalancer.server.port` bukan 80.

## Container restart loop

```bash
docker inspect app --format='{{.State.ExitCode}}'
docker logs app 2>&1 | head -50
```

Cari baris `[entrypoint]` terakhir. Sering: env wajib kosong, DB tidak terjangkau 30 x 3 detik,
`migrate` gagal, atau `config:cache` error karena closure di file config.

## Database connection failed

```bash
docker logs app-db
docker exec -it app php artisan tinker --execute="DB::connection()->getPdo();"
```

Periksa `DB_HOST=db` (nama service, bukan `127.0.0.1`), kecocokan `DB_PASSWORD` antara app dan db.
Image MySQL hanya membuat user/database saat volume **pertama kali** dibuat: mengganti
`DB_PASSWORD` setelahnya tidak mengubah password di DB. Ubah lewat `ALTER USER`, atau di dev
hapus volume (`down -v`).

## MySQL SSL error (Docker dev)

Gejala: `self-signed certificate in certificate chain`.

1. Set `MYSQL_ATTR_SSL_VERIFY=false` (sudah ada di compose dev/local).
2. Pastikan `config/database.php` membaca variabel itu:

```php
'options' => extension_loaded('pdo_mysql') ? array_filter([
    PDO::MYSQL_ATTR_SSL_CA => env('MYSQL_ATTR_SSL_CA'),
]) + (env('MYSQL_ATTR_SSL_VERIFY', true) ? [] : [
    PDO::MYSQL_ATTR_SSL_VERIFY_SERVER_CERT => false,
]) : [],
```

## Storage permission error

```bash
docker exec -it app sh -c "chown -R www-data:www-data storage bootstrap/cache && chmod -R 775 storage bootstrap/cache"
```

Biasanya karena `artisan` dijalankan sebagai root (lewat `docker exec`) dan membuat file log/cache
milik root. Jalankan perintah yang menulis file sebagai www-data: `docker exec -u www-data app php artisan ...`.

## SSR crash loop / tidak jalan / hydration mismatch

| Gejala | Penyebab | Solusi |
|---|---|---|
| `inertia-ssr` restart terus | dependency tidak ter-bundle | `ssr: { noExternal: true }` di `vite.config.ts`, rebuild |
| SSR tidak jalan | error Node di bundle | `tail -f /var/log/supervisor/ssr.log`, `node bootstrap/ssr/ssr.js` |
| `bootstrap/ssr/ssr.js` tidak ada | build SSR tidak dijalankan | script build harus menyertakan `vite build --ssr`; cek COPY dari stage frontend |
| Hydration mismatch | render server ≠ client | jaga kode browser-only (`window`, `localStorage`) dengan `onMount`/`useEffect`/cek `typeof window` |
| Meta tag tidak ada di `curl` | SSR mati, Inertia fallback ke CSR | `php artisan inertia:check-ssr`, cek `INERTIA_SSR_ENABLED` |

## Vite HMR tidak jalan (dev)

```bash
docker exec app supervisorctl status vite-dev
docker exec app supervisorctl restart vite-dev
docker exec app tail -50 /var/log/supervisor/vite.log
curl http://localhost:5173
```

- Pastikan port `5173:5173` dipetakan dan Vite jalan dengan `--host 0.0.0.0`.
- Bila browser mencoba memuat aset dari `http://0.0.0.0:5173`, set
  `server: { hmr: { host: 'localhost' } }` di `vite.config.ts` (isi `public/hot` mengikuti nilai ini).
- Perubahan file tidak terdeteksi pada bind mount (Docker Desktop/WSL): tambahkan
  `server: { watch: { usePolling: true } }`.
- Bila `public/hot` tertinggal dari sesi lama, hapus file itu; di production file ini tidak boleh ada.

## Perubahan tidak muncul (cache)

```bash
docker exec app php artisan optimize:clear
docker exec app php artisan config:cache
docker exec app php artisan route:cache
docker exec app php artisan view:cache
```

Di production, perubahan kode PHP baru terbaca setelah redeploy/restart (OPcache `validate_timestamps=0`).
Perubahan env juga butuh restart karena config di-cache saat start.

## Sertifikat SSL tidak terbit

1. DNS sudah propagate: `dig +short app.example.com` mengembalikan IP VPS.
2. Tunggu 1-2 menit untuk provisioning Let's Encrypt.
3. Periksa log Traefik di panel Dokploy (rate limit, challenge gagal, port 80 tertutup).

## Git mendeteksi perubahan permission

`chmod` di dalam container dev mengubah mode file di mount source:

```bash
git config core.fileMode false
```

## Maintenance: backup, restore, log, reset

Password diambil dari env container, jadi tidak perlu diketik di command line:

```bash
# Backup database
docker exec app-db sh -c 'mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' \
  > backup-$(date +%Y%m%d-%H%M%S).sql

# Restore
docker exec -i app-db sh -c 'mysql -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < backup.sql

# Backup file upload
docker cp app:/var/www/html/storage/app ./storage-backup
```

```bash
docker exec -it app tail -f storage/logs/laravel.log          # aplikasi
docker logs -f app                                            # nginx + php-fpm (stdout)
docker exec -it app tail -f /var/log/supervisor/queue.log     # queue worker
docker exec -it app tail -f /var/log/supervisor/ssr.log       # SSR server
docker exec -it app sh                                        # shell
```

Reset database (menghapus semua data, minta konfirmasi pengguna dulu):

```bash
docker exec app php artisan migrate:fresh --seed --force
```
