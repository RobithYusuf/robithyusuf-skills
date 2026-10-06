# Panduan Penulisan Agent Skill

Ringkasan dari spesifikasi terbuka [agentskills.io/specification](https://agentskills.io/specification) dan
[panduan best practice Anthropic](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices).

## Daftar isi

- Struktur folder
- Field frontmatter
- Progressive disclosure
- Tingkat kebebasan
- Pola yang terbukti efektif
- Anti-pattern
- Skill dengan script
- Keamanan untuk repo publik
- Checklist sebelum publish

## Struktur folder

```
nama-skill/
├── SKILL.md      # wajib: frontmatter + instruksi
├── scripts/      # opsional: kode yang DIJALANKAN agent (output-nya saja yang masuk konteks)
├── references/   # opsional: dokumen yang DIBACA saat perlu
└── assets/       # opsional: template, gambar, data yang dipakai di output
```

## Field frontmatter

| Field | Wajib | Aturan |
|---|---|---|
| `name` | ya | 1-64 karakter, `a-z 0-9 -`, tidak diawali/diakhiri `-`, tanpa `--`, **sama dengan nama folder**. Platform Claude melarang kata `claude`/`anthropic`. |
| `description` | ya | 1-1024 karakter, tanpa tag XML. Apa yang dilakukan + kapan dipakai + kata kunci pemicu. Orang ketiga. |
| `license` | tidak | Nama lisensi pendek (`MIT`) atau nama file lisensi. |
| `compatibility` | tidak | ≤ 500 karakter. Hanya bila butuh lingkungan khusus ("Butuh gh, docker, akses internet"). |
| `metadata` | tidak | Map string → string (`author`, `version`). |
| `allowed-tools` | tidak | Eksperimental. Daftar tool pra-izin dipisah spasi (`Bash(git:*) Read`). |

Agent tertentu menambah field sendiri (mis. Claude Code: `disable-model-invocation`, `argument-hint`). Field itu boleh dipakai, tetapi agent lain akan mengabaikannya.

## Progressive disclosure

1. **Metadata** (~100 token): `name` + `description` selalu dimuat untuk semua skill.
2. **Instruksi** (< 5000 token disarankan): isi SKILL.md dimuat saat skill dipicu.
3. **Resource** (tanpa batas): file di `scripts/`, `references/`, `assets/` dimuat hanya bila perlu.

Pola organisasi:
- **Panduan + rujukan**: SKILL.md berisi quick start, lalu tautan "Untuk X lihat references/x.md".
- **Per domain**: `references/aws.md`, `references/gcp.md`. Agent hanya membaca yang relevan.
- **Detail bersyarat**: kasus umum di SKILL.md, kasus langka di file terpisah.

Rujukan cukup **satu tingkat** dari SKILL.md. Rantai A → B → C membuat agent hanya membaca sebagian (mis. `head -100`).

## Tingkat kebebasan

| Situasi | Bentuk instruksi |
|---|---|
| Banyak cara benar, tergantung konteks (review, desain) | Heuristik dan langkah umum |
| Ada pola pilihan, variasi boleh | Pseudocode / script berparameter |
| Rapuh, harus berurutan (migrasi DB, deploy) | Perintah persis, "jangan ubah flag" |

## Pola yang terbukti efektif

- **Checklist yang disalin agent** untuk alur multi-langkah, supaya tidak ada langkah terlewat.
- **Loop umpan balik**: jalankan validator → perbaiki → ulangi sampai lolos.
- **Plan → validasi → eksekusi** untuk operasi massal atau destruktif: agent menulis rencana ke file (`changes.json`), script memvalidasi, baru dieksekusi.
- **Template output**: ketat ("SELALU pakai struktur ini") bila format penting, longgar ("default yang masuk akal") bila perlu adaptasi.
- **Contoh input → output** bila kualitas bergantung pada gaya.
- **Workflow bersyarat**: "Membuat baru? → alur A. Mengedit? → alur B."

## Anti-pattern

- Menjelaskan hal yang sudah diketahui agent ("PDF adalah format dokumen…").
- Menawarkan banyak pilihan tanpa default.
- Description samar ("Membantu dengan dokumen").
- Info yang cepat basi ("sebelum Agustus pakai API lama"). Taruh di bagian "pola lama" bila perlu.
- Istilah berganti-ganti untuk konsep yang sama.
- Path Windows (`scripts\x.py`).
- "Voodoo constant": angka tanpa alasan di script.
- Mengasumsikan paket sudah terpasang tanpa menyebutkannya.
- Nama tool MCP tanpa prefix server. Tulis `NamaServer:nama_tool`.

## Skill dengan script

- **Selesaikan, jangan lempar**: script menangani error (file tidak ada, izin, input salah) dan mencetak pesan yang bisa ditindaklanjuti.
- Utamakan standard library. Bila butuh paket, sebutkan perintah instalnya di SKILL.md.
- Pesan error spesifik: "Field 'tanggal' tidak ada. Field tersedia: nama, total".
- Exit code bermakna (0 sukses, ≠0 gagal) supaya bisa dipakai di hook/CI.

## Keamanan untuk repo publik

- Kredensial **selalu** lewat env var atau secret manager. Skill hanya menyebut *nama* variabelnya.
- Jangan commit `.env`, kunci privat, `credentials.json`, cookie/session export, file HAR, atau log yang berisi header Authorization.
- Samarkan data pribadi: path `/Users/<nama>`, IP/hostname server, ID proyek, email.
- Skill tidak boleh mengejutkan: perilakunya harus sesuai dengan yang tertulis di description (tanpa eksfiltrasi data atau perintah tersembunyi).
- Bila kredensial sempat ter-push: **rotasi dulu**, baru bersihkan riwayat. Menghapus commit tidak membuat token yang sudah bocor kembali aman.

## Checklist sebelum publish

- [ ] Description spesifik: apa + kapan + kata pemicu
- [ ] Isi SKILL.md < 500 baris; detail ada di references/
- [ ] Rujukan satu tingkat; file panjang punya daftar isi
- [ ] Contoh konkret, istilah konsisten, tidak ada info yang cepat basi
- [ ] Script menangani error, dependensi disebutkan, path pakai `/`
- [ ] Langkah verifikasi ada untuk operasi kritis
- [ ] Tidak ada kredensial atau data pribadi (lolos pemindaian)
- [ ] Lolos `validate_skill.py`
- [ ] Diuji pada ≥ 3 prompt nyata (termasuk yang tidak boleh memicu)
