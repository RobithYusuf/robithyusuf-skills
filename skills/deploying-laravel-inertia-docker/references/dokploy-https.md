# Deploy ke Dokploy, Reverse Proxy & HTTPS

## Daftar isi

- Prasyarat
- Langkah deploy
- DNS
- Label Traefik
- Trusted proxies & force HTTPS
- Seeder di production
- Platform lain

## Prasyarat

1. VPS dengan Dokploy terpasang (Traefik + network `dokploy-network` sudah dibuat Dokploy).
2. DNS domain mengarah ke IP VPS.
3. Repository Git yang bisa diakses Dokploy.
4. `docker compose -f docker-compose.local.yml up --build` sudah lolos di lokal.

## Langkah deploy

1. Push kode ke branch deploy.
2. Dokploy: **Create Project → Compose**, hubungkan repository, pilih branch, compose path `docker-compose.yml`.
3. **Environment**: isi minimal `APP_SLUG`, `APP_DOMAIN`, `APP_KEY`, `DB_PASSWORD`, `DB_ROOT_PASSWORD`,
   plus API key pihak ketiga. Untuk deploy pertama set `RUN_SEEDERS=true`.
4. **Deploy**. Build pertama ~5-10 menit.
5. Setelah sukses: set `RUN_SEEDERS=false` (atau hapus), ganti password akun default dari seeder.
6. Verifikasi: `https://<domain>` dan `https://<domain>/up` mengembalikan 200.
7. Update berikutnya: **Redeploy**, atau aktifkan Auto Deploy agar deploy otomatis saat push.

## DNS

```
Type: A
Name: <subdomain>     (mis. app → app.example.com)
Value: <IP VPS>
TTL: 3600
```

Cek propagasi dengan `dig +short app.example.com` sebelum menunggu sertifikat.

## Label Traefik

Sudah ada di `assets/docker-compose.yml`. Intinya:

| Label | Fungsi |
|---|---|
| `traefik.enable=true` | container diekspos ke Traefik |
| `traefik.docker.network=dokploy-network` | container punya 2 network; tanpa ini Traefik bisa memilih `app-network` dan menghasilkan 502 |
| router `<slug>-http` (entrypoint `web`) + middleware `redirectscheme` | HTTP → HTTPS |
| router `<slug>` (entrypoint `websecure`, `tls.certresolver=letsencrypt`) | HTTPS dengan sertifikat otomatis |
| `loadbalancer.server.port=80` | Traefik meneruskan ke Nginx di container |

Nama router/service/middleware memakai `${APP_SLUG}`. Bila dua stack memakai nama yang sama di satu
host, routing saling bertabrakan, jadi `APP_SLUG` harus unik.

Nama entrypoint (`web`, `websecure`) dan certresolver (`letsencrypt`) mengikuti default Dokploy;
sesuaikan bila Traefik di host dikonfigurasi berbeda.

## Trusted proxies & force HTTPS

TLS berhenti di Traefik, jadi request yang masuk ke container adalah HTTP. Tanpa dua pengaturan
ini Laravel membuat URL `http://` (aset mixed content, redirect login salah, signed URL invalid).

```php
// bootstrap/app.php
->withMiddleware(function (Middleware $middleware) {
    $middleware->trustProxies(at: '*');
})
```

```php
// app/Providers/AppServiceProvider.php
use Illuminate\Support\Facades\URL;

public function boot(): void
{
    if ($this->app->environment('production')) {
        URL::forceScheme('https');
    }
}
```

`trustProxies(at: '*')` aman karena container hanya bisa dijangkau lewat Traefik (tidak ada port publik).

## Seeder di production

- Otomatis: `RUN_SEEDERS=true` → `db:seed --force` saat container start. Default `false`.
- Manual:

```bash
docker exec app php artisan db:seed --force
docker exec app php artisan db:seed --class=NamaSeeder --force
```

Seeder **harus idempotent** karena bisa jalan lebih dari sekali (restart dengan `RUN_SEEDERS=true`):
pakai `firstOrCreate` untuk data referensi/akun dan `updateOrCreate` untuk data yang boleh diperbarui.
Jangan bergantung pada Faker di seeder production (Faker biasanya `require-dev`, tidak ada di image).
Akun default dari seeder harus segera diganti passwordnya setelah deploy pertama.

## Platform lain

- **Coolify / CapRover**: compose yang sama bisa dipakai; hapus label Traefik + `dokploy-network`
  dan atur domain lewat panel platform.
- **Docker Compose manual + Nginx Proxy Manager / Caddy**: pakai pola `docker-compose.local.yml`,
  ekspos port app hanya ke `127.0.0.1`, lalu proxy dari reverse proxy ke port itu.
