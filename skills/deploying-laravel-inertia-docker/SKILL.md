---
name: deploying-laravel-inertia-docker
description: Menyiapkan Docker untuk aplikasi Laravel + Inertia.js (Svelte, React, atau Vue) dengan SSR, dari environment development dengan hot-reload Vite sampai image production multi-stage berisi Nginx, PHP-FPM, Supervisor, queue worker, scheduler, dan server Inertia SSR di belakang Traefik/Dokploy, lengkap dengan template Dockerfile, docker-compose, nginx, supervisor, dan entrypoint siap salin. Gunakan saat pengguna ingin men-dockerize proyek Laravel Inertia, menyiapkan Docker dev, deploy ke VPS/Dokploy/Coolify, menjalankan SSR di container, atau memperbaiki 502, SSR crash loop, HMR tidak jalan, MySQL SSL error, dan permission storage di container. Cocok untuk permintaan seperti dockerize laravel, deploy laravel inertia, setup docker dev laravel, SSR inertia docker, deploy ke dokploy, laravel docker production, inertia ssr not working, vite hmr docker.
license: MIT
metadata:
  author: robithyusuf
  version: "1.0.0"
---

# Deploy Laravel + Inertia (SSR) dengan Docker

Hasil akhirnya: satu set file Docker yang membuat proyek Laravel + Inertia bisa jalan di tiga mode
(dev hot-reload, uji lokal ala production, production di VPS) dengan SSR aktif di production.
Template siap salin ada di `assets/`; skill ini menjelaskan cara memasang, menyesuaikan, dan memverifikasinya.

## Persiapan

- Docker + Docker Compose v2 di mesin pengguna; Dokploy (atau platform sejenis) di VPS untuk production.
- Proyek: Laravel 11+, Inertia.js v2, Vite 5+, frontend Svelte 5 / React 18+ / Vue 3, MySQL 8.
  Route health `/up` aktif (default `withRouting(health: '/up')`).
- Tidak ada kredensial di file mana pun. Nilai rahasia (`APP_KEY`, `DB_PASSWORD`, `DB_ROOT_PASSWORD`,
  API key) hanya ada di `.env` lokal (tidak di-commit) atau panel environment platform.

## Pilih mode

| Kebutuhan | File compose | Dockerfile | SSR | Baca |
|---|---|---|---|---|
| Ngoding harian, HMR, edit langsung terlihat | `docker-compose.dev.yml` | `Dockerfile.dev` | tidak | [references/dev-environment.md](references/dev-environment.md) |
| Uji image production di laptop sebelum push | `docker-compose.local.yml` | `Dockerfile` | ya | [references/production-build.md](references/production-build.md) |
| Production di VPS (Dokploy + Traefik, HTTPS) | `docker-compose.yml` | `Dockerfile` | ya | [references/production-build.md](references/production-build.md), [references/dokploy-https.md](references/dokploy-https.md) |

Bila pengguna tidak menyebut mode: pasang ketiganya (file-nya saling melengkapi), lalu mulai dari dev.

## Alur kerja

Salin checklist ini dan centang selama bekerja:

```
- [ ] 1. Periksa proyek: framework frontend, TS/JS, isi script build, config/inertia.php
- [ ] 2. Salin template dari assets/ dan sesuaikan placeholder
- [ ] 3. Siapkan frontend untuk SSR (noExternal, entry ssr, build --ssr)
- [ ] 4. Siapkan Laravel untuk proxy (trustProxies, forceScheme https)
- [ ] 5. Jalankan dev, verifikasi
- [ ] 6. Jalankan local (production-like), verifikasi SSR
- [ ] 7. Deploy production, verifikasi HTTPS + SSR + /up
```

**1. Periksa proyek.** Baca `package.json` (adapter `@inertiajs/svelte|react|vue3`, script `build`),
`vite.config.*`, keberadaan `resources/js/ssr.*`, `svelte.config.js`, `tsconfig.json`,
`config/inertia.php`, dan `bootstrap/app.php`. Hasilnya menentukan baris `COPY` di Dockerfile dan apa yang perlu ditambahkan.

