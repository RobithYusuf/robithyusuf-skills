# Fase 4-6: Svelte 5 + Inertia

## Daftar isi

- Aturan umum
- Pola props A-E
- Generic component dan atribut HTML native
- State, derived, ref DOM, dan event
- Inertia: $page, useForm, usePage, router
- Pages
- Urutan dan prioritas komponen
- Inertia + Svelte vs SvelteKit
- Rujukan resmi

## Aturan umum

- Ganti `<script>` → `<script lang="ts">` dan beri `interface Props` untuk setiap `$props()`.
- `import type { Snippet } from 'svelte'` untuk `children` dan slot bernama.
- `$bindable()` tetap bekerja seperti biasa; type-nya ditulis di `Props`, default-nya di destructuring.
- `$state()` dan `$derived()` menyimpulkan type sendiri; anotasi hanya bila nilai awal tidak mewakili (array kosong, `null`).
- `$effect()` tidak butuh anotasi return.
- Callback props (`onclose`, `onsort`) diberi signature fungsi eksplisit, bukan `Function`.

## Pola props A-E

**A. Props sederhana**

```svelte
<!-- Sebelum -->
<script>
    let { title = '', size = 'md', disabled = false, children } = $props();
</script>

<!-- Sesudah -->
<script lang="ts">
    import type { Snippet } from 'svelte';

    interface Props {
        title?: string;
        size?: 'sm' | 'md' | 'lg';
        disabled?: boolean;
        children?: Snippet;
    }

    let { title = '', size = 'md', disabled = false, children }: Props = $props();
</script>
```

**B. Props dengan `$bindable`**

```svelte
<script lang="ts">
    interface Props {
        show?: boolean;
        value?: string;
        onclose?: (() => void) | null;
    }

    let { show = $bindable(false), value = $bindable(''), onclose = null }: Props = $props();
</script>
```

**C. Rest props.** Lebih baik extend atribut native daripada index signature (lihat bagian berikutnya). Index signature `[key: string]: unknown` hanya untuk transisi cepat.

```svelte
<script lang="ts">
    import type { Snippet } from 'svelte';

    interface Props {
        type?: 'button' | 'submit' | 'reset';
        class?: string;
        onclick?: ((e: MouseEvent) => void) | null;
        children?: Snippet;
        [key: string]: unknown;
    }

    let { type = 'button', class: className = '', onclick = null, children, ...restProps }: Props = $props();
</script>
```

**D. Callback props**

```svelte
<script lang="ts">
    interface SortEvent {
        field: string;
        order: 'asc' | 'desc';
    }

    interface Props {
        onsort?: (event: SortEvent) => void;
        ondelete?: (id: number) => void;
        onview?: (id: number) => void;
    }

    let { onsort = () => {}, ondelete = () => {}, onview = () => {} }: Props = $props();
</script>
```

**E. Banyak snippet (modal, layout, card)**

```svelte
<script lang="ts">
    import type { Snippet } from 'svelte';

    interface Props {
        children?: Snippet;
        header?: Snippet;
        footer?: Snippet;
        row?: Snippet<[item: { id: number; name: string }, index: number]>;   // snippet berparameter
    }

    let { children, header, footer, row }: Props = $props();
</script>
```

## Generic component dan atribut HTML native

**Extend atribut native** agar `restProps` bertipe benar dan autocomplete atribut HTML tetap ada:

```svelte
<script lang="ts">
    import type { HTMLButtonAttributes } from 'svelte/elements';

    interface Props extends HTMLButtonAttributes {
        variant?: 'primary' | 'secondary' | 'danger';
    }

    let { variant = 'primary', children, ...restProps }: Props = $props();
</script>

<button {...restProps} class="btn btn-{variant}">{@render children?.()}</button>
```

Tersedia juga `HTMLInputAttributes`, `HTMLTextareaAttributes`, `HTMLSelectAttributes`, `HTMLAnchorAttributes`.

**Generic component** (data table, list, select):

