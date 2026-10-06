#!/usr/bin/env python3
"""Audit page object Inertia (props) yang ikut terkirim di HTML awal.

Pemakaian:
    python3 audit_page_props.py https://example.com/
    python3 audit_page_props.py halaman.html          # HTML yang sudah disimpan
    curl -s https://example.com/ | python3 audit_page_props.py -

Opsi:
    --cookie-env NAMA   ambil header Cookie dari env var NAMA (untuk halaman yang butuh login)
    --wide N            tandai objek dengan >= N field sebagai kemungkinan "full model" (default 15)

Hanya standard library. Exit code: 0 = tidak ada temuan, 1 = ada field mencurigakan, 2 = error.
"""
import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request

ATTR_RE = re.compile(r"""data-page\s*=\s*(["'])(.*?)\1""", re.S)
SCRIPT_RE = re.compile(r"<script[^>]*data-page[^>]*>(.*?)</script>", re.S | re.I)
# Nama field yang hampir tidak pernah perlu dikirim ke browser. Sesuaikan per proyek.
SENSITIVE_RE = re.compile(
    r"(password|remember_token|secret|api_?key|private|token|two_factor|otp|salt|hash"
    r"|cost_price|margin|profit|admin_note|internal|deleted_at|ip_address|payment_reference)",
    re.I,
)


def load(source, cookie_env):
    if source == "-":
        return sys.stdin.read()
    if re.match(r"https?://", source):
        headers = {"User-Agent": "inertia-props-audit"}
        if cookie_env:
            cookie = os.environ.get(cookie_env)
            if not cookie:
                raise SystemExit(f"env var {cookie_env} kosong; export dulu nilai header Cookie")
            headers["Cookie"] = cookie
        req = urllib.request.Request(source, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", "replace")
        except urllib.error.URLError as exc:
            raise SystemExit(f"gagal mengambil {source}: {exc}")
    try:
        with open(source, encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        raise SystemExit(f"gagal membaca {source}: {exc}")


def extract_page(text):
    # Page object bisa ada di atribut data-page (klasik) atau di <script data-page ...> (JSON).
    candidates = [m.group(1).strip() for m in SCRIPT_RE.finditer(text)]
    candidates += [html.unescape(m.group(2)) for m in ATTR_RE.finditer(text)]
    for raw in candidates:
        try:
            page = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(page, dict) and "component" in page:
            return page
    raise SystemExit("page object Inertia tidak ditemukan (bukan halaman Inertia, atau butuh login?)")


def walk(node, path, wide, flagged, wide_objs):
    if isinstance(node, dict):
        if len(node) >= wide:
            wide_objs.setdefault(path or "(root)", len(node))
        for key, value in node.items():
            child = f"{path}.{key}" if path else key
            if SENSITIVE_RE.search(key):
                flagged.add(child)
            walk(value, child, wide, flagged, wide_objs)
    elif isinstance(node, list):
        for item in node:
            walk(item, f"{path}[]", wide, flagged, wide_objs)


def size(value):
    return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Audit props Inertia di HTML awal")
    parser.add_argument("source", help="URL, path file HTML, atau '-' untuk stdin")
    parser.add_argument("--cookie-env", help="nama env var berisi header Cookie")
    parser.add_argument("--wide", type=int, default=15, help="ambang jumlah field per objek")
    args = parser.parse_args()

    page = extract_page(load(args.source, args.cookie_env))
    props = page.get("props", {})
    print(f"component : {page.get('component')}")
    print(f"url       : {page.get('url')}")
    print(f"total     : {size(page) / 1024:.1f} KB\n")
    print("Ukuran per prop (terbesar dulu):")
    for key, value in sorted(props.items(), key=lambda kv: -size(kv[1])):
        print(f"  {size(value) / 1024:7.1f} KB  {key}")

    flagged, wide_objs = set(), {}
    walk(props, "", args.wide, flagged, wide_objs)
    if wide_objs:
        print(f"\nObjek dengan >= {args.wide} field (kemungkinan model dikirim utuh):")
        for path, count in sorted(wide_objs.items()):
            print(f"  {count:3d} field  {path}")
    if flagged:
        print("\nField dengan nama mencurigakan (cek apakah benar dipakai UI):")
        for path in sorted(flagged):
            print(f"  {path}")
        return 1
    print("\nTidak ada nama field mencurigakan. Tetap tinjau daftar di atas secara manual.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as exc:
        if isinstance(exc.code, str):
            print(f"error: {exc.code}", file=sys.stderr)
            sys.exit(2)
        raise
