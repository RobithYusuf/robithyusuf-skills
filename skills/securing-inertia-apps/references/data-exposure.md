# Data Exposure di Inertia.js

Detail teknis untuk mencegah props, shared data, dan route list terekspos ke browser. Berlaku untuk Laravel + Inertia v2+ dengan Svelte, React, atau Vue (dengan atau tanpa SSR).

## Daftar isi

- Masalah: page object di HTML
- Prinsip dari maintainer Inertia
- 1. Filter props di controller
- 2. Filter shared data
- 3. Route list: Ziggy vs Wayfinder
- 4. History encryption
- 5. Hapus `data-page` setelah hydration (kosmetik)
- 6. Audit manual dan contoh temuan
- Checklist
- Sumber

## Masalah: page object di HTML

Pada kunjungan pertama, Inertia menaruh seluruh page object di HTML, biasanya sebagai atribut `data-page` pada root element:

```html
<div id="app" data-page="{&quot;component&quot;:&quot;Home&quot;,&quot;props&quot;:{&quot;auth&quot;:{...}},&quot;url&quot;:&quot;/&quot;,&quot;version&quot;:&quot;...&quot;}">
```

Data itu terlihat lewat:
- **View Page Source / curl**: response HTML mentah.
- **Inspect Element**: atribut di DOM.
- **Browser history**: page object disimpan di `window.history.state`.
- **Kunjungan Inertia berikutnya (XHR)**: props datang sebagai JSON di tab Network.