```svelte
<script lang="ts" generics="T extends { id: number | string }">
    import type { Snippet } from 'svelte';

    interface Column {
        key: keyof T & string;
        label: string;
        sortable?: boolean;
    }

    interface Props {
        rows: T[];
        columns: Column[];
        cell?: Snippet<[row: T, column: Column]>;
        onrowclick?: (row: T) => void;
    }

    let { rows, columns, cell, onrowclick }: Props = $props();
</script>
```

Ambil props dari komponen lain: `import type { ComponentProps } from 'svelte'; type ButtonProps = ComponentProps<typeof Button>;`.

## State, derived, ref DOM, dan event

```svelte
<script lang="ts">
    import type { Product } from '@/types';

    let items = $state<Product[]>([]);              // array kosong perlu generic
    let selected = $state<Product | null>(null);
    let total = $derived(items.reduce((sum, p) => sum + Number(p.price), 0));

    let input: HTMLInputElement | undefined = $state();   // untuk bind:this

    function onKeydown(e: KeyboardEvent): void {
        if (e.key === 'Enter') input?.blur();
    }

    function onFiles(e: Event & { currentTarget: HTMLInputElement }): void {
        const files: File[] = Array.from(e.currentTarget.files ?? []);
    }

    function readPreview(file: File): void {
        const reader = new FileReader();
        reader.onload = () => {
            const url = reader.result as string;   // readAsDataURL selalu string
        };
        reader.readAsDataURL(file);
    }
</script>
```

Event DOM yang sering dipakai: `MouseEvent`, `KeyboardEvent`, `DragEvent`, `FocusEvent`, `InputEvent`, `SubmitEvent`. Untuk `CustomEvent` lintas komponen (`window.dispatchEvent`), deklarasikan payload-nya: `CustomEvent<{ id: number }>`. Untuk `<svelte:window>` dan listener global, augment `WindowEventMap` di `global.d.ts` agar `addEventListener('nama-event', ...)` bertipe.

## Inertia: $page, useForm, usePage, router

Pada adapter Svelte v2, `page` dan hasil `useForm()` adalah **Svelte store**, bukan rune. Akses selalu dengan prefix `$`. Cek ulang bila adapter di-upgrade ke versi berbasis rune.

**Shared props sudah bertipe global** lewat `InertiaConfig.sharedPageProps`, jadi tidak dideklarasi ulang:

```svelte
<script lang="ts">
    import type { Product } from '@/types';
    import { page, router } from '@inertiajs/svelte';

    interface Props {
        featuredProducts?: Product[];
    }

    let { featuredProducts = [] }: Props = $props();

    const isAuthenticated = $derived($page.props.auth.user !== null);

    function addToCart(product: Product): void {
        if (!isAuthenticated) {
            router.visit('/login');
            return;
        }
        router.post('/cart', { product_id: product.id, quantity: 1 }, {
            preserveScroll: true,
            only: ['flash', 'cartCount'],
            onSuccess: (visit) => {
                const flash = visit.props.flash;   // bertipe dari flashDataType
                if (flash?.success) console.info(flash.success);
            },
        });
    }
</script>
```

**Form helper:**

```svelte
<script lang="ts">
    import type { Product, Category } from '@/types';
    import { useForm } from '@inertiajs/svelte';

    interface Props {
        product?: Product | null;
        categories?: Category[];
    }

    let { product = null, categories = [] }: Props = $props();

    interface ProductForm {
        name: string;
        category_id: string;
        price: string;
        is_active: boolean;
        image: File | null;
    }

    const form = useForm<ProductForm>({
        name: product?.name ?? '',
        category_id: product?.category_id?.toString() ?? '',
        price: product?.price ?? '',
        is_active: product?.status === 'active',
        image: null,
    });

    function submit(e: SubmitEvent): void {
        e.preventDefault();
        if (product) {
            $form.put(`/admin/products/${product.id}`);
        } else {
            $form.post('/admin/products');
        }
    }
    // $form.errors.name → string | undefined, $form.processing → boolean
</script>
```

