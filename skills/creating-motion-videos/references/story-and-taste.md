# Cerita, Template Adegan, dan Rasa Visual

## Daftar isi

1. Struktur iklan 30 dan 60 detik
2. Template rencana adegan
3. Hook dan cover
4. Bukti dan klaim
5. Sistem tipografi
6. Warna dan latar
7. Anti-slop beserta alasannya
8. Bekerja dengan umpan balik pemilik

---

## 1. Struktur iklan 30 dan 60 detik

Contoh pada 122 BPM, 30 fps (1 ketukan ≈ 14,75 frame, 16 ketukan ≈ 7,9 dtk):

| Ketukan | Bagian | Isi |
|---|---|---|
| 0–7 | Hook | Masalah dengan kata-kata penonton, gerak sejak frame 0 |
| 7–16 | Aksi | Pengguna melakukan satu hal sederhana di UI asli (mengetik brief, unggah foto) |
| 16 | **Drop** | Momen khas: input berubah menjadi hasil, hard cut di balik objek |
| 16–24 | Hasil | Keluaran asli memenuhi layar, tersusun di ketukan |
| 24–32 | Bukti variasi | Cut per ketukan: beda brand, beda gaya, beda format |
| 32–48 | Pembeda | 2–3 fitur, satu per 4–8 ketukan, masing-masing satu kalimat |
| 48–52 | Penawaran | Harga atau paket, fakta saja |
| 52–60 | CTA | Maskot/brand + URL, diam cukup lama untuk dibaca |

Versi 60 detik: tambahkan adegan masalah nyata sebelum aksi (situasi yang benar-benar terjadi, mis. kerja larut dengan kanvas kosong), lebih banyak fitur, **breakdown** yang lebih tenang (mis. ketukan 72–80) untuk fitur pilihan, lalu drop kedua. Adegan yang dipakai ulang dari versi 30 dtk digeser kelipatan 16 ketukan.

## 2. Template rencana adegan

Tulis ini sebelum kode, dan simpan di README proyek:

| Ketukan | Frame | Visual | Teks layar | SFX | VO |
|---|---|---|---|---|---|
| 0–7 | 0–103 | Ponsel di meja, notifikasi menumpuk | "Kontennya numpuk." | hit kecil di b(3) | (kalimat pembuka) |
| 7–16 | 104–235 | Composer asli, brief diketik, kamera ikut caret | – | typing, click | (diam di drop) |
| 16 | 236 | Kartu terlipat jadi pesawat, menembus lensa | – | fwip + flyby + hit | – |
| … | … | … | … | … | … |

Kolom VO diisi narasi yang **bercerita**, bukan membacakan teks layar. Frasa diletakkan di adegan yang dibicarakannya.

## 3. Hook dan cover

- Dua detik pertama menentukan retensi. Mulai dari masalah atau hasil yang mengejutkan, bukan logo intro.
- Frame 0 sudah bergerak dan sudah ada teks terbaca.
- **Cover** dirancang sebagai frame tersendiri yang diselipkan sebelum potongan (komposisi lebih panjang beberapa frame, semua isi mulai frame 1 sehingga audio tetap sinkron). Grid profil Instagram memotong cover Reels ke 3:4, jadi isi penting cover diletakkan di pita tengah (± y 240–1680 pada 1920).

## 4. Bukti dan klaim

- Tampilkan keluaran produk yang sungguhan dan UI yang sungguhan. Penonton cepat mengenali mockup palsu.
- Brand di konten contoh harus fiktif; saring keluaran yang memuat nama, logo, atau kemasan merek nyata.
- Setiap angka (harga, jumlah, durasi) punya sumber di repo atau dari pemilik. Kalau harga bisa berubah, catat sumbernya di README agar diperbarui sebelum render ulang.
- Satu fitur per cut. Jangan menumpuk tiga klaim di satu layar.
- Hindari superlatif kosong ("terbaik", "revolusioner") dan kata "AI" di setiap adegan; tunjukkan hasilnya.

