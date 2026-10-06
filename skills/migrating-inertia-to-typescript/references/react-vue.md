# Fase 4-6: React dan Vue 3 + Inertia

## Daftar isi

- React: props dan children
- React: event dan ref
- React: usePage, useForm, layout
- Vue: props, emits, model
- Vue: slots, ref, generic
- Vue: usePage, useForm, layout
- Pages (kedua framework)
- Rujukan resmi

Augmentasi `InertiaConfig`, aturan type data Laravel, dan urutan migrasi sama dengan Svelte. Lihat SKILL.md dan `types.md`.

## React: props dan children

Rename `.jsx` → `.tsx`. Hapus `PropTypes` setelah interface menggantikannya.

```tsx
import type { ReactNode, ComponentPropsWithoutRef } from 'react';
import type { Product } from '@/types';

interface ProductListProps {
    products: Product[];
    title?: string;
    children?: ReactNode;
    onSelect?: (product: Product) => void;
}

export default function ProductList({ products, title = 'Produk', children, onSelect }: ProductListProps) {
    return (
        <section>
            <h2>{title}</h2>
            {products.map((p) => (
                <button key={p.id} onClick={() => onSelect?.(p)}>{p.name}</button>
            ))}
            {children}
        </section>
    );
}

// Extend atribut native untuk komponen pembungkus
interface ButtonProps extends ComponentPropsWithoutRef<'button'> {
    variant?: 'primary' | 'secondary' | 'danger';
}

export function Button({ variant = 'primary', className = '', ...rest }: ButtonProps) {
    return <button className={`btn btn-${variant} ${className}`} {...rest} />;
}
```

Generic component:

```tsx
interface TableProps<T extends { id: number | string }> {
    rows: T[];
    columns: { key: keyof T & string; label: string }[];
    renderCell?: (row: T, key: keyof T & string) => ReactNode;
}

export function DataTable<T extends { id: number | string }>({ rows, columns, renderCell }: TableProps<T>) {
    /* ... */
}
```

## React: event dan ref

```tsx
import { useRef, useState, type ChangeEvent, type FormEvent } from 'react';

const [items, setItems] = useState<Product[]>([]);        // array kosong perlu generic
const inputRef = useRef<HTMLInputElement>(null);

function onChange(e: ChangeEvent<HTMLInputElement>) { /* e.target.value: string */ }
function onFiles(e: ChangeEvent<HTMLInputElement>) {
    const files: File[] = Array.from(e.target.files ?? []);
}
function onSubmit(e: FormEvent<HTMLFormElement>) { e.preventDefault(); }
```

## React: usePage, useForm, layout

```tsx
import type { FormEvent } from 'react';
import { useForm, usePage } from '@inertiajs/react';
import type { Category } from '@/types';

interface CreateProductProps {
    categories: Category[];
}

export default function Create({ categories }: CreateProductProps) {
    const { auth } = usePage().props;   // shared props bertipe dari InertiaConfig

    const { data, setData, post, processing, errors } = useForm<{
        name: string;
        category_id: string;
        image: File | null;
    }>({ name: '', category_id: '', image: null });

    function submit(e: FormEvent<HTMLFormElement>) {
        e.preventDefault();
        post('/admin/products');
    }

    return (
        <form onSubmit={submit}>
            <input value={data.name} onChange={(e) => setData('name', e.target.value)} />
            {errors.name && <p>{errors.name}</p>}
            <button disabled={processing}>Simpan</button>
        </form>
    );
}
```

`setData('nama_field', value)` memeriksa nama field dan tipe nilainya. Untuk props page di komponen anak: `usePage<{ products: Product[] }>().props.products`.

Layout persisten:

```tsx
import type { ReactNode } from 'react';
import AppLayout from '@/Layouts/AppLayout';

Create.layout = (page: ReactNode) => <AppLayout>{page}</AppLayout>;
```

Bila TypeScript menolak properti `layout` pada fungsi, tulis page sebagai `const Create = (...) => {...}` lalu tambahkan `Create.layout`, atau buat type `PageWithLayout<P> = FC<P> & { layout?: (page: ReactNode) => ReactNode }` (import `FC` dan `ReactNode` dari `react`).

## Vue: props, emits, model

Ubah `<script setup>` → `<script setup lang="ts">` dan ganti deklarasi runtime dengan generic.

```vue
<script setup lang="ts">
import type { Product } from '@/types';

interface Props {
    products: Product[];
    title?: string;
}

const props = withDefaults(defineProps<Props>(), { title: 'Produk' });

const emit = defineEmits<{
    select: [product: Product];
    sort: [field: string, order: 'asc' | 'desc'];
}>();

// Vue 3.4+: two-way binding pengganti prop + emit update:modelValue
const open = defineModel<boolean>('open', { default: false });
const search = defineModel<string>({ default: '' });
</script>
```

Pada Vue 3.5+, destructuring props reaktif (`const { title = 'Produk' } = defineProps<Props>()`) bisa menggantikan `withDefaults`.

Sebelum migrasi, props runtime seperti `defineProps({ products: Array })` hanya memberi type `unknown[]`; itu sebabnya generic lebih disukai.

## Vue: slots, ref, generic

```vue
<script setup lang="ts" generic="T extends { id: number | string }">
import { ref, useTemplateRef } from 'vue';

const props = defineProps<{ rows: T[] }>();

defineSlots<{
    default?: () => unknown;
    row?: (scope: { item: T; index: number }) => unknown;
}>();

const selected = ref<T | null>(null);
const input = useTemplateRef<HTMLInputElement>('input');   // Vue 3.5+; versi lama: ref<HTMLInputElement | null>(null)

function onFiles(e: Event) {
    const target = e.target as HTMLInputElement;
    const files: File[] = Array.from(target.files ?? []);
}
</script>
```

## Vue: usePage, useForm, layout

```vue
<script setup lang="ts">
import { computed } from 'vue';
import { useForm, usePage } from '@inertiajs/vue3';
import AppLayout from '@/Layouts/AppLayout.vue';
import type { Category } from '@/types';

defineOptions({ layout: AppLayout });   // layout persisten

defineProps<{ categories: Category[] }>();

const page = usePage();
const user = computed(() => page.props.auth.user);   // bertipe dari InertiaConfig

const form = useForm<{ name: string; category_id: string; image: File | null }>({
    name: '',
    category_id: '',
    image: null,
});

function submit() {
    form.post('/admin/products');
}
// form.errors.name → string | undefined, form.processing → boolean
</script>
```

`page.props` reaktif; bungkus dengan `computed` bila dipakai di logika, bukan disalin ke variabel biasa.

## Pages (kedua framework)

Sama seperti Svelte: cari controller dengan `grep -rn "Inertia::render('Nama/Page'" app/ routes/`, salin key array ke interface props, jangan deklarasi ulang shared props. Pilih `Paginator<T>` atau `PaginatedResource<T>` sesuai bentuk pagination yang dikirim (lihat `types.md`). Deferred/optional prop ditandai opsional.

## Rujukan resmi

- inertiajs.com/docs/v2/advanced/typescript
- inertiajs.com/docs/v2/the-basics/forms
- react-typescript-cheatsheet.netlify.app
- vuejs.org/guide/typescript/composition-api
- Starter kit resmi Laravel untuk React dan Vue (repo `laravel/react-starter-kit` dan `laravel/vue-starter-kit`) sebagai contoh struktur TS yang sudah jadi
