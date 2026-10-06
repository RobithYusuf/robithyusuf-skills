#!/usr/bin/env python3
"""Pindai file atau riwayat git untuk kredensial yang bocor. Hanya standard library.

Pemakaian:
    python3 scan_secrets.py [path ...]   # pindai folder/file (default: .)
    python3 scan_secrets.py --staged     # hanya isi yang sudah di-stage (git add)
    python3 scan_secrets.py --history    # seluruh riwayat git semua branch

Exit code: 0 bersih, 1 ada temuan, 2 salah pemakaian.

Pengecualian:
  - Tambahkan komentar `secret-scan: allow` di baris yang memang aman (contoh/dummy).
  - Tulis pola glob path per baris di `.secretscanignore` pada root yang dipindai.
Nilai rahasia selalu disamarkan di output agar log tidak ikut membocorkannya.
"""
import fnmatch
import math
import os
import re
import subprocess
import sys
from pathlib import Path

MAX_FILE_BYTES = 2_000_000  # file lebih besar hampir pasti data/bundle, bukan konfigurasi
MIN_ENTROPY = 3.5           # nilai acak (token) biasanya > 3.5 bit/karakter; kata biasa < 3
ALLOW_MARK = "secret-scan: allow"
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", ".turbo", "vendor"}

PATTERNS = [
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{50,}\b")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI API key", re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("Stripe live key", re.compile(r"\b[sr]k_live_[0-9A-Za-z]{20,}")),
    ("Telegram bot token", re.compile(r"\b\d{8,10}:AA[A-Za-z0-9_-]{33}\b")),
    ("Private key", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY(?: BLOCK)?-----")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("URL berisi password", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@'\"]+:([^\s@/'\"]{6,})@[^\s'\"]+")),
]

GENERIC_ASSIGN = re.compile(
    r"(?i)\b[\w.-]*(?:api[_-]?key|secret|token|passw(?:or)?d|pwd|access[_-]?key|private[_-]?key|client[_-]?secret|auth[_-]?key)[\w.-]*"
    r"[\"']?\s*(?::|=|=>)\s*[\"']?([^\s\"'`,;)}]{12,})"
)
PLACEHOLDER = re.compile(
    r"(?i)(x{4,}|\*{3,}|your[_-]|example|sample|dummy|changeme|placeholder|redacted|replace|<[^>]*>|\$\{|\{\{|"
    r"process\.env|os\.environ|getenv|env\(|secrets\.|vars\.|\.\.\.|…|^(?:password|passwd|pass|secret|pwd|token)$)"
)

SENSITIVE_NAMES = ["id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", ".netrc", ".pgpass", "credentials.json",
                   "service-account*.json", "*.pem", "*.key", "*.p12", "*.pfx", "*.keystore", "*.jks", ".env", ".env.*"]
SAFE_NAMES = [".env.example", ".env.sample", ".env.template", "*.pub"]


def entropy(value):
    counts = {ch: value.count(ch) for ch in set(value)}
    return -sum(c / len(value) * math.log2(c / len(value)) for c in counts.values())


def mask(value):
    return f"{value[:4]}…({len(value)} karakter)" if len(value) > 8 else "…"


def scan_text(text):
    """Kembalikan daftar (nomor_baris, jenis, nilai_tersamar)."""
    findings = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARK in line:
            continue
        hit = False
        for label, pattern in PATTERNS:
            match = pattern.search(line)
            # Cek placeholder hanya pada bagian rahasia, bukan host/konteks di sekitarnya.
            value = match.group(match.lastindex or 0) if match else ""
            if match and not PLACEHOLDER.search(value):
                findings.append((lineno, label, mask(value)))
                hit = True
                break
        if hit:
            continue
        match = GENERIC_ASSIGN.search(line)
        if match:
            value = match.group(1)
            if not PLACEHOLDER.search(value) and entropy(value) >= MIN_ENTROPY:
                findings.append((lineno, "Nilai rahasia generik", mask(value)))
    return findings


