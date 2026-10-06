# Katalog Warning Svelte 5

Satu bagian per kode warning: pesan, kondisi pemicu, contoh before/after, dan kapan boleh suppress. Teks pesan bisa sedikit berbeda antar versi Svelte, jadi cocokkan berdasarkan **kode**.

## Daftar isi

- [state_referenced_locally](#state_referenced_locally)
- [a11y_consider_explicit_label](#a11y_consider_explicit_label)
- [a11y_label_has_associated_control](#a11y_label_has_associated_control)
- [a11y_missing_attribute](#a11y_missing_attribute)
- [Template untuk kode baru](#template-untuk-kode-baru)

---

## state_referenced_locally

**Pesan:** "This reference only captures the initial value of `x`. Did you mean to reference it inside a closure instead?" (akhiran bisa "inside a derived" bila referensinya ada di dalam `$state(...)`). Versi lama: "State referenced in its own scope will never update."

**Kondisi pemicu.** Dalam runes mode, sebuah nilai reaktif **dibaca** langsung di level teratas `<script>` (bukan di dalam fungsi, closure, atau template). Nilai reaktif yang dimaksud:
- prop dari `$props()` (selalu),
- `$derived` dan `$state.raw`,
- `$state` yang di-reassign, atau yang nilai awalnya primitif.

Pembacaan di level teratas hanya terjadi sekali saat komponen dibuat, sehingga hasilnya membeku pada nilai awal. Bila prop berganti (navigasi ke data lain, parent meng-update), variabel itu tidak ikut berubah. Pada beberapa rilis Svelte 5 warning ini diperluas ke props, sehingga upgrade bisa memunculkan puluhan warning sekaligus. Tim Svelte menganggapnya *by design*: hampir selalu, memakai nilai awal prop di level teratas adalah bug.

### Fix 1: nilai turunan → `$derived`

```svelte
<!-- Sebelum: membeku pada nilai awal -->
<script lang="ts">
  let { settings } = $props();
  let contactInfo = [
    { title: 'Alamat', content: settings.address || '-' },
    { title: 'Telepon', content: settings.phone || '-' },
  ];
</script>

<!-- Sesudah: ikut berubah saat settings berubah -->
<script lang="ts">
  let { settings } = $props();
  let contactInfo = $derived([
    { title: 'Alamat', content: settings.address || '-' },
    { title: 'Telepon', content: settings.phone || '-' },
  ]);
</script>
```

Pola yang sama untuk nilai hitungan dan struktur turunan lain:

```svelte
<script lang="ts">
  let { price, discount, user } = $props();

  // Sebelum: let finalPrice = price - (discount || 0);
  let finalPrice = $derived(price - (discount || 0));

  // Sebelum: let breadcrumbs = [{ label: 'Home', href: '/' }, { label: user.name }];
  let breadcrumbs = $derived([{ label: 'Home', href: '/' }, { label: user.name }]);
</script>
```

Untuk logika multi-baris pakai `$derived.by(() => { ... })`.

Props dari server yang "tidak pernah berubah di client" tetap sebaiknya dibungkus `$derived`: aman, tanpa biaya berarti, dan tetap benar bila nanti halaman yang sama dirender ulang dengan data lain (navigasi client-side ke route yang sama).

### Fix 2: state dioper ke fungsi atau context → closure

```svelte
<!-- Sebelum: Child menerima angka 0 dan tidak pernah update -->
<script>
  import { setContext } from 'svelte';
  let count = $state(0);
  setContext('count', count);
</script>

<!-- Sesudah: Child memanggil count() dan selalu dapat nilai terbaru -->
<script>
  import { setContext } from 'svelte';
  let count = $state(0);
  setContext('count', () => count);
</script>
```

Alternatif: oper objek `$state({...})` (proxy) lalu mutasi propertinya, bukan reassign variabelnya.

### Disengaja: form yang menyalin nilai awal

Form edit biasanya *harus* menyalin nilai awal, supaya ketikan pengguna tidak tertimpa saat prop di-refresh. Di sini warning adalah false positive yang disengaja. Suppress dengan alasan:

```svelte
<script lang="ts">
  let { product } = $props();
  // svelte-ignore state_referenced_locally (salinan awal untuk form edit, sengaja tidak mengikuti prop)
  let form = $state({
    name: product?.name ?? '',
    price: product?.price ?? 0,
  });
</script>
```

Bila form harus **reset saat item berganti** (mis. pindah dari produk A ke produk B tanpa unmount), jangan sinkronkan dengan `$effect`. Pilih salah satu:
- Paksa remount di parent: `{#key product.id}<ProductForm {product} />{/key}`. Suppress di dalam `ProductForm` tetap valid.
- Pakai `$derived` yang ditimpa (Svelte ≥ 5.25 mengizinkan reassign `$derived` yang dideklarasi dengan `let`): nilainya bisa diubah pengguna dan kembali mengikuti sumber saat sumbernya berubah.

```svelte
<script lang="ts">
  let { product } = $props();
  let name = $derived(product.name); // reset otomatis saat product berganti
</script>

<input value={name} oninput={(e) => (name = e.currentTarget.value)} />
```

### Ringkas

| Situasi | Pendekatan |
|---|---|
| Array/objek/nilai hitungan dari props | `$derived()` / `$derived.by()` |
| `const` yang diisi dari props | `$derived()` |
| State/prop dioper ke `setContext` atau fungsi | Closure `() => value` |
| Form edit menyalin nilai awal | Suppress dengan alasan, plus `{#key}` di parent bila perlu reset |
| Nilai yang bisa diedit tapi harus reset saat sumber berubah | `$derived` yang ditimpa |

---

## a11y_consider_explicit_label

**Pesan:** "Buttons and links should either contain text or have an `aria-label`, `aria-labelledby` or `title` attribute"

**Kondisi pemicu.** `<button>` atau `<a>` tidak punya `aria-label`/`aria-labelledby`/`title`, tidak punya spread props, dan isinya tidak mengandung teks. Elemen kosong seperti `<i class="icon-x"></i>` atau `<svg>` tanpa teks dianggap tidak berisi apa pun. Screen reader hanya bisa mengumumkan "button" tanpa nama.

```svelte
<!-- Sebelum -->
<button onclick={close}>
  <i class="icon icon-close"></i>
</button>

<a href={social.url} class="icon-link">
  <i class={social.icon}></i>
</a>

<!-- Sesudah: aria-label -->
<button onclick={close} aria-label="Tutup">
  <i class="icon icon-close" aria-hidden="true"></i>
</button>

<a href={social.url} class="icon-link" aria-label={social.name}>
  <i class={social.icon} aria-hidden="true"></i>
</a>

<!-- Alternatif: teks visually hidden -->
<button onclick={close}>
  <i class="icon icon-close" aria-hidden="true"></i>
  <span class="sr-only">Tutup</span>
</button>
```

`sr-only` adalah utilitas Tailwind. Tanpa Tailwind, definisikan sendiri:

```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

Label harus menjelaskan **aksi atau tujuan**, bukan nama ikonnya, dan memakai bahasa antarmuka aplikasi:

| Ikon | Contoh label |
|---|---|
| Silang / close | "Tutup" |
| Tempat sampah | "Hapus" (lebih baik spesifik: "Hapus produk") |
| Pensil | "Edit" |
| Kaca pembesar | "Cari" |
| Hamburger | "Menu" (atau "Buka menu") |
| Link media sosial | Nama platform, mis. `{social.name}` |
| Lonceng | "Notifikasi" |
| Keranjang | "Keranjang" |

**Catatan.**
- Ikon berupa komponen (`<CloseIcon />`) tidak memicu warning karena compiler menganggap komponen punya konten. Tombol seperti itu tetap butuh `aria-label`, jadi periksa manual.
- Menambahkan `aria-hidden="true"` pada `<button>`/`<a>` memang menghilangkan warning, tetapi menyembunyikan kontrol dari screen reader. Itu bukan perbaikan. `aria-hidden` dipasang pada **ikonnya**, bukan tombolnya.
- Suppress hampir tidak pernah tepat untuk kode ini.

---

## a11y_label_has_associated_control

**Pesan:** "A form label must be associated with a control"

**Kondisi pemicu.** `<label>` **tidak** punya atribut `for`, tidak punya spread props, **dan** tidak membungkus kontrol. Yang dihitung sebagai kontrol: elemen labelable (`input`, `select`, `textarea`, `button`, `meter`, `output`, `progress`), komponen apa pun, `{@render ...}`, `<svelte:element>`, dan slot. Artinya warning ini hampir tidak pernah false positive: begitu ada `for` atau ada komponen di dalam label, warning tidak muncul.

```svelte
<!-- Sebelum: label berdiri sendiri -->
<label>Nama</label>
<input type="text" bind:value={name} />

<!-- Sesudah, opsi 1 (default): for + id -->
<label for="name">Nama</label>
<input id="name" type="text" bind:value={name} />

<!-- Sesudah, opsi 2: bungkus kontrolnya -->
<label>
  Nama
  <input type="text" bind:value={name} />
</label>
```

Dalam komponen yang bisa dirender lebih dari sekali, hindari `id` statis yang bentrok. Pakai `$props.id()` (Svelte ≥ 5.20), yang konsisten antara SSR dan hydration:

```svelte
<script lang="ts">
  const uid = $props.id();
  let { value = $bindable('') } = $props();
</script>

<label for="{uid}-name">Nama</label>
<input id="{uid}-name" type="text" bind:value />
```

**Komponen input custom.** Compiler hanya memeriksa *keberadaan* atribut `for`, tidak memeriksa apakah `id` yang dituju benar-benar ada. Jadi `<label for="name">` + `<TextInput id="name" />` lolos tanpa warning, tetapi asosiasinya baru benar bila `TextInput` meneruskan `id` ke elemen `<input>` aslinya:

```svelte
<!-- TextInput.svelte -->
<script lang="ts">
  let { id, value = $bindable(''), ...rest } = $props();
</script>

<input {id} bind:value {...rest} />
```

Suppress hanya bila `<label>` sengaja dipakai sebagai teks biasa. Dalam kasus itu, lebih baik ganti elemennya (`<span>`/`<p>`) daripada suppress.

---

## a11y_missing_attribute

**Pesan:** "`<img>` element should have an alt attribute" (bentuk umum: "`<tag>` element should have a/an `attr` attribute").

**Kondisi pemicu.** Elemen tidak punya atribut wajibnya dan tidak memakai spread props:

| Elemen | Atribut wajib (salah satu) |
|---|---|
| `<img>` | `alt` |
| `<area>` | `alt`, `aria-label`, `aria-labelledby` |
| `<iframe>` | `title` |
| `<object>` | `title`, `aria-label`, `aria-labelledby` |
| `<html>` | `lang` |
| `<a>` | `href` (kecuali punya `id`, `name`, atau `aria-disabled="true"`) |

```svelte
<!-- Sebelum -->
<img src={product.image} />

<!-- Sesudah: gambar bermakna, alt deskriptif -->
<img src={product.image} alt={product.name} />

<!-- Sesudah: gambar dekoratif, alt kosong -->
<img src="/pattern.svg" alt="" />
```

`alt=""` (string kosong) valid untuk gambar dekoratif dan membuat screen reader melewatinya. Jangan menghapus atribut `alt` sama sekali, karena screen reader lalu membacakan nama file.

Untuk `<a>` tanpa `href` yang sebenarnya memicu aksi (bukan navigasi), perbaikannya adalah mengganti menjadi `<button type="button">`, bukan menambahkan `href="#"` (yang memicu warning `a11y_invalid_attribute`).

Suppress tidak tepat untuk kode ini.

---

## Template untuk kode baru

Saat menemukan kode warning yang belum ada di file ini, baca dulu definisinya di `https://svelte.dev/docs/svelte/compiler-warnings` (dan bila ragu, kondisi pemicunya di source compiler Svelte), lalu tambahkan bagian baru di atas bagian ini dan entri di daftar isi:

````markdown
## <kode_warning>

**Pesan:** "<teks pesan persis>"

**Kondisi pemicu.** <Kapan compiler memunculkannya, termasuk pengecualian (spread props, atribut tertentu).>

```svelte
<!-- Sebelum -->
...

<!-- Sesudah -->
...
```

**Kapan boleh suppress.** <Situasi false positive yang terverifikasi, atau "Tidak tepat untuk kode ini.">
````

Tambahkan juga satu baris ke tabel ringkasan di SKILL.md bila kode itu sering muncul.
