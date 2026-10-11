#!/usr/bin/env python3
"""Tile stills into one labelled contact sheet for quick review (one image instead of twenty).

  python3 contact_sheet.py <dir | image ...> <out.jpg> [--cols 5] [--width 320]

Images are sorted by name (put the frame number in the file name, e.g. MyVideo_0236.jpg). Requires: pip install Pillow
"""
import argparse
import os
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("Butuh Pillow: pip install Pillow")

EXT = (".jpg", ".jpeg", ".png", ".webp")


def main():
    ap = argparse.ArgumentParser(description="Gabungkan still menjadi satu contact sheet.")
    ap.add_argument("inputs", nargs="+", help="folder atau berkas gambar, diakhiri path keluaran")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--width", type=int, default=320, help="lebar tiap tile (px)")
    args = ap.parse_args()
    if len(args.inputs) < 2:
        sys.exit("Pemakaian: contact_sheet.py <folder|gambar ...> <out.jpg>")
    *srcs, out = args.inputs

    files = []
    for s in srcs:
        if os.path.isdir(s):
            files += [os.path.join(s, f) for f in sorted(os.listdir(s)) if f.lower().endswith(EXT) and os.path.join(s, f) != out]
        elif os.path.isfile(s):
            files.append(s)
        else:
            print(f"dilewati, tidak ada: {s}", file=sys.stderr)
    if not files:
        sys.exit("Tidak ada gambar yang ditemukan.")

    first = Image.open(files[0])
    tw = args.width
    th = round(first.height * tw / first.width)
    label_h = 22
    cols = max(1, min(args.cols, len(files)))
    rows = (len(files) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + 6) + 6, rows * (th + label_h + 6) + 6), (24, 24, 26))
    draw = ImageDraw.Draw(sheet)
    for i, f in enumerate(files):
        x = 6 + (i % cols) * (tw + 6)
        y = 6 + (i // cols) * (th + label_h + 6)
        try:
            im = Image.open(f).convert("RGB").resize((tw, th))
        except OSError as exc:
            print(f"{f}: tidak bisa dibuka ({exc})", file=sys.stderr)
            continue
        sheet.paste(im, (x, y + label_h))
        draw.text((x + 2, y + 4), os.path.basename(f), fill=(220, 220, 220))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    sheet.save(out, quality=82)
    print(f"{out}  {len(files)} gambar, {cols} kolom")
    return 0


if __name__ == "__main__":
    sys.exit(main())
