---
name: securing-inertia-apps
description: Mengaudit dan memperbaiki kebocoran data dan struktur halaman pada aplikasi Inertia.js (Laravel + React/Vue/Svelte + Vite). Mencakup props dan shared data yang terlihat di page source (atribut data-page), filter kolom di controller, route list Ziggy vs Wayfinder, history encryption, serta memecah bundle Vite per role agar halaman admin atau internal tidak ikut terkirim ke pengunjung publik. Gunakan saat meninjau keamanan app Inertia, saat page source atau tab Network memperlihatkan field sensitif, saat bundle app.js menyebut path admin, saat memisahkan entrypoint public dan admin, atau saat muncul blank screen atau Error undefined setelah login hanya di production. Cocok untuk permintaan seperti amankan inertia, data-page bocor, props terekspos, sembunyikan halaman admin, pisah bundle admin, history encryption inertia, audit keamanan laravel inertia, inertia data exposure, hide admin routes from bundle, secure inertia app.
license: MIT
metadata:
  author: robithyusuf
  version: "1.0.0"
---

# Mengamankan Aplikasi Inertia.js

Dua prinsip dasar:
1. **Semua yang dikirim Inertia adalah publik** bagi user yang membuka halaman itu. Page object (component, props, shared data) ada di HTML awal, di `history.state`, dan di JSON setiap kunjungan berikutnya. Tidak bisa dimatikan, jadi satu-satunya perbaikan nyata adalah **tidak mengirimkannya**.
2. **Bundle JS adalah publik** bagi siapa pun. Glob wildcard default membuat daftar seluruh halaman, termasuk admin, tertulis di `app-<hash>.js` yang diunduh pengunjung anonim.

Keduanya mengurangi informasi yang bocor; **tidak satu pun menggantikan otorisasi di server**. Setiap route dan action tetap wajib dilindungi middleware/policy.

## Persiapan

- Python 3 (standard library saja) untuk `scripts/audit_page_props.py`; `curl` dan `grep`.
- Akses ke URL staging/production, atau jalankan app lokal dengan build production (`npm run build`).
- Untuk halaman yang butuh login: simpan HTML dari browser, atau export header Cookie ke env var (mis. `INERTIA_AUDIT_COOKIE`). Jangan menulis nilai cookie di file atau chat.

## Alur kerja

Salin checklist ini dan centang selama bekerja:

```
- [ ] 1. Petakan stack dan permukaan
- [ ] 2. Audit data: page object per halaman kunci (guest + tiap role)
- [ ] 3. Audit bundle: apakah bundle publik menyebut halaman internal
- [ ] 4. Perbaiki data (controller -> shared data -> route list -> history)
- [ ] 5. Perbaiki bundle bila diputuskan perlu (split per role, sinkron 3 arah)
- [ ] 6. Verifikasi di build production, termasuk navigasi lintas bundle
```

**1. Petakan.** Kumpulkan sebelum mengubah apa pun:
- Versi `inertiajs/inertia-laravel` dan adapter client (`composer.json`, `package.json`); history encryption butuh v2+.
- Framework (React/Vue/Svelte), lokasi dan casing folder halaman (`resources/js/pages` vs `Pages`).
- Entrypoint di `vite.config.*` (`input`), isi `import.meta.glob` di `app.*` dan `ssr.*`.
- `HandleInertiaRequests`: isi `share()`, ada tidaknya override `rootView()` dan `version()`.
- Routing client: Ziggy (`@routes`, prop `ziggy`) atau Wayfinder.
- Daftar halaman kunci: beranda, list, detail, checkout/profil, dashboard tiap role.

**2. Audit data.** Untuk setiap halaman kunci:

```bash
python3 scripts/audit_page_props.py https://example.com/
python3 scripts/audit_page_props.py https://example.com/dashboard --cookie-env INERTIA_AUDIT_COOKIE
python3 scripts/audit_page_props.py saved-page.html
```

Script mencetak ukuran per prop, objek dengan banyak field (tanda model dikirim utuh), dan nama field mencurigakan (exit 1 bila ada). Lalu cocokkan dengan kode: grep nama prop di komponen halaman untuk tahu field mana yang benar-benar dirender. Field yang tidak dirender adalah kandidat dibuang. Periksa juga kunjungan XHR (DevTools > Network > respons JSON dengan header `X-Inertia`) karena halaman yang dibuka lewat navigasi tidak muncul di page source.

**3. Audit bundle.** Tanpa login, ambil bundle yang dimuat beranda lalu cari path internal:

```bash
curl -s https://example.com/ | grep -oE '/build/assets/[A-Za-z0-9_.-]+\.js' | sort -u
curl -s https://example.com/build/assets/app-<hash>.js | grep -oE '\./[Pp]ages/[^"]+' | sort -u
```

Bila keluar path seperti `./pages/admin/...`, halaman internal ikut terdaftar di bundle publik.

