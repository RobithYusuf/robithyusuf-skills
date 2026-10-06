---
name: creating-agent-skills
description: Membuat, memporting, merapikan, dan memvalidasi Agent Skills (folder berisi SKILL.md) sesuai spesifikasi terbuka agentskills.io sehingga bisa dipakai ulang di Claude Code, Codex, Cursor, dan agent lain. Gunakan saat pengguna ingin membuat skill baru, mengubah workflow atau prompt yang sering diulang menjadi skill, memasukkan skill lama ke repo skill, memperbaiki skill yang tidak ter-trigger, atau menyiapkan skill untuk dipublikasi. Cocok untuk permintaan seperti buat skill, bikin skill, skill baru, jadikan skill, port skill ini, SKILL.md, create a skill, skill tidak jalan.
license: MIT
metadata:
  author: robithyusuf
  version: "1.1.0"
---

# Membuat Agent Skill

Skill = folder berisi `SKILL.md` (frontmatter YAML + instruksi Markdown), opsional ditemani `scripts/`, `references/`, `assets/`. Agent hanya memuat `name` + `description` di awal; isi SKILL.md dimuat saat skill dipicu; file lain dibaca hanya bila perlu. Karena itu **description menentukan apakah skill dipakai**, dan **isi SKILL.md harus hemat konteks**.

## Alur kerja

Salin checklist ini dan centang selama bekerja:

```
- [ ] 0. Cari skill/guideline yang sudah ada; pakai atau pinjam yang terbaik
- [ ] 1. Pahami tujuan: apa yang dikerjakan, kapan dipicu, output seperti apa
- [ ] 2. Pilih nama (kebab-case, sama dengan nama folder)
- [ ] 3. Tulis description (apa + kapan + kata pemicu)
- [ ] 4. Tulis isi SKILL.md dari template
- [ ] 5. Pindahkan detail panjang ke references/, kode deterministik ke scripts/
- [ ] 6. Hapus data pribadi & kredensial; ganti dengan env var / placeholder
- [ ] 7. Jalankan validator sampai lolos
- [ ] 8. Uji dengan 2-3 prompt nyata, perbaiki berdasarkan perilaku agent
```