## 5. Sistem tipografi

- Satu keluarga display dengan 3–4 berat (300, 700, 800, 800 italic), satu keluarga UI (sama dengan produk, untuk screenshot dan ketikan), satu mono untuk angka/kode bila perlu.
- Skala pada 1080 × 1920: kata hero 150–180 px, judul 68–110 px, isi 32–40 px, caption 26–32 px.
- Display: tracking −0,035 em, line-height 0,98–1,05, maksimal dua baris per judul. Label kapital kecil: tracking 0,06–0,08 em.
- Satu kata aksen per judul (italic, gradien halus sesuai brand). Bukan setiap kata.
- Posisi judul bergantian antar adegan (kiri, kanan, tengah, tengah layar) dengan kontras ukuran dan berat. Margin samping ≥ 88 px.
- Zona aman Reels/TikTok: UI platform menutup ± 320–380 px bawah dan ± 140 px kanan. Teks dan tombol penting di atas y ≈ 1600 dan menjauh dari tepi kanan.

## 6. Warna dan latar

- Latar netral: charcoal tanpa rona biru, atau kertas hangat. Warna brand untuk satu elemen per adegan.
- Pelat foto (cyclorama studio, dinding plester, meja kayu) lebih meyakinkan daripada gradien CSS.
- Arah cahaya konsisten di seluruh video (mis. key dari kiri atas) supaya aset generatif dan foto terasa satu dunia.
- Layar penuh satu warna jenuh (mis. biru polos) terbaca slide presentasi; ganti dengan pelat foto atau produk.

## 7. Anti-slop beserta alasannya

| Pola | Kenapa ditolak | Ganti dengan |
|---|---|---|
| Gradien ungu/violet, glow neon | Bawaan generator AI, langsung terbaca "dibuat AI" | Palet brand + netral, cahaya studio |
| Sparkle, lens flare, partikel bintang | Dekorasi tanpa makna, murahan | Partikel nyata (kertas, debu) dengan kedalaman |
| Badge, pill, chip gaya web sebagai label | Bahasa UI web, bukan bahasa film | Caption editorial: nomor redup + teks |
| Garis tipis di antara label dan teks | Terbaca sebagai em dash/pola template | Spasi saja, atau "·" |
| Kartu glassmorphism, blob 3D melayang | Tren template, tidak ada di dunia nyata | Objek dengan material nyata |
| Layar biru polos | Terbaca slide | Pelat foto atau produk |
| Metafora yang tidak terjadi (bola kertas kusut untuk "bingung") | Penonton tidak mengenali masalahnya | Situasi nyata (meja kerja malam, profil 0 postingan) |
| Mockup HTML tiruan | Ukuran dan font selalu meleset | Screenshot asli + ketikan di atasnya |
| Emoji, bullet list di layar | Gaya presentasi | Satu kalimat per cut |
| Em dash di copy | Pola tulisan AI | Koma, titik, atau "·" |
| Semua judul seragam di kiri atas | Template | Hierarki yang berganti per adegan |

Yang **boleh** dari dunia web: tombol CTA bila memang tombol produk (mis. pil gelap "nama-domain.com →"), screenshot UI produk.

## 8. Bekerja dengan umpan balik pemilik

- Tunjukkan contact sheet still dan render draft sebelum render final; umpan balik visual lebih cepat daripada membaca kode.
- Catat setiap keputusan dan penolakan di README proyek ("ditolak: badge web, alasan …"). Iterasi berikutnya, oleh siapa pun, tidak boleh mengulanginya.
- Saat pemilik bilang "kurang suka", cari elemen spesifiknya; tawarkan satu rekomendasi tegas, bukan lima pilihan.
- Jangan hapus atau timpa render yang sudah dikirim. Arsipkan dengan tanggal dan label; varian baru mendapat nama baru.
- Perubahan selera kecil (volume, kecepatan) sering perlu dua putaran: setelah putaran pertama "sedikit", ukur dan buat perubahan berikutnya cukup besar untuk terdengar.