Pakai `??` bukan `||` untuk default nilai form: `||` mengubah `0` dan `false` yang sah menjadi default. Nilai dari `<select>` dan `<input>` selalu string; simpan sebagai string di form, biarkan Laravel memvalidasi dan meng-cast.

**`usePage<T>()`** untuk props page di luar `$props()` (mis. di komponen anak tanpa prop drilling):

```svelte
<script lang="ts">
    import { usePage } from '@inertiajs/svelte';
    import type { Product } from '@/types';

    const currentPage = usePage<{ products: Product[] }>();
    // $currentPage.props.products → Product[], $currentPage.props.auth tetap bertipe
</script>
```

## Pages

Untuk setiap page, cari controller yang me-render-nya dan salin key array-nya ke `interface Props`:

```bash
grep -rn "Inertia::render('Products/Index'" app/ routes/
grep -rn "inertia('Products/Index'" app/ routes/
```

Contoh terjemahan:

| Controller mengirim | Props di page |
|---|---|
| `'products' => Product::paginate()` | `products: Paginator<Product>` |
| `'products' => ProductResource::collection(...->paginate())` | `products: PaginatedResource<Product>` |
| `'product' => $product ?? null` (form create/edit) | `product?: Product \| null` |
| `'filters' => $request->only('search', 'status')` | `filters: { search?: string; status?: string }` |
| `'status' => session('status')` (halaman auth) | `status?: string` |
| Lazy/deferred prop (`Inertia::defer`, `Inertia::optional`) | `field?: T` (bisa belum ada saat render pertama) |

Page error:

```svelte
<script lang="ts">
    interface Props {
        status?: number;
        message?: string;
    }
    let { status = 500, message = 'Terjadi kesalahan' }: Props = $props();
</script>
```

## Urutan dan prioritas komponen

Gunakan hasil analisis fase 0 (jumlah komponen per folder) untuk menyusun urutan:

| Kelompok | Perhatian khusus |
|---|---|
| UI dasar (badge, spinner, skeleton, avatar, progress) | Union literal untuk `size`/`color`/`variant` |
| UI dengan snippet (card, empty state, accordion) | `Snippet`, snippet berparameter |
| UI dengan binding (modal, tabs, toggle, dropdown) | `$bindable`, callback props, action portal |
| Form input (text, textarea, select, checkbox, file, tag, date) | Extend atribut native, `$bindable(value)` dengan tipe yang tepat (`string[]`, `number`, `File[]`) |
| Komponen data (data table, pagination, filter) | Generic `T`, `Paginator<T>`/`PaginatedResource<T>`, callback sort/filter |
| Layout | `$page.props` shared, flash di `$effect`, state sidebar `$bindable` |
| Pages | Props dari controller, `useForm<T>()`, alur kompleks terakhir |

## Inertia + Svelte vs SvelteKit

Jangan salin pola TypeScript dari tutorial SvelteKit.

| Aspek | SvelteKit | Inertia + Svelte |
|---|---|---|
| Props page | `PageData` otomatis dari `load()` | `interface Props` manual, cocok dengan controller |
| Shared data | `$page.data` dari layout `load()` | `InertiaConfig.sharedPageProps` |
| Type generation | `svelte-kit sync` → `./$types` | Tidak ada (kecuali Wayfinder versi baru) |
| Navigasi | `goto` dari `$app/navigation` | `router` dari `@inertiajs/svelte`, route dari Wayfinder/Ziggy |
| Page store | `page` dari `$app/stores` atau `$app/state` | `page` dari `@inertiajs/svelte` |
| Form | `<form>` + `use:enhance` | `useForm<T>()` |
| Error validasi | `ActionFailure` | `errorValueType` + `$form.errors` |

## Rujukan resmi

- svelte.dev/docs/svelte/typescript (setup, generics, `svelte/elements`, `ComponentProps`)
- svelte.dev/docs/svelte/$props, svelte.dev/docs/svelte/$bindable, svelte.dev/docs/svelte/snippet
- svelte.dev/docs/svelte/svelte-action, svelte.dev/docs/svelte/svelte-store
- inertiajs.com/docs/v2/advanced/typescript
