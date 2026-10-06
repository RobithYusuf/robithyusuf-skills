---
name: scanning-secrets
description: Memindai file, perubahan yang di-stage, atau seluruh riwayat git untuk kredensial yang bocor (API key, token GitHub/OpenAI/Anthropic/AWS/Stripe/Slack, kunci privat, JWT, password di URL, file .env) lalu memandu perbaikan dan rotasi. Gunakan sebelum commit, sebelum push, sebelum menjadikan repo publik, saat membagikan kode/skill/config, atau saat pengguna khawatir ada rahasia yang terekspos. Cocok untuk permintaan seperti cek kredensial, scan secret, ada token bocor, aman di-push, aman dipublikasi, check for leaked keys.
license: MIT
metadata:
  author: robithyusuf
  version: "1.1.0"
---

# Memindai Kredensial Bocor

Tujuannya: tidak ada rahasia yang keluar dari mesin pengguna. Pemindaian murah, sedangkan token yang bocor ke repo publik biasanya dipanen bot dalam hitungan menit.

## Alur kerja

```
- [ ] 1. Pindai (pilih mode sesuai situasi)
- [ ] 2. Tinjau setiap temuan, pisahkan asli vs false positive
- [ ] 3. Perbaiki temuan asli
- [ ] 4. Bila pernah ter-push: rotasi, lalu bersihkan riwayat
- [ ] 5. Pindai ulang sampai bersih
```

**1. Pindai.** Script hanya butuh Python 3 (tanpa paket tambahan):

```bash
python3 scripts/scan_secrets.py .            # seluruh folder kerja
python3 scripts/scan_secrets.py --staged     # sebelum commit
python3 scripts/scan_secrets.py --history    # sebelum repo lama dijadikan publik
```

Bila `gitleaks` terpasang, jalankan juga sebagai lapisan kedua karena aturannya lebih banyak:
`gitleaks dir . --redact` dan `gitleaks git . --redact`.

Untuk mengetahui apakah key yang ditemukan **masih aktif**, `trufflehog git file://. --results=verified` mengujinya langsung ke API penyedia. Karena key ikut dikirim ke penyedianya, minta izin pengguna dulu.

Selain itu periksa hal yang tidak bisa ditangkap pola: path absolut berisi nama pengguna, IP/hostname server pribadi, email pribadi, ID proyek internal. Gunakan `grep -rnE '/Users/|/home/|[0-9]{1,3}(\.[0-9]{1,3}){3}' .`.

**2. Tinjau.** Output sudah menyamarkan nilai. Jangan pernah mencetak nilai rahasia lengkap ke chat atau log. Bila perlu melihat konteks, baca barisnya, lalu rujuk dengan `file:baris`.

**3. Perbaiki.**
- Ganti nilai dengan env var (`os.environ["NAMA_KEY"]`, `process.env.NAMA_KEY`) atau placeholder (`<isi-api-key>`).
- Tambahkan file sensitif ke `.gitignore`. Untuk `.env`, sediakan `.env.example` berisi nama variabel saja.
- File yang sudah di-stage: `git rm --cached <file>`.
- False positive (contoh/dummy): tambahkan komentar `secret-scan: allow` di baris itu, atau pola path di `.secretscanignore`.

**4. Sudah pernah ter-push / dibagikan?** Anggap rahasia itu **sudah bocor**.
1. Beri tahu pengguna dan minta mereka **merotasi/mencabut** kredensial di penyedianya. Ini langkah yang benar-benar menutup kebocoran.
2. Baru setelah itu tawarkan pembersihan riwayat (`git filter-repo --replace-text` atau BFG) plus force-push. Ini destruktif, jadi minta konfirmasi dulu.

**5. Pindai ulang** dengan mode yang sama sampai keluar `Bersih`.

## Mencegah ke depan

- Pre-commit hook: `python3 <path>/scan_secrets.py --staged` (exit 1 menggagalkan commit).
- CI: jalankan `--history` dan `gitleaks/gitleaks-action` di setiap push.
- Repo GitHub: aktifkan *secret scanning* dan *push protection*:
  `gh api -X PATCH repos/OWNER/REPO -f "security_and_analysis[secret_scanning][status]=enabled" -f "security_and_analysis[secret_scanning_push_protection][status]=enabled"`

## Batasan

Deteksi berbasis pola dan entropi tidak sempurna. Script ini bisa melewatkan format token yang belum dikenal, dan bisa salah tandai string acak. Hasil "bersih" artinya tidak ada pola yang dikenali, bukan jaminan mutlak, jadi tetap tinjau file yang asing sebelum publish.
