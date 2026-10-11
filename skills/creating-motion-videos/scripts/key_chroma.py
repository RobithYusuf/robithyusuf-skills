#!/usr/bin/env python3
"""Chroma-key green-screen renders into clean transparent PNGs.

  python3 key_chroma.py <image> [<image> ...] --out <dir> [--crop] [--hole] [--split MIN_AREA] [--solid 200]

  --crop        crop to the object's bounding box (+ small padding)
  --hole        find the enclosed keyed area (a device screen) and write <name>.hole.json with its box and corner radius,
                so content can be placed exactly behind the bezel. The outer background is told apart by touching the
                image border.
  --split N     write every separate object of at least N pixels as <name>_<i>.png plus <name>.pieces.json (paper scraps,
                leaves, particles generated together on one green sheet)
  --solid N     alpha >= N becomes fully opaque (cleans semi-transparent interiors from dirty masks)
  --t0/--t1     soft-key thresholds on green dominance g - max(r, b); raise t0 if green tints survive at the edges

Requires: pip install numpy Pillow  (and scipy for --hole/--split)
"""
import argparse
import json
import os
import sys

try:
    import numpy as np
    from PIL import Image, ImageFilter
except ImportError:
    sys.exit("Butuh numpy dan Pillow: pip install numpy Pillow")


def key(path, t0, t1, channel):
    im = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    key_c, o1, o2 = (g, r, b) if channel == "g" else (b, r, g)
    excess = key_c - np.maximum(o1, o2)  # how "screen coloured" a pixel is
    a = 1.0 - np.clip((excess - t0) / (t1 - t0), 0, 1)
    # despill: the key channel may never exceed the other two on kept pixels
    clean = np.minimum(key_c, np.maximum(o1, o2) + 4)
    rgb = np.stack([r, clean, b], -1) if channel == "g" else np.stack([r, g, clean], -1)
    alpha = Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.MedianFilter(3))  # edge speckles
    return np.dstack([rgb.astype(np.uint8), np.asarray(alpha)])


def bbox(mask, pad, shape):
    ys, xs = np.where(mask)
    if not len(ys):
        return None
    h, w = shape
    return max(0, ys.min() - pad), min(h - 1, ys.max() + pad), max(0, xs.min() - pad), min(w - 1, xs.max() + pad)


def need_scipy():
    try:
        from scipy import ndimage  # noqa: F401
        return ndimage
    except ImportError:
        sys.exit("--hole/--split butuh scipy: pip install scipy")


def main():
    ap = argparse.ArgumentParser(description="Key latar chroma menjadi PNG beralfa.")
    ap.add_argument("images", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--channel", choices=["g", "b"], default="g", help="g = layar hijau (default), b = layar biru")
    ap.add_argument("--t0", type=float, default=18.0)
    ap.add_argument("--t1", type=float, default=64.0)
    ap.add_argument("--crop", action="store_true")
    ap.add_argument("--hole", action="store_true")
    ap.add_argument("--split", type=int, metavar="MIN_AREA")
    ap.add_argument("--solid", type=int, metavar="ALPHA")
    args = ap.parse_args()
    if args.t1 <= args.t0:
        sys.exit("--t1 harus lebih besar dari --t0")
    os.makedirs(args.out, exist_ok=True)
    failed = 0

    for path in args.images:
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            rgba = key(path, args.t0, args.t1, args.channel)
        except (OSError, ValueError) as exc:
            print(f"{path}: tidak bisa dibuka ({exc})", file=sys.stderr)
            failed += 1
            continue
        if args.solid:
            rgba[..., 3] = np.where(rgba[..., 3] >= args.solid, 255, rgba[..., 3])
        alpha = rgba[..., 3]
        if (alpha > 8).mean() > 0.995:
            print(f"{path}: hampir tidak ada piksel ter-key; latarnya bukan layar {args.channel}?", file=sys.stderr)

        if args.split:
            nd = need_scipy()
            labels, n = nd.label(alpha > 8)
            pieces = []
            for i, sl in enumerate(nd.find_objects(labels), start=1):
                if sl is None:
                    continue
                area = int((labels[sl] == i).sum())
                if area < args.split:
                    continue
                piece = rgba[sl].copy()
                piece[..., 3] = np.where(labels[sl] == i, piece[..., 3], 0)
                fn = f"{name}_{len(pieces)}.png"
                Image.fromarray(piece).save(os.path.join(args.out, fn))
                pieces.append({"file": fn, "w": piece.shape[1], "h": piece.shape[0], "area": area})
            with open(os.path.join(args.out, f"{name}.pieces.json"), "w") as fh:
                json.dump(pieces, fh, indent=1)
            print(f"{name}: {len(pieces)} potongan (≥ {args.split} px)")
            continue

        info = {}
        x0 = y0 = 0
        if args.hole:
            nd = need_scipy()
            transparent = alpha < 128
            labels, _ = nd.label(transparent)
            border = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))) - {0}
            outer = np.isin(labels, list(border))
            holes = transparent & ~outer
            if holes.any():
                hl, _ = nd.label(holes)
                biggest = np.argmax(np.bincount(hl.ravel())[1:]) + 1
                hole = hl == biggest
            else:
                hole = None
                print(f"{name}: tidak ada area tertutup (layar) yang ditemukan", file=sys.stderr)
            body = bbox(~outer, 0, alpha.shape)
            if body:
                y0, y1, x0, x1 = body
                rgba = rgba[y0:y1 + 1, x0:x1 + 1]
            if hole is not None:
                ys, xs = np.where(hole)
                top = ys.min()
                info = {
                    "width": int(rgba.shape[1]),
                    "height": int(rgba.shape[0]),
                    "screen": {
                        "x": int(xs.min() - x0),
                        "y": int(ys.min() - y0),
                        "w": int(xs.max() - xs.min() + 1),
                        "h": int(ys.max() - ys.min() + 1),
                        "radius": int(xs[ys == top].min() - xs.min()),
                    },
                }
                with open(os.path.join(args.out, f"{name}.hole.json"), "w") as fh:
                    json.dump(info, fh, indent=1)
        elif args.crop:
            box = bbox(alpha > 8, 6, alpha.shape)
            if box:
                y0, y1, x0, x1 = box
                rgba = rgba[y0:y1 + 1, x0:x1 + 1]

        out = os.path.join(args.out, f"{name}.png")
        Image.fromarray(rgba).save(out)
        print(f"{out}  {rgba.shape[1]}x{rgba.shape[0]}" + (f"  layar {info['screen']}" if info else ""))

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
