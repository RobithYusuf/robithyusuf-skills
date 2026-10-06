#!/bin/sh
# Production entrypoint: siapkan storage -> tunggu DB -> migrate -> (seed) -> cache -> supervisor
set -e
cd /var/www/html

# 1. Named volume storage masih kosong saat start pertama: isi dari salinan di image
if [ ! -d storage/framework ]; then
    echo "[entrypoint] Inisialisasi storage dari storage-init"
    cp -r /var/www/storage-init/. storage/
fi
mkdir -p storage/framework/cache/data storage/framework/sessions storage/framework/views \
         storage/logs storage/app/public bootstrap/cache

# 2. Permission
chown -R www-data:www-data storage bootstrap/cache
chmod -R 775 storage bootstrap/cache

# 3. Tunggu database (maks 30 percobaan x 3 detik)
if [ "${DB_CONNECTION:-mysql}" != "sqlite" ]; then
    attempt=0
    until php artisan tinker --execute="DB::connection()->getPdo();" >/dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ "$attempt" -ge 30 ]; then
            echo "[entrypoint] Database tidak bisa dihubungi setelah 30 percobaan" >&2
            exit 1
        fi
        echo "[entrypoint] Menunggu database ($attempt/30)..."
        sleep 3
    done
fi

# 4. Migrasi
php artisan migrate --force

# 5. Seeder hanya bila diminta (deploy pertama). Seeder harus idempotent.
if [ "${RUN_SEEDERS:-false}" = "true" ]; then
    php artisan db:seed --force
fi

# 6. Cache untuk performa
php artisan config:cache
php artisan route:cache
php artisan view:cache
php artisan event:cache

# 7. Symlink public/storage
php artisan storage:link >/dev/null 2>&1 || true

# Perintah di atas jalan sebagai root dan bisa membuat file log/cache milik root.
# Kembalikan ke www-data agar PHP-FPM & queue tidak gagal menulis (500 / permission denied).
chown -R www-data:www-data storage bootstrap/cache

# 8. Jalankan semua proses
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
