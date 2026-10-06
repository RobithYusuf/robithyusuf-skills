---
name: writing-agents-md
description: Menulis atau merapikan AGENTS.md (dan CLAUDE.md pendampingnya) untuk sebuah repo dengan format Agent Guide, yaitu peta repo, hard constraints, working defaults, bahasa dan penamaan, invarian arsitektur, dokumentasi on-demand, verifikasi, dan aturan memelihara guide. Isinya diambil dari kode dan perintah yang benar-benar ada, bukan tebakan. Gunakan saat memulai proyek baru, saat agent berulang kali melakukan kesalahan yang sama di sebuah repo, saat AGENTS.md atau CLAUDE.md sudah terlalu panjang atau usang, atau saat pengguna meminta buat AGENTS.md, bikin CLAUDE.md, agent guide, aturan proyek untuk agent, rapikan instruksi agent.
license: MIT
metadata:
  author: robithyusuf
  version: "1.0.0"
---

# Menulis AGENTS.md

AGENTS.md dimuat di **setiap** sesi agent pada repo itu, jadi setiap baris memakan konteks. Tujuannya bukan mendokumentasikan semua hal. Tujuannya mencatat hal yang **tidak bisa ditebak dari kode** dan **mahal bila dilanggar**.

## Alur kerja

```
- [ ] 1. Survei repo
- [ ] 2. Kumpulkan invarian & koreksi berulang
- [ ] 3. Isi template
- [ ] 4. Verifikasi setiap perintah dan path
- [ ] 5. Pangkas
- [ ] 6. Pasang CLAUDE.md pendamping
```

**1. Survei repo.** Baca `README`, manifest (`package.json`, `pyproject.toml`, `composer.json`, `go.mod`), `docker-compose*.yml`, `Makefile`/scripts, CI workflow, struktur folder tingkat atas, dan `docs/`. Bila sudah ada AGENTS.md/CLAUDE.md lama, baca dulu dan pertahankan aturan yang masih berlaku.

**2. Kumpulkan isi.** Cari:
- Sumber kebenaran (folder mana yang asli, mana yang hasil generate).
- Arah dependensi antar layer dan tempat kode baru semestinya diletakkan.
- Hal yang wajib idempoten atau sinkron (pembayaran, kredit, dua storage).
- Perintah dev/test/check yang benar-benar dipakai.
- Koreksi yang sering diberikan pengguna di sesi sebelumnya. Inilah kandidat aturan terkuat.
Bila ada yang tidak bisa disimpulkan (misalnya siapa yang boleh deploy), tanyakan ke pengguna.

**3. Isi template.** Pakai [assets/AGENTS.template.md](assets/AGENTS.template.md). Bedakan dengan tegas:
- **Hard constraints**: pelanggaran mahal/tidak bisa dibatalkan (data, uang, deploy, secret). Selalu sertakan alternatif yang aman.
- **Working defaults**: kebiasaan baik yang boleh ditimpa oleh permintaan developer.
- **Architecture invariants**: fakta spesifik proyek beserta *alasannya*. Aturan tanpa alasan akan dilanggar di kasus tepi.

**4. Verifikasi.** Jalankan atau cek keberadaan setiap perintah dan path yang ditulis. Perintah yang salah di AGENTS.md lebih berbahaya daripada tidak ada, karena agent akan mempercayainya.

**5. Pangkas.** Target root AGENTS.md ≤ ~150 baris. Hapus:
- Hal yang sudah jelas dari kode atau sudah diketahui agent (cara kerja React, arti REST).
- Status sementara ("migrasi sedang berjalan", daftar TODO, tanggal). Pindahkan ke `docs/`.
- Aturan yang hanya berlaku di satu folder. Pindahkan ke `AGENTS.md` di folder itu (agent memuat yang terdekat).

**6. CLAUDE.md pendamping.** Supaya Claude Code dan agent lain memakai satu sumber, isi `CLAUDE.md` dengan satu baris:

```
@AGENTS.md
```

## Bahasa

Ikuti bahasa yang sudah dipakai repo. Default: guide ditulis dalam bahasa Inggris (identifier dan perintah memang Inggris), sedangkan aturan teks UI menyebut bahasa Indonesia sebagai bahasa untuk pengguna.

## Memperbarui guide yang sudah ada

Tambahkan aturan baru hanya bila ia mencatat invarian yang tidak jelas, mencegah kegagalan mahal, atau menjawab koreksi yang berulang. Saat mengedit, jangan menulis ulang seluruh file. Ubah bagian yang relevan dan laporkan diff singkatnya ke pengguna.