Page object **tidak bisa dihilangkan** karena dibutuhkan untuk hydration awal dan merupakan bagian dari [protokol Inertia](https://inertiajs.com/the-protocol). SSR tidak mengubah ini. Apa pun wadahnya (atribut atau elemen `<script>`), isinya tetap publik.

## Prinsip dari maintainer Inertia

> "All data sent in an Inertia response is publicly available and should be treated as such. Only share data that is safe to share."
> Jonathan Reinink, [inertiajs/inertia#1430](https://github.com/inertiajs/inertia/discussions/1430)

Perlakukan semua props sebagai data publik untuk user yang membuka halaman itu.

## 1. Filter props di controller

Prioritas utama. Semua langkah lain hanya pelengkap.

```php
// Salah: model utuh, semua kolom (dan relasi yang sudah di-load) ikut terkirim
return Inertia::render('Products/Show', [
    'product' => $product,
    'orders'  => $user->orders,
]);

// Benar: hanya field yang dirender UI
return Inertia::render('Products/Show', [
    'product' => $product->only(['id', 'name', 'slug', 'price', 'description', 'images']),
]);

// Lebih konsisten: API Resource sebagai kontrak output
return Inertia::render('Products/Show', [
    'product' => new ProductResource($product),
]);
```

### Pola filtering

**`select()` di query** (halaman list/index):

```php
$products = Product::select(['id', 'name', 'slug', 'price', 'discount_price', 'main_image', 'category_id'])
    ->with(['category:id,name,slug'])
    ->paginate(12);
```

**`makeHidden()`** (sembunyikan field tertentu tanpa mengubah query):

```php
$transaction->makeHidden(['admin_note', 'payment_reference', 'qr_string']);
```

**`only()`** (model tunggal):

```php
'user' => $user->only(['id', 'name', 'email', 'avatar']),
```

**Kolom relasi**:

```php
Product::with([
    'category:id,name,slug',
    'variants:id,product_id,name,additional_price,stock',
])->get();
```

**`map()` ke array eksplisit** (paling ketat, cocok untuk halaman publik yang ramai):

```php
'featuredProducts' => Product::where('is_featured', true)
    ->select('id', 'name', 'slug', 'price', 'discount_price', 'main_image', 'category_id')
    ->with('category:id,name')
    ->limit(8)
    ->get()
    ->map(fn ($p) => [
        'id'             => $p->id,
        'name'           => $p->name,
        'slug'           => $p->slug,
        'price'          => $p->price,
        'discount_price' => $p->discount_price,
        'main_image_url' => $p->main_image_url,   // accessor dihitung di sini, bukan di select()
        'category'       => ['name' => $p->category->name],
    ]),
```

### Panduan field

| Data | Kirim? | Alasan |
|---|---|---|
| `id`, `name`, `price`, `image` | Ya | Dibutuhkan untuk render |
| `password`, `remember_token`, secret 2FA | Tidak | Sensitif |
| `created_at`, `updated_at` | Hanya bila ditampilkan | Info internal |
| `cost_price`, `profit_margin`, catatan admin | Tidak | Data bisnis internal |
| Model user utuh | Tidak | Pilih field spesifik |
| Data khusus admin | Tidak di halaman publik | Pisahkan per halaman/role |

Field yang umumnya tidak perlu sampai ke user biasa:

| Model | Field |
|---|---|
| Produk/konten | `is_active`, flag internal, `meta_*` (bila tidak dirender), timestamps, `deleted_at`, stok internal |
| Transaksi | `admin_note`, `payment_reference`, kode/QR pembayaran (kecuali di halaman pembayaran milik user itu) |
| User | `password`, `remember_token`, `email_verified_at`, `is_active`, timestamps |
| Semua model | `deleted_at`, foreign key yang tidak dipakai UI |

Daftar ini titik awal. Cek dulu field mana yang benar-benar dipakai komponen frontend (grep nama prop di file page) sebelum membuang, supaya UI tidak rusak.

### Jebakan Eloquent

- **Foreign key wajib ikut** saat memilih kolom relasi. `'variants:name,stock'` menghasilkan `[]` karena Eloquent tidak bisa mencocokkan relasi. Benar: `'variants:id,product_id,name,stock'`. Begitu juga `select()` di model induk harus menyertakan `category_id` bila `with('category:...')`.
- **`select()` hanya boleh kolom database nyata.** Accessor/computed (`avg_rating`, `main_image_url`) di `select()` menyebabkan SQL error (500 di production). Accessor otomatis ikut lewat `$appends` atau hitung di `map()`.
- **Nama kolom harus persis.** Cocokkan setiap field di `select()` dengan migration (termasuk migration `alter table` berikutnya). Salah nama (`image_path` vs `path`, `sort_order` vs `order`) juga 500.
- **`$appends` ikut terkirim.** Accessor di `$appends` muncul di setiap serialisasi model; pastikan isinya juga aman.
- Setelah mengubah `select()`, buka setiap halaman terdampak secara lokal sebelum deploy.

## 2. Filter shared data

`share()` di `app/Http/Middleware/HandleInertiaRequests.php` dikirim ke **setiap halaman**, termasuk halaman publik. Jaga tetap minimal.

```php
public function share(Request $request): array
{
    $user = $request->user();

    return [
        ...parent::share($request),
        'auth' => [
            'user' => $user ? [
                'id'          => $user->id,
                'name'        => $user->name,
                'email'       => $user->email,
                'avatar'      => $user->avatar,
                'roles'       => $user->getRoleNames()->toArray(),
                'permissions' => $user->getAllPermissions()->pluck('name')->toArray(),
            ] : null,
        ],
        'flash' => ['success' => fn () => $request->session()->get('success')],
    ];
}
```

Catatan:
- Jangan `'user' => $request->user()` (model utuh, termasuk kolom 2FA dan apa pun yang di-load).
- `roles`/`permissions` boleh untuk menyembunyikan tombol di UI, tetapi user bisa melihat nama role dan permission miliknya. Otorisasi tetap di server (policy/gate/middleware).
- Angka ringkas (`cartCount`), pesan flash: aman.
- Data mahal atau jarang dipakai: bungkus closure (lazy) atau pindahkan ke props halaman yang butuh saja.

## 3. Route list: Ziggy vs Wayfinder

| Aspek | Ziggy | Wayfinder |
|---|---|---|
| Route list di browser | Ya, semua nama route + pola URL di page source | Tidak, URL di-generate ke TypeScript saat build |
| Route admin terlihat | Ya, kecuali difilter | Tidak ada daftar yang dikirim |
| Beban per page load | Puluhan KB JSON pada app besar | Hanya fungsi yang di-import |

Wayfinder aman by design untuk route list, tetapi fungsi route yang di-import oleh halaman admin ikut masuk ke chunk halaman itu. Bila semua halaman masih di satu bundle, URL admin tetap bisa ditemukan di chunk; gabungkan dengan pemisahan bundle (lihat `hidden-routes.md`).

Bila masih memakai Ziggy, kecualikan route sensitif. Cara paling sederhana di `config/ziggy.php`:

```php
return [
    'except' => ['admin.*', 'horizon.*', 'telescope.*', 'debugbar.*'],
];
```

Atau filter per user saat dibagikan lewat Inertia:

```php
use Tighten\Ziggy\Ziggy;

'ziggy' => function () use ($request) {
    $ziggy = new Ziggy;
    if (! $request->user()?->hasRole('admin')) {
        $ziggy = $ziggy->filter(['admin.*'], false); // false = kecualikan pola ini
    }
    return [...$ziggy->toArray(), 'location' => $request->url()];
},
```

Periksa juga `@routes` di Blade: tanpa argumen group, directive itu mencetak semua route yang tidak dikecualikan.

## 4. History encryption

Fitur Inertia v2+. Page object di `history.state` dienkripsi sehingga setelah logout, tombol back tidak menampilkan data halaman sebelumnya.

Global, `config/inertia.php`:

```php
'history' => [
    'encrypt' => (bool) env('INERTIA_ENCRYPT_HISTORY', false),
],
```

lalu `INERTIA_ENCRYPT_HISTORY=true` di `.env` production (dan dokumentasikan di `.env.example`).

Per request atau per grup route:

```php
Inertia::encryptHistory();
return Inertia::render('Dashboard', [...]);
```

```php
use Inertia\Middleware\EncryptHistory;

Route::middleware([EncryptHistory::class])->group(function () {
    Route::get('/dashboard', ...);
    Route::get('/profile', ...);
});
```

Saat logout, rotasi kunci agar history lama tidak bisa didekripsi:

```php
Inertia::clearHistory();
```

Cara kerja: client mengenkripsi page object dengan `window.crypto.subtle` sebelum `pushState`, kuncinya disimpan di session storage, dan `clearHistory()` membuang kunci itu. Butuh secure context (HTTPS; `localhost` juga dianggap aman). Fitur ini tidak menyembunyikan apa pun dari user yang sedang login; tujuannya melindungi perangkat bersama setelah logout.

## 5. Hapus `data-page` setelah hydration (kosmetik)

Menghilangkan atribut dari Inspect Element, **tidak** dari View Page Source atau curl. Murah, jadi boleh dipasang, tetapi jangan dihitung sebagai perbaikan.

Svelte:

```typescript
setup({ el, App, props }) {
    mount(App, { target: el!, props });
    delete el!.dataset.page;
},
```

React:

```tsx
setup({ el, App, props }) {
    createRoot(el!).render(<App {...props} />);
    delete el!.dataset.page;
},
```

Vue:

```typescript
setup({ el, App, props, plugin }) {
    createApp({ render: () => h(App, props) }).use(plugin).mount(el!);
    delete el!.dataset.page;
},
```

Untuk SSR dengan hydration (`hydrate()` / `createSSRApp`), hapus atributnya setelah hydrate selesai, bukan sebelumnya.

| Skenario | Data terlihat? |
|---|---|
| View Page Source / curl | Ya |
| Inspect Element (setelah JS jalan) | Tidak |
| Kunjungan Inertia berikutnya | Ya, sebagai JSON di tab Network |

## 6. Audit manual dan contoh temuan

Jalankan `scripts/audit_page_props.py` (lihat SKILL.md). Bila hanya ada shell, versi cepat:

```bash
curl -s https://example.com/ \
  | python3 -c "import sys,re,html,json; m=re.search(r'data-page=\"(.*?)\"', sys.stdin.read(), re.S); p=json.loads(html.unescape(m.group(1))); print(json.dumps(p['props'], indent=2)[:4000])"
```

Laravel meng-escape atribut dengan kutip ganda dan entity `&quot;`, jadi pola `data-page='...'` dengan kutip tunggal biasanya tidak menemukan apa-apa.

Untuk halaman yang butuh login, simpan dulu HTML-nya dari browser (Save Page As, atau salin header Cookie ke env var lalu pakai `--cookie-env`). Audit sebagai guest **dan** sebagai setiap role.

Contoh pola temuan yang khas di halaman beranda toko online:

| Prop | Temuan | Perbaikan |
|---|---|---|
| Route list (Ziggy) | Sepertiga ukuran page object, puluhan route admin terlihat oleh guest | Migrasi ke Wayfinder atau `except` |
| `featuredProducts`, `latestProducts` | 8 item x 30+ field: dimensi, flag `is_active`, `meta_*`, timestamps, stok, relasi lengkap | `select()` + `map()` ke ~10 field |
| `categories` | Field urutan, flag aktif, timestamps | `select('id','name','slug','icon')` |
| `auth`, `flash`, counter | Kecil dan sudah difilter | Biarkan |

Hasil yang wajar setelah perbaikan: page object turun 60-80%, dan tidak ada field internal di daftar `props`.

## Checklist

```
- [ ] Setiap controller: hanya field yang dirender (select/only/Resource/map)
- [ ] Tidak ada model utuh, password/token, data bisnis internal, atau timestamps yang tidak ditampilkan
- [ ] Data khusus admin tidak dikirim ke halaman publik
- [ ] share() minimal; user hanya field yang dipakai UI
- [ ] Route list tidak terkirim (Wayfinder) atau sudah difilter (Ziggy)
- [ ] INERTIA_ENCRYPT_HISTORY=true di production + clearHistory() saat logout
- [ ] (Kosmetik) delete el.dataset.page di setup()
- [ ] Kolom di select() dicocokkan dengan migration; relasi menyertakan foreign key
- [ ] Audit ulang page source production (guest + tiap role) secara berkala
```

## Sumber

- [Inertia: History encryption](https://inertiajs.com/history-encryption)
- [Inertia: Responses](https://inertiajs.com/responses)
- [Inertia: The protocol](https://inertiajs.com/the-protocol)
- [inertiajs/inertia#1430: menonaktifkan atribut data-page](https://github.com/inertiajs/inertia/discussions/1430)