**4. Perbaiki data**, urut dari dampak terbesar. Detail dan contoh kode: [references/data-exposure.md](references/data-exposure.md).
1. **Props di controller**: kirim hanya field yang dirender (`select()`, `only()`, API Resource, atau `map()` ke array eksplisit). Jangan pernah mengirim model utuh.
2. **Shared data** di `share()`: dikirim ke setiap halaman, jadi minimal. User sebagai array field terpilih, bukan `$request->user()`.
3. **Route list**: Wayfinder tidak mengirim route list; bila Ziggy, kecualikan `admin.*` dan route tool internal.
4. **History encryption**: `INERTIA_ENCRYPT_HISTORY=true` di production dan `Inertia::clearHistory()` saat logout.
5. **(Kosmetik)** `delete el.dataset.page` di `setup()`. Hanya menyembunyikan dari Inspect Element; jangan dilaporkan sebagai perbaikan.

**5. Perbaiki bundle** bila keputusan di bawah menyatakan perlu. Detail, kode per framework, dan pemetaan role: [references/hidden-routes.md](references/hidden-routes.md). Intinya: entrypoint terpisah per area (`app.*` publik, `admin.*` terproteksi), Blade layout per entrypoint, `rootView()` memilih layout berdasarkan path URL, dan `version()` menyertakan nama root view supaya perpindahan bundle memicu full reload.

**6. Verifikasi.** Wajib di build production, karena dev server menyajikan semua file dan menyembunyikan error pemetaan bundle.
- Ulangi langkah 2 dan 3: tidak ada field mencurigakan, tidak ada path internal di bundle publik.
- Buka setiap halaman yang `select()`-nya diubah (kolom salah = 500).
- Uji login, register, reset password, logout, dan link lintas area; tidak boleh ada blank screen atau "Error undefined".
- Bila gagal, kembali ke langkah 4 atau 5.

## Keputusan utama

**Perlu memecah bundle?**

| Kondisi | Keputusan |
|---|---|
| Ada area admin/internal dan app dibuka publik | Ya, minimal 2 entrypoint |
| Beberapa role dengan area berbeda (member, admin) | 3+ entrypoint, satu per area |
| Semua user adalah staf terautentikasi (app internal) | Biasanya tidak perlu; fokus ke filter props |
| Halaman admin sedikit dan tidak memuat apa pun yang bermakna | Opsional; catat sebagai risiko rendah |

**Di bundle mana halaman auth?** Di bundle yang sama dengan tujuan redirect setelah login. Bila tidak, redirect pasca-login me-resolve komponen yang tidak ada dan layar menjadi blank di production. Untuk banyak role, default-nya taruh di bundle role terbanyak; detail strategi di referensi.

**Ziggy atau Wayfinder?** Wayfinder bila memungkinkan (tidak ada route list di browser). Bila tetap Ziggy, filter via `config/ziggy.php` (`except`) atau filter per user. Wayfinder saja tidak cukup bila halaman admin masih satu bundle, karena URL admin ikut di chunk halamannya.

**Apa yang dilaporkan?** Pisahkan temuan nyata (field sensitif di props, model utuh, route admin di route list, path admin di bundle publik) dari hardening (history encryption, hapus `data-page`). Beri severity: data sensitif/bisnis milik orang lain = tinggi; field internal milik user sendiri atau struktur admin = rendah-sedang.

## Jebakan umum

- **Foreign key relasi**: `with('variants:name,stock')` menghasilkan `[]`. Sertakan `id` dan foreign key (`product_id`); model induk juga perlu `category_id` di `select()` bila memuat `category`.
- **Accessor di `select()`**: kolom computed (`avg_rating`, `*_url`) bukan kolom DB, jadi SQL error. Cocokkan semua kolom dengan migration, termasuk migration `alter`.
- **`$appends`** ikut terkirim setiap kali model diserialisasi.
- **Dev jalan, build rusak**: hampir selalu mismatch antara `vite.config` input, `rootView()`, dan glob entrypoint. Ketiganya harus sinkron.
- **`$request->is()` vs `routeIs()`**: pakai path URL; nama route dari Breeze/Fortify/Jetstream berbeda-beda.
- **SSR**: `ssr.*` tetap memakai wildcard (berjalan di server), dan folder output SSR tidak boleh disajikan publik.
- **`@viteReactRefresh`** hanya untuk React; hapus di Blade untuk Vue/Svelte.
- **History encryption** butuh secure context (HTTPS atau localhost).

## Rujukan

- [references/data-exposure.md](references/data-exposure.md): baca saat memperbaiki props, shared data, Ziggy/Wayfinder, history encryption, atau perlu contoh kode filter Eloquent dan contoh temuan audit.
- [references/hidden-routes.md](references/hidden-routes.md): baca sebelum memecah bundle, saat menentukan bundle untuk halaman auth, saat menangani navigasi lintas bundle, atau saat mendiagnosis blank screen/"Error undefined" di production.
- `scripts/audit_page_props.py`: **jalankan** (bukan dibaca) untuk mengaudit page object dari URL, file HTML, atau stdin.
