#!/bin/sh
# Development entrypoint: install deps bila kosong -> tunggu DB -> migrate/seed -> CLEAR cache -> supervisor
set -e
cd /var/www/html

# 1. Direktori storage
mkdir -p storage/framework/cache/data storage/framework/sessions storage/framework/views \
         storage/logs storage/app/public bootstrap/cache

# 2. Permission
chown -R www-data:www-data storage bootstrap/cache
chmod -R 775 storage bootstrap/cache

# 3. npm deps (anonymous volume node_modules kosong pada start pertama)
if [ ! -f node_modules/.package-lock.json ]; then
    echo "[entrypoint-dev] npm install"
    npm install
fi

# 4. composer deps (anonymous volume vendor kosong pada start pertama)
if [ ! -f vendor/autoload.php ]; then
    echo "[entrypoint-dev] composer install"
    composer install --no-interaction --prefer-dist
fi

# 5. Cache Vite harus bisa ditulis
mkdir -p node_modules/.vite
chmod -R 775 node_modules/.vite

# APP_KEY kosong di .env lokal -> generate sekali
if [ -f .env ] && ! grep -q '^APP_KEY=..*' .env; then
    php artisan key:generate --force
fi

# 6. Tunggu database dengan PDO mentah (SSL verify dimatikan: sertifikat MySQL di container self-signed)
attempt=0
until php -r '
    $opts = [PDO::MYSQL_ATTR_SSL_VERIFY_SERVER_CERT => false];
    new PDO("mysql:host=" . getenv("DB_HOST") . ";port=" . (getenv("DB_PORT") ?: "3306"),
            getenv("DB_USERNAME"), getenv("DB_PASSWORD"), $opts);
' >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 30 ]; then
        echo "[entrypoint-dev] Database tidak bisa dihubungi setelah 30 percobaan" >&2
        exit 1
    fi
    echo "[entrypoint-dev] Menunggu database ($attempt/30)..."
    sleep 3
done

# 7. Migrasi + seeder (seeder jalan tiap start bila RUN_SEEDERS=true, jadi harus idempotent)
php artisan migrate --force
if [ "${RUN_SEEDERS:-false}" = "true" ]; then
    php artisan db:seed --force
fi

# 8. Dev: HAPUS cache (bukan membuat cache) supaya perubahan langsung terlihat
php artisan optimize:clear

# 9. Symlink public/storage
php artisan storage:link >/dev/null 2>&1 || true

chown -R www-data:www-data storage bootstrap/cache

# 10. Jalankan semua proses (termasuk Vite dev server)
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