**Langkah 0 — jangan menulis ulang yang sudah ada.** Cari dulu: dokumentasi/AI guideline resmi vendor (mis. Laravel Boost, MCP resmi framework), `npx skills find <topik>` / [skills.sh](https://skills.sh), dan repo skill populer. Urutan pilihan:
- **REPLACE**: alternatif resmi atau terawat sudah mencakup kebutuhan → pasang itu saja, jangan duplikasi.
- **MERGE**: alternatif bagus tapi kurang konteks Anda → tulis skill ramping berisi selisihnya (konvensi, jebakan, keputusan Anda) dan rujuk/pinjam bagian terbaiknya.
- **KEEP**: belum ada yang setara → tulis sendiri.
Lebih lengkap tidak berarti lebih baik. Skill yang terlalu panjang memakan konteks, menenggelamkan aturan penting, dan bisa membuat agent kaku atau salah memilih langkah.

**Langkah 1.** Kalau skill berasal dari percakapan atau skill lama, ekstrak dulu: langkah yang diulang, koreksi yang pernah diberikan pengguna, format output, tool yang dipakai. Tanyakan hanya yang benar-benar tidak bisa disimpulkan.

**Langkah 2 — nama.** `a-z`, `0-9`, `-`; maks 64 karakter; tanpa `--`, tanpa `-` di awal/akhir; tidak memuat `claude`/`anthropic`. Utamakan bentuk aktivitas (`reviewing-code`, `deploying-to-vps`). Hindari nama samar (`helper`, `utils`).

**Langkah 3 — description** (maks 1024 karakter, orang ketiga, tanpa tag XML):

```
<Apa yang dilakukan, kata kerja konkret>. Gunakan saat <situasi/konteks>.
Cocok untuk permintaan seperti <frasa yang benar-benar diketik pengguna, campur ID/EN>.
```

Agent cenderung *kurang* memakai skill, jadi description boleh agak "mendorong" dan harus memuat kata kunci yang diketik pengguna. Jangan pakai `: ` atau ` #` di nilai YAML tanpa kutip, karena parser ketat akan gagal. Validator memeriksa ini.

**Langkah 4 — isi.** Mulai dari [assets/SKILL.template.md](assets/SKILL.template.md). Prinsip:
- Anggap agent sudah pintar; tulis hanya yang *tidak* ia ketahui (konvensi Anda, urutan langkah, jebakan, nama perintah persis).
- Jelaskan *alasan* di balik aturan, bukan sekadar HARUS/JANGAN huruf kapital.
- Sesuaikan kebebasan dengan risiko: tugas rapuh (migrasi, deploy) beri perintah persis; tugas terbuka (review, desain) beri heuristik.
- Satu istilah untuk satu konsep; beri satu default plus jalan keluar, bukan daftar lima pilihan.
- Hindari info yang cepat basi (tanggal, versi "terbaru").

**Langkah 5 — struktur.** Isi SKILL.md < 500 baris. Referensi cukup satu tingkat dari SKILL.md (jangan berantai). File referensi > 100 baris beri daftar isi. Tulis jelas apakah script **dijalankan** ("Jalankan `scripts/x.py`") atau **dibaca**. Script harus menangani error sendiri dan mencetak pesan yang bisa ditindaklanjuti. Pakai path relatif dengan `/`.

**Langkah 6 — keamanan.** Skill akan dipublikasi. Jangan tulis token, password, API key, cookie, URL berisi kredensial, IP server pribadi, atau email pribadi di file mana pun. Rujuk lewat env var (`$SERVICE_API_KEY`) dan dokumentasikan nama variabelnya di bagian "Persiapan". Pindai dengan skill `scanning-secrets` bila tersedia.

**Langkah 7 — validasi.**

```bash
python3 scripts/validate_skill.py <folder-skill>
```

Perbaiki semua `error`, lalu jalankan ulang sampai `[OK]`. `peringatan` boleh dibiarkan bila ada alasannya.

**Langkah 8 — uji.** Jalankan agent baru dengan skill terpasang pada 2-3 prompt realistis (termasuk satu yang *tidak* seharusnya memicu skill). Amati: apakah skill dipicu, file mana yang dibaca, langkah mana yang dilewati. Perbaiki description bila tidak terpicu, dan perbaiki isi bila agent salah langkah. Untuk uji terukur (eval dengan baseline, benchmark, optimasi description otomatis), pakai skill `skill-creator` dari [anthropics/skills](https://github.com/anthropics/skills) daripada membuat sistem eval sendiri.

## Menyesuaikan dengan model

Detail yang dibutuhkan tergantung model yang menjalankan skill:
- **Model besar** (kelas Opus/GPT-5): cukup tujuan, prinsip, keputusan penting, dan jebakan. Langkah yang terlalu rinci justru mengekang.
- **Model kecil/cepat** (kelas Haiku/mini, model lokal): butuh langkah eksplisit, perintah persis, contoh input→output, dan checklist.

Pola yang melayani keduanya: SKILL.md ramping (inti + keputusan), lalu detail langkah demi langkah di `references/` yang hanya dibaca bila perlu. Uji skill dengan model yang benar-benar dipakai; kalau model besar jadi kaku, pangkas; kalau model kecil tersesat, tambah langkah atau contoh.

## Memporting skill lama

1. Salin folder ke `skills/<nama>/`, samakan `name` dengan nama folder.
2. Pisahkan yang bersifat pribadi (path absolut `/Users/...`, nama server, ID proyek) menjadi parameter, env var, atau bagian "Sesuaikan".
3. Hapus artefak build (`__pycache__/`, `.pyc`, `node_modules/`).
4. Tambahkan `license` dan `metadata.author`/`metadata.version`.
5. Validasi dan pindai rahasia.

## Rujukan

- Spesifikasi lengkap, field opsional, pola progressive disclosure, dan anti-pattern: [references/panduan-penulisan.md](references/panduan-penulisan.md)
- Template siap pakai: [assets/SKILL.template.md](assets/SKILL.template.md)