**2. Salin template.** Dari root proyek (ganti `<skill-dir>` dengan path skill ini):

```bash
cp -r <skill-dir>/assets/docker <skill-dir>/assets/Dockerfile <skill-dir>/assets/Dockerfile.dev \
      <skill-dir>/assets/docker-compose.yml <skill-dir>/assets/docker-compose.dev.yml \
      <skill-dir>/assets/docker-compose.local.yml <skill-dir>/assets/.dockerignore .
chmod +x docker/entrypoint.sh docker/entrypoint-dev.sh
```

Jangan menimpa file yang sudah ada tanpa membandingkan dulu. `assets/.env.example` **digabung** ke
`.env.example` proyek (tambahkan key yang belum ada), bukan disalin menimpa.

Sesuaikan:

| Item | Default template | Ganti dengan |
|---|---|---|
| `APP_SLUG` | `app` | nama unik proyek; jadi nama container `<slug>` dan `<slug>-db` serta nama router Traefik |
| `APP_DOMAIN` | `app.example.com` | domain production |
| `DB_DATABASE` / `DB_USERNAME` | `app` | nama DB & user (user bukan `root`) |
| `COPY vite.config.ts svelte.config.js tsconfig.json` di `Dockerfile` | Svelte + TS | React/Vue: hapus `svelte.config.js`; JS: `vite.config.js`, tanpa `tsconfig.json` |
| Port dev `8080`, `5173`, `3307` | | ubah bila bentrok di host |
| `date.timezone` di `docker/php.ini` | `UTC` | zona waktu aplikasi |
| `numprocs` queue di `docker/supervisord.conf` | 2 | sesuai beban |

API key pihak ketiga: tambahkan ke `environment:` di compose sebagai `${NAMA_KEY}` dan ke `.env.example` tanpa nilai.

**3. Frontend untuk SSR.** Wajib: `ssr: { noExternal: true }` di `vite.config.*` (tanpanya SSR crash loop
di image production), file `resources/js/ssr.ts|tsx` ada, dan `npm run build` menghasilkan
`bootstrap/ssr/ssr.js` (script `vite build && vite build --ssr`). Plugin Vite yang memanggil PHP
(mis. Wayfinder) di-skip saat `DOCKER=true`. Contoh per framework: [references/ssr-frontend.md](references/ssr-frontend.md).

**4. Laravel di belakang proxy.** TLS berhenti di Traefik, jadi tambahkan `trustProxies(at: '*')` di
`bootstrap/app.php` dan `URL::forceScheme('https')` saat production di `AppServiceProvider`.
Pastikan `config/inertia.php` membaca `INERTIA_SSR_ENABLED` dan `INERTIA_SSR_URL`.
Kode lengkap: [references/dokploy-https.md](references/dokploy-https.md).

**5. Dev.** `.env` lokal harus berisi `DB_PASSWORD` dan `DB_ROOT_PASSWORD` (compose sengaja gagal bila kosong).

```bash
docker compose -f docker-compose.dev.yml up --build -d
docker logs -f app          # start pertama ~1-2 menit: install deps, migrate, seed
```

**6. Local production-like.** `.env` juga butuh `APP_KEY`.

```bash
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.local.yml up --build -d
```

**7. Production.** Ikuti langkah di [references/dokploy-https.md](references/dokploy-https.md): isi env di panel,
`RUN_SEEDERS=true` hanya untuk deploy pertama lalu kembalikan ke `false`, ganti password akun default seeder.

## Verifikasi

Jangan menyatakan selesai sebelum cek yang relevan lolos:

