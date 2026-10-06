# robithyusuf-skills

Kumpulan **Agent Skills** dan aturan agent buatan sendiri. Formatnya mengikuti spesifikasi terbuka [agentskills.io](https://agentskills.io/specification), jadi bisa dipakai di Claude Code, Codex, Cursor, Gemini CLI, Copilot, dan agent lain yang mendukung `SKILL.md`.

## Isi

**Meta & keamanan**

| Skill | Fungsi |
|---|---|
| [`creating-agent-skills`](skills/creating-agent-skills/SKILL.md) | Membuat, memporting, dan memvalidasi skill sesuai spesifikasi |
| [`scanning-secrets`](skills/scanning-secrets/SKILL.md) | Memindai kredensial bocor di file, staging, atau riwayat git |
| [`writing-agents-md`](skills/writing-agents-md/SKILL.md) | Menulis AGENTS.md proyek dengan format Agent Guide |
| [`auditing-security-baseline`](skills/auditing-security-baseline/SKILL.md) | Audit keamanan lintas stack dengan temuan berbukti dan tingkat keparahan |

**Laravel + Inertia**

| Skill | Fungsi |
|---|---|
| [`securing-inertia-apps`](skills/securing-inertia-apps/SKILL.md) | Mencegah kebocoran props `data-page` dan memisahkan bundle admin/publik |
| [`migrating-inertia-to-typescript`](skills/migrating-inertia-to-typescript/SKILL.md) | Migrasi bertahap JS → TS untuk Svelte/React/Vue |
| [`setting-up-laravel-wayfinder`](skills/setting-up-laravel-wayfinder/SKILL.md) | Memasang Wayfinder dan migrasi dari Ziggy, termasuk build Docker/CI |
| [`deploying-laravel-inertia-docker`](skills/deploying-laravel-inertia-docker/SKILL.md) | Docker dev + production dengan SSR, beserta template siap salin |

**Frontend**

| Skill | Fungsi |
|---|---|
| [`fixing-svelte5-warnings`](skills/fixing-svelte5-warnings/SKILL.md) | Memperbaiki warning compiler Svelte 5 dari akar masalahnya |
| [`optimizing-web-performance`](skills/optimizing-web-performance/SKILL.md) | Metode ukur → diagnosis → perbaiki → verifikasi untuk performa web |

| Aturan | Fungsi |
|---|---|
| [`rules/AGENTS.global.md`](rules/AGENTS.global.md) | Aturan global: gaya, kata kunci, cara kerja, format laporan |

## Pasang

Lewat [skills CLI](https://skills.sh):

```bash
npx skills add RobithYusuf/robithyusuf-skills            # pilih skill secara interaktif
npx skills add RobithYusuf/robithyusuf-skills -s scanning-secrets -g   # satu skill, global
```

Atau clone lalu symlink. Cara ini cocok saat skill sedang dikembangkan, karena perubahan langsung terpakai:

```bash
git clone https://github.com/RobithYusuf/robithyusuf-skills.git
cd robithyusuf-skills
sh scripts/install-local.sh                  # ke ~/.claude/skills
sh scripts/install-local.sh ~/.codex/skills  # ke agent lain
```

Cara memasang aturan global ada di [rules/README.md](rules/README.md).

## Menambah skill

```bash
git config core.hooksPath .githooks   # sekali per clone: aktifkan cek otomatis
sh scripts/new-skill.sh nama-skill    # buat dari template
# isi skills/nama-skill/SKILL.md
sh scripts/check.sh                   # validasi + pindai kredensial
```

Struktur satu skill:

```
skills/nama-skill/
├── SKILL.md       # wajib: frontmatter (name, description) + instruksi
├── scripts/       # opsional: kode yang dijalankan agent
├── references/    # opsional: dokumen yang dibaca saat perlu
└── assets/        # opsional: template, data
```

Sebelum menulis skill baru, cek dulu skill resmi atau populer untuk topik itu (Laravel Boost, sveltejs/ai-tools, anthropics/skills, dll.). Skill di repo ini hanya mengisi hal yang belum dicakup, dan sengaja dibuat ramping karena skill yang terlalu lengkap bisa membuat agent kaku. Lihat langkah 0 di panduan.

Aturan penulisannya ada di [panduan penulisan](skills/creating-agent-skills/references/panduan-penulisan.md). Ringkasnya:
- `name` sama dengan nama folder, huruf kecil dan `-`, maksimal 64 karakter.
- `description` menjelaskan **apa** yang dilakukan **dan kapan** dipakai, plus kata pemicu (maksimal 1024 karakter).
- Isi `SKILL.md` di bawah 500 baris; detail dipindah ke `references/`.

## Keamanan

Repo ini publik. Lapisan pengamannya:

1. **`.gitignore`** menolak `.env`, kunci privat, `credentials*.json`, cookie, file HAR, dan catatan `*.local.md`.
2. **Pre-commit hook** memindai perubahan yang di-stage; **pre-push hook** memindai seluruh riwayat.
3. **CI** menjalankan validator, pemindai riwayat, dan [gitleaks](https://github.com/gitleaks/gitleaks) di setiap push.
4. **GitHub secret scanning + push protection** aktif di repo.

Skill tidak boleh memuat nilai kredensial. Rujuk lewat environment variable (`$NAMA_API_KEY`) dan sebutkan namanya di bagian "Persiapan" skill. Bila kredensial sempat ter-push, **rotasi dulu**, baru bersihkan riwayat.

## Lisensi

[MIT](LICENSE)