def name_findings(path):
    name = os.path.basename(path)
    if any(fnmatch.fnmatch(name, pat) for pat in SAFE_NAMES):
        return []
    if any(fnmatch.fnmatch(name, pat) for pat in SENSITIVE_NAMES):
        return [(0, "Nama file sensitif (jangan di-commit)", name)]
    return []


def load_ignore(root):
    ignore_file = Path(root) / ".secretscanignore"
    if not ignore_file.is_file():
        return []
    lines = ignore_file.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]


def ignored(rel_path, patterns):
    return any(fnmatch.fnmatch(rel_path, pat) for pat in patterns)


def decode(data):
    if b"\0" in data[:8192]:
        return None  # file biner
    return data.decode("utf-8", errors="replace")


def scan_paths(paths):
    results = []
    for base in paths:
        base_path = Path(base)
        root = base_path if base_path.is_dir() else base_path.parent
        patterns = load_ignore(root)
        files = [base_path] if base_path.is_file() else (
            Path(dirpath) / f
            for dirpath, dirnames, filenames in os.walk(base_path)
            if not dirnames.__setitem__(slice(None), [d for d in dirnames if d not in SKIP_DIRS])
            for f in filenames
        )
        for file_path in files:
            rel = os.path.relpath(file_path, root)
            if ignored(rel, patterns):
                continue
            results += [(rel, *f) for f in name_findings(rel)]
            try:
                if file_path.stat().st_size > MAX_FILE_BYTES:
                    continue
                text = decode(file_path.read_bytes())
            except OSError:
                continue
            if text is not None:
                results += [(rel, *f) for f in scan_text(text)]
    return results


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, check=True).stdout


def scan_staged():
    root = git("rev-parse", "--show-toplevel").decode().strip()
    patterns = load_ignore(root)
    names = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").decode().split("\0")
    results = []
    for rel in filter(None, names):
        if ignored(rel, patterns):
            continue
        results += [(rel, *f) for f in name_findings(rel)]
        text = decode(git("show", f":{rel}"))
        if text is not None:
            results += [(rel, *f) for f in scan_text(text)]
    return results


def scan_history():
    """Pindai setiap baris yang pernah DITAMBAHKAN di commit mana pun."""
    log = git("log", "-p", "--all", "--no-color", "--unified=0", "--format=commit %h").decode("utf-8", "replace")
    results, commit, current = [], "?", "?"
    for line in log.splitlines():
        if line.startswith("commit "):
            commit = line.split()[1]
        elif line.startswith("+++ b/"):
            current = line[6:]
            results += [(f"{commit}:{current}", *f) for f in name_findings(current)]
        elif line.startswith("+") and not line.startswith("+++"):
            results += [(f"{commit}:{current}", 0, label, val) for _, label, val in scan_text(line[1:])]
    return results


def main(argv):
    if argv and argv[0] in ("-h", "--help"):
        print((__doc__ or "").strip())
        return 0
    try:
        if argv == ["--staged"]:
            results = scan_staged()
        elif argv == ["--history"]:
            results = scan_history()
        elif any(a.startswith("--") for a in argv):
            print((__doc__ or "").strip())
            return 2
        else:
            results = scan_paths(argv or ["."])
    except subprocess.CalledProcessError as exc:
        print(f"git gagal: {exc.stderr.decode().strip()}", file=sys.stderr)
        return 2

    if not results:
        print("Bersih: tidak ada kredensial yang terdeteksi.")
        return 0
    print(f"DITEMUKAN {len(results)} kemungkinan kredensial:\n")
    for location, lineno, label, value in results:
        where = f"{location}:{lineno}" if lineno else location
        print(f"  {where}  [{label}]  {value}")
    print("\nPindahkan nilai ke environment variable / secret manager. Jika sudah pernah ter-push, ROTASI kredensialnya.")
    print(f"Jika ini false positive, tambahkan komentar '{ALLOW_MARK}' di baris tersebut.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
