#!/usr/bin/env python3
"""Validasi folder Agent Skill terhadap spesifikasi agentskills.io.

Pemakaian:
    python3 validate_skill.py <folder-skill> [<folder-skill> ...]

Hanya memakai standard library, jadi bisa dijalankan di mana saja.
Exit code 0 jika semua valid, 1 jika ada error. Peringatan tidak menggagalkan.
"""
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX = 64          # batas spesifikasi
DESC_MAX = 1024        # batas spesifikasi
DESC_MIN_WARN = 60     # di bawah ini biasanya terlalu samar untuk memicu skill
COMPAT_MAX = 500       # batas spesifikasi
BODY_LINES_WARN = 500  # rekomendasi spesifikasi; pecah ke references/ bila lebih
RESERVED = ("anthropic", "claude")  # dilarang di `name` oleh platform Claude
KNOWN_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
XML_TAG = re.compile(r"<[a-zA-Z/][^>]*>")
MD_LINK = re.compile(r"\]\(([^)\s]+)\)")
YAML_RISKY_START = tuple("*&!%@`[{>|")


def unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        inner = value[1:-1]
        return inner.replace("''", "'") if value[0] == "'" else inner
    return value


def check_plain_scalar(key, value, lineno):
    """Tolak scalar YAML tanpa kutip yang akan gagal di parser YAML ketat."""
    if value[:1] in "'\"":
        return
    if value.startswith(YAML_RISKY_START):
        raise ValueError(f"baris {lineno}: nilai '{key}' diawali karakter khusus YAML; bungkus dengan kutip")
    if ": " in value or " #" in value:
        raise ValueError(f"baris {lineno}: nilai '{key}' mengandung ': ' atau ' #'; bungkus dengan kutip atau ubah kalimatnya")


def parse_frontmatter(text):
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md harus diawali frontmatter '---' di baris pertama")
    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError("frontmatter tidak ditutup dengan '---'")
    raw = text[4:end]
    body = text[end + 4:].lstrip("\n")
    data, current_map = {}, None
    for lineno, line in enumerate(raw.splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            if current_map is None:
                raise ValueError(f"baris {lineno}: indentasi tak terduga")
            key, sep, value = line.strip().partition(":")
            if not sep:
                raise ValueError(f"baris {lineno}: format 'key: value' tidak valid")
            value = value.strip()
            check_plain_scalar(key, value, lineno)
            data[current_map][key.strip()] = unquote(value)
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"baris {lineno}: format 'key: value' tidak valid")
        key, value = key.strip(), value.strip()
        if key in data:
            raise ValueError(f"baris {lineno}: field '{key}' ditulis dua kali")
        if value == "":
            data[key], current_map = {}, key
        elif value in (">", "|", ">-", "|-", ">+", "|+"):
            raise ValueError(f"baris {lineno}: block scalar untuk '{key}' tidak didukung validator ini; tulis dalam satu baris")
        else:
            check_plain_scalar(key, value, lineno)
            data[key], current_map = unquote(value), None
    return data, body


def validate(skill_dir):
    errors, warnings = [], []
    skill_dir = Path(skill_dir)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_md} tidak ditemukan"], warnings

    text = skill_md.read_text(encoding="utf-8")
    try:
        meta, body = parse_frontmatter(text)
    except ValueError as exc:
        return [str(exc)], warnings

    name = meta.get("name")
    if not isinstance(name, str) or not name:
        errors.append("field 'name' wajib diisi")
    else:
        if len(name) > NAME_MAX:
            errors.append(f"'name' {len(name)} karakter (maks {NAME_MAX})")
        if not NAME_RE.match(name):
            errors.append(f"'name' '{name}' hanya boleh huruf kecil, angka, dan satu tanda '-' di antaranya")
        if name != skill_dir.resolve().name:
            errors.append(f"'name' '{name}' harus sama dengan nama folder '{skill_dir.resolve().name}'")
        if any(word in name for word in RESERVED):
            errors.append(f"'name' tidak boleh memuat kata {RESERVED}")

    desc = meta.get("description")
    if not isinstance(desc, str) or not desc.strip():
        errors.append("field 'description' wajib diisi")
    else:
        if len(desc) > DESC_MAX:
            errors.append(f"'description' {len(desc)} karakter (maks {DESC_MAX})")
        if len(desc) < DESC_MIN_WARN:
            warnings.append("'description' sangat pendek; sebutkan apa yang dilakukan DAN kapan dipakai")
        if XML_TAG.search(desc):
            errors.append("'description' tidak boleh berisi tag XML/HTML")
        if re.match(r"(?i)^(i |i'm |saya |aku |you |kamu )", desc):
            warnings.append("'description' sebaiknya orang ketiga, bukan 'saya/kamu/I/you'")

    compat = meta.get("compatibility")
    if compat is not None and (not isinstance(compat, str) or not 1 <= len(compat) <= COMPAT_MAX):
        errors.append(f"'compatibility' harus teks 1-{COMPAT_MAX} karakter")

    metadata = meta.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        errors.append("'metadata' harus berupa map key: value")

    for key in meta:
        if key not in KNOWN_FIELDS:
            warnings.append(f"field '{key}' bukan bagian spesifikasi inti (mungkin khusus satu agent)")

    if not body.strip():
        errors.append("isi SKILL.md (setelah frontmatter) kosong")
    lines = body.count("\n") + 1
    if lines > BODY_LINES_WARN:
        warnings.append(f"isi SKILL.md {lines} baris; pindahkan detail ke references/ (target < {BODY_LINES_WARN})")

    for target in MD_LINK.findall(body):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        if "\\" in target:
            errors.append(f"path '{target}' memakai backslash; pakai '/'")
            continue
        if not (skill_dir / target.split("#")[0]).exists():
            errors.append(f"tautan ke '{target}' tidak ditemukan di dalam skill")

    return errors, warnings


def main(argv):
    if not argv:
        print((__doc__ or "").strip())
        return 2
    failed = False
    for arg in argv:
        errors, warnings = validate(arg)
        status = "GAGAL" if errors else "OK"
        print(f"[{status}] {arg}")
        for err in errors:
            print(f"   error: {err}")
        for warn in warnings:
            print(f"   peringatan: {warn}")
        failed = failed or bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
