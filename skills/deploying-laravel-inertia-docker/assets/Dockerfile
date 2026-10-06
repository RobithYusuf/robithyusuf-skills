# Production image: Laravel + Inertia SSR (multi-stage).
# Hasil: Nginx + PHP-FPM + queue worker + scheduler + SSR server dalam satu container (Supervisor).

# ---------- Stage 1: build frontend (client assets + SSR bundle) ----------
FROM node:20-alpine AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm ci --prefer-offline --no-audit
# Svelte butuh svelte.config.js. React/Vue: hapus svelte.config.js dari baris ini.
COPY vite.config.ts svelte.config.js tsconfig.json ./
COPY resources ./resources
COPY public ./public
RUN mkdir -p bootstrap/ssr
# Dipakai vite.config.ts untuk melewati plugin yang butuh PHP (mis. Wayfinder) di stage Node-only.
ENV DOCKER=true
# Menghasilkan public/build/ (client) dan bootstrap/ssr/ssr.js (SSR)
RUN npm run build

# ---------- Stage 2: PHP base ----------
FROM php:8.2-fpm-alpine AS base
# nodejs tetap dibutuhkan di runtime: inertia:start-ssr menjalankan bootstrap/ssr/ssr.js dengan node.
RUN apk add --no-cache \
    nginx supervisor curl zip unzip git \
    icu-dev libzip-dev libpng-dev libjpeg-turbo-dev \
    freetype-dev oniguruma-dev sqlite-dev \
    mysql-client shadow nodejs npm
RUN docker-php-ext-configure gd --with-freetype --with-jpeg \
 && docker-php-ext-install pdo pdo_mysql pdo_sqlite \
    mbstring zip bcmath opcache intl gd pcntl exif
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer
WORKDIR /var/www/html

# ---------- Stage 3: production ----------
FROM base AS production
# Layer composer di-cache selama composer.json/lock tidak berubah
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-scripts --no-autoloader --prefer-dist --no-interaction
COPY --chown=www-data:www-data . .
RUN composer dump-autoload --optimize --no-dev

COPY --from=frontend --chown=www-data:www-data /app/public/build ./public/build
COPY --from=frontend --chown=www-data:www-data /app/bootstrap/ssr ./bootstrap/ssr

COPY docker/nginx.conf /etc/nginx/http.d/default.conf
COPY docker/php.ini /usr/local/etc/php/conf.d/zz-app.ini
COPY docker/opcache.ini /usr/local/etc/php/conf.d/zz-opcache.ini
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh

# storage-init: salinan awal storage/ untuk mengisi named volume yang masih kosong saat start pertama
RUN cp -r storage /var/www/storage-init \
 && mkdir -p /var/log/supervisor \
 && chmod +x /usr/local/bin/entrypoint.sh \
 && chown -R www-data:www-data storage bootstrap/cache

EXPOSE 80
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