```bash
# Dev
curl -sI http://localhost:8080 | head -1                    # 200
curl -s http://localhost:5173 >/dev/null && echo vite-ok
docker exec app supervisorctl status                        # semua RUNNING

# Local / production
docker exec app supervisorctl status                        # inertia-ssr RUNNING
docker exec app php artisan inertia:check-ssr
curl -s http://localhost:8080 | grep -o '<meta property="og:title"[^>]*>'   # local: meta dari SSR
curl -sI https://app.example.com/up | head -1               # production: 200
curl -sI http://app.example.com | grep -i location          # redirect ke https
curl -s https://app.example.com | grep -o '<meta property="og:title"[^>]*>'
```

Bila meta/konten tidak ada di HTML mentah, SSR mati dan Inertia diam-diam fallback ke client render.

## Jebakan umum

- **Tanpa `ssr.noExternal: true`** → `inertia-ssr` crash loop karena image tidak punya `node_modules`.
- **`node` hilang dari stage runtime** → SSR tidak bisa start. `nodejs` sengaja dipasang di stage `base`.
- **Container di dua network tanpa `traefik.docker.network`** → 502 acak.
- **`artisan` lewat `docker exec` sebagai root** membuat log milik root → 500. Pakai `docker exec -u www-data`.
- **Mengganti `DB_PASSWORD` setelah volume DB terbentuk** tidak mengubah password MySQL.
- **`config:cache` saat build** membekukan env kosong; cache dibuat di entrypoint saat runtime.
- **Seeder tidak idempotent** gagal saat restart dengan `RUN_SEEDERS=true`.
- **`.env` masuk build context** → rahasia ter-bake ke image. `.dockerignore` template sudah mengecualikannya.

## Indeks troubleshooting

Detail perintah dan solusi ada di [references/troubleshooting.md](references/troubleshooting.md):

| Gejala | Bagian |
|---|---|
| 502 Bad Gateway | 502 Bad Gateway |
| Container terus restart | Container restart loop |
| `SQLSTATE` / tidak bisa konek DB | Database connection failed |
| `self-signed certificate in certificate chain` | MySQL SSL error |
| `Permission denied` di `storage/` | Storage permission error |
| SSR mati, meta tag hilang, hydration mismatch | SSR crash loop |
| Perubahan frontend tidak muncul di dev | Vite HMR tidak jalan |
| Perubahan PHP/env tidak terbaca di production | Perubahan tidak muncul (cache) |
| HTTPS tidak aktif | Sertifikat SSL tidak terbit |
| Backup/restore DB, lihat log | Maintenance |

## Referensi cepat

| Item | Nilai |
|---|---|
| Container | `<APP_SLUG>` (app), `<APP_SLUG>-db` (MySQL 8.0) |
| Image | PHP 8.2-fpm Alpine + Node 20, ~200-250 MB |
| Port internal | Nginx 80, PHP-FPM 9000, SSR 13714 |
| Port dev (host) | app 8080, Vite 5173, MySQL 3307 |
| Health check | `/up` |
| Log | `storage/logs/laravel.log`, `/var/log/supervisor/{queue,scheduler,ssr,vite}.log` |

## Rujukan

- [references/dev-environment.md](references/dev-environment.md): baca saat menyiapkan/men-debug mode dev (mount, anonymous volume, urutan entrypoint dev, kapan rebuild).
- [references/production-build.md](references/production-build.md): baca saat mengubah Dockerfile, compose production/local, Nginx/PHP/OPcache, Supervisor, atau env vars.
- [references/ssr-frontend.md](references/ssr-frontend.md): baca saat menyiapkan SSR per framework, `vite.config`, entry SSR, `config/inertia.php`, SEO meta.
- [references/dokploy-https.md](references/dokploy-https.md): baca saat deploy ke Dokploy/VPS, DNS, label Traefik, trusted proxies, seeder production.
- [references/troubleshooting.md](references/troubleshooting.md): baca saat ada error atau untuk backup, restore, dan log.
- `assets/`: template file (`Dockerfile`, `Dockerfile.dev`, tiga `docker-compose*.yml`, `.dockerignore`, `.env.example`, `docker/*`).
