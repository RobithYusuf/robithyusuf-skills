#!/usr/bin/env python3
"""Generate or edit an image through any OpenAI-compatible Images API (gpt-image-2 by default).

Credentials come only from the environment and are never printed:
  IMAGE_API_BASE_URL   base URL of the endpoint (include /v1 if the provider uses it)
  IMAGE_API_KEY        API key
  IMAGE_MODEL          optional, default gpt-image-2

Examples:
  python3 gen_image.py --prompt-file prompts/plane.txt --size 1536x1024 --chroma --n 3 --out public/gen/raw/plane.png
  python3 gen_image.py --edit mascot_2d.png --prompt-file prompts/mascot3d.txt --chroma --out public/gen/raw/mascot3d.png
  python3 gen_image.py --prompt "..." --size 1024x1536 --dry-run      # print the request, no API call

Requires: pip install openai   (Pillow only for --flatten)
Exit code 0 when every requested image was written, 1 otherwise.
"""
import argparse
import base64
import io
import math
import os
import sys
import time
import urllib.request

GREEN = (
    "Isolated on a perfectly flat, evenly lit, solid chroma-key green background (pure #00B140) that fills the whole "
    "frame edge to edge: no floor, no horizon, no gradient, no vignette, no shadow cast on the background, no green "
    "reflections on the object. No text, no logo, no watermark, no brand marks anywhere."
)
OPAQUE = "The background is solid and fully opaque (not transparent)."


def ratio_text(size):
    """Some gateways ignore `size`, so the aspect ratio also goes into the prompt text."""
    try:
        w, h = (int(v) for v in size.lower().split("x"))
    except ValueError:
        return ""
    g = math.gcd(w, h)
    shape = "vertical (portrait)" if h > w else "horizontal (landscape)" if w > h else "square"
    return f"Composition: {shape} frame, aspect ratio {w // g}:{h // g}."


def build_prompt(args):
    if args.prompt_file:
        try:
            text = open(args.prompt_file, encoding="utf-8").read().strip()
        except OSError as exc:
            sys.exit(f"Tidak bisa membaca --prompt-file: {exc}")
    else:
        text = (args.prompt or "").strip()
    if not text:
        sys.exit("Prompt kosong. Isi --prompt atau --prompt-file.")
    if text[-1] not in ".!?":
        text += "."
    parts = [text]
    if args.size != "auto" and not args.no_ratio_text:
        parts.append(ratio_text(args.size))
    if args.chroma:
        parts.append(GREEN)
    if args.opaque or args.chroma:
        parts.append(OPAQUE)
    return " ".join(p for p in parts if p)


def out_paths(out, n):
    root, ext = os.path.splitext(out)
    ext = ext or ".png"
    return [f"{root}{ext}" if i == 0 else f"{root}-{i + 1}{ext}" for i in range(n)]


def image_bytes(item, timeout):
    b64 = getattr(item, "b64_json", None)
    if b64:
        return base64.b64decode(b64)
    url = getattr(item, "url", None)
    if url:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 (URL comes from the API response)
            return resp.read()
    raise RuntimeError("respons tanpa b64_json maupun url")


def flatten(data, color):
    try:
        from PIL import Image
    except ImportError:
        sys.exit("--flatten butuh Pillow: pip install Pillow")
    im = Image.open(io.BytesIO(data))
    if im.mode not in ("RGBA", "LA", "P"):
        return data
    im = im.convert("RGBA")
    bg = Image.new("RGBA", im.size, color)
    bg.alpha_composite(im)
    buf = io.BytesIO()
    bg.convert("RGB").save(buf, "PNG")
    return buf.getvalue()


def call(client, args, model, prompt, attempts=4):
    delay = 8
    for i in range(attempts):
        try:
            if args.edit:
                files = [open(p, "rb") for p in args.edit]
                try:
                    return client.images.edit(model=model, image=files if len(files) > 1 else files[0], prompt=prompt, size=args.size, n=args.n)
                finally:
                    for fh in files:
                        fh.close()
            kwargs = dict(model=model, prompt=prompt, size=args.size, n=args.n)
            if args.quality:
                kwargs["quality"] = args.quality
            return client.images.generate(**kwargs)
        except Exception as exc:  # rate limits, timeouts and 5xx are common on image endpoints
            msg = str(exc).splitlines()[0][:200]
            if i == attempts - 1:
                raise
            print(f"percobaan {i + 1} gagal ({type(exc).__name__}: {msg}); ulang dalam {delay} dtk", file=sys.stderr)
            time.sleep(delay)
            delay *= 2


def main():
    ap = argparse.ArgumentParser(description="Generate/edit gambar lewat endpoint kompatibel OpenAI Images API.")
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--edit", nargs="+", help="gambar referensi/target edit (endpoint /images/edits)")
    ap.add_argument("--size", default="1024x1536", help="WIDTHxHEIGHT atau auto (gpt-image-2: kelipatan 16, maks 3840)")
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--quality", choices=["low", "medium", "high", "auto"])
    ap.add_argument("--out", required=False, default="output.png")
    ap.add_argument("--chroma", action="store_true", help="tambahkan kalimat latar chroma hijau #00B140")
    ap.add_argument("--opaque", action="store_true", help="tambahkan kalimat latar opaque")
    ap.add_argument("--no-ratio-text", action="store_true", help="jangan tulis rasio di teks prompt")
    ap.add_argument("--flatten", metavar="COLOR", help="ratakan PNG transparan ke warna ini, mis. '#00B140'")
    ap.add_argument("--timeout", type=float, default=300)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not 1 <= args.n <= 10:
        sys.exit("--n harus 1-10")
    for p in args.edit or []:
        if not os.path.isfile(p):
            sys.exit(f"Berkas --edit tidak ada: {p}")
    model = os.environ.get("IMAGE_MODEL", "gpt-image-2")
    prompt = build_prompt(args)
    outs = out_paths(args.out, args.n)

    if args.dry_run:
        print(f"model: {model}\nendpoint: {'images.edit' if args.edit else 'images.generate'}\nsize: {args.size}  n: {args.n}")
        print(f"edit: {args.edit or '-'}\nout: {', '.join(outs)}\nprompt:\n{prompt}")
        return 0

    base_url = os.environ.get("IMAGE_API_BASE_URL")
    api_key = os.environ.get("IMAGE_API_KEY")
    missing = [k for k, v in (("IMAGE_API_BASE_URL", base_url), ("IMAGE_API_KEY", api_key)) if not v]
    if missing:
        sys.exit(f"Env belum diset: {', '.join(missing)}. Set di shell/secret manager, jangan di berkas proyek.")
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("Butuh paket openai: pip install openai")

    client = OpenAI(base_url=base_url, api_key=api_key, timeout=args.timeout, max_retries=0)
    t0 = time.time()
    try:
        resp = call(client, args, model, prompt)
    except Exception as exc:
        sys.exit(f"Gagal setelah beberapa percobaan: {type(exc).__name__}: {str(exc).splitlines()[0][:300]}")

    written = 0
    for item, path in zip(resp.data or [], outs):
        try:
            data = image_bytes(item, args.timeout)
            if args.flatten:
                data = flatten(data, args.flatten)
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(data)
            written += 1
            print(f"{path}  {len(data) // 1024} KB")
        except Exception as exc:
            print(f"{path}: gagal ditulis ({exc})", file=sys.stderr)
    print(f"{written}/{args.n} gambar, model {model}, {time.time() - t0:.0f} dtk")
    return 0 if written == args.n else 1


if __name__ == "__main__":
    sys.exit(main())
