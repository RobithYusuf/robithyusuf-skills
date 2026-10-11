#!/usr/bin/env python3
"""How loud is each sound effect against the music under it? (ITU-R BS.1770 momentary loudness, 400 ms windows)

  python3 sfx_levels.py --music music.wav --sfx sfx_stem.wav --frames 102,229,338 [--fps 30]
  python3 sfx_levels.py --music music.wav --sfx sfx_stem.wav --at 3.4,7.6 --labels whoosh,flyby --limit -4

For every event it takes the loudest 400 ms window of the SFX stem that starts within --before/--after seconds of the
event (default -0.2..+0.4 s), then measures the music alone and the mix in that same window:
  sfx-mus  SFX loudness minus music loudness (LU). Transitions sit well at about -4 LU or lower.
  poke     how much the event raises the mix above the music alone (dB). Above ~1.5 dB it sticks out.
Render the SFX stem without music (e.g. Remotion --codec=wav --props '{"music":false}'). Other SFX inside the window are
measured together with the event (a hit right after a whoosh); shorten --after or render a stem with only that category
when that happens. --music-gain applies the music volume the composition uses. Exit code 1 when any event is above --limit.

Requires: pip install numpy scipy soundfile
"""
import argparse
import math
import sys

try:
    import numpy as np
    import scipy.signal as ss
    import soundfile as sf
except ImportError:
    sys.exit("Butuh numpy, scipy, soundfile: pip install numpy scipy soundfile")


def k_filter(fs):
    """BS.1770 K-weighting (pre-filter shelf + RLB high-pass) designed for any sample rate."""
    db, q, fc = 3.999843853973347, 0.7071752369554196, 1681.974450955533
    k = math.tan(math.pi * fc / fs)
    vh = 10 ** (db / 20)
    vb = vh ** 0.4996667741545416
    a0 = 1 + k / q + k * k
    shelf_b = [(vh + vb * k / q + k * k) / a0, 2 * (k * k - vh) / a0, (vh - vb * k / q + k * k) / a0]
    shelf_a = [1.0, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0]
    q, fc = 0.5003270373238773, 38.13547087602444
    k = math.tan(math.pi * fc / fs)
    a0 = 1 + k / q + k * k
    hp_a = [1.0, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0]
    return (shelf_b, shelf_a), ([1.0, -2.0, 1.0], hp_a)


def momentary(x, fs, hop):
    (b1, a1), (b2, a2) = k_filter(fs)
    y = ss.lfilter(b2, a2, ss.lfilter(b1, a1, x, axis=0), axis=0)
    p = (y ** 2).sum(1)
    c = np.concatenate([[0.0], np.cumsum(p)])
    w = int(0.4 * fs)
    idx = np.arange(0, max(1, len(p) - w), hop)
    return -0.691 + 10 * np.log10((c[idx + w] - c[idx]) / w + 1e-12)


def load(path):
    try:
        x, fs = sf.read(path, always_2d=True, dtype="float64")
    except RuntimeError as exc:
        sys.exit(f"Tidak bisa membaca {path}: {exc}")
    return x, fs


def main():
    ap = argparse.ArgumentParser(description="Ukur level SFX per kejadian terhadap musik (BS.1770 momentary).")
    ap.add_argument("--music", required=True)
    ap.add_argument("--sfx", required=True, help="stem SFX tanpa musik")
    ap.add_argument("--frames", help="daftar frame kejadian, dipisah koma")
    ap.add_argument("--at", help="daftar detik kejadian, dipisah koma")
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--labels", help="label per kejadian, dipisah koma (opsional)")
    ap.add_argument("--music-gain", type=float, default=1.0, help="volume musik di komposisi, mis. 0.9")
    ap.add_argument("--limit", type=float, default=-4.0, help="batas sfx-mus dalam LU")
    ap.add_argument("--before", type=float, default=0.2, help="detik sebelum kejadian yang ikut dicari")
    ap.add_argument("--after", type=float, default=0.4, help="detik sesudah kejadian yang ikut dicari")
    args = ap.parse_args()

    if bool(args.frames) == bool(args.at):
        sys.exit("Isi salah satu: --frames atau --at")
    try:
        times = [int(v) / args.fps for v in args.frames.split(",")] if args.frames else [float(v) for v in args.at.split(",")]
    except ValueError:
        sys.exit("--frames/--at harus angka dipisah koma")
    labels = args.labels.split(",") if args.labels else [""] * len(times)
    if len(labels) != len(times):
        sys.exit(f"--labels berisi {len(labels)} item, kejadian {len(times)}")

    mus, fs = load(args.music)
    sfx, fs2 = load(args.sfx)
    if fs != fs2:
        sys.exit(f"Sample rate beda: musik {fs}, sfx {fs2}. Samakan dulu (ffmpeg -ar).")
    if mus.shape[1] != sfx.shape[1]:
        mus = np.repeat(mus[:, :1], sfx.shape[1], 1) if mus.shape[1] == 1 else mus[:, : sfx.shape[1]]
    n = min(len(mus), len(sfx))
    mus = mus[:n] * args.music_gain
    sfx = sfx[:n]
    hop = int(0.01 * fs)
    lm, ls, lx = momentary(mus, fs, hop), momentary(sfx, fs, hop), momentary(mus + sfx, fs, hop)

    print(f"{'detik':>7} {'label':12} {'sfx LUFS':>9} {'musik':>7} {'sfx-mus':>8} {'poke':>6}")
    over, diffs = 0, []
    for t, lab in zip(times, labels):
        i0, i1 = max(0, int((t - args.before) / 0.01)), min(len(ls), int((t + args.after) / 0.01) + 1)
        if i0 >= i1:
            print(f"{t:7.2f} {lab:12} di luar durasi audio")
            continue
        k = i0 + int(np.argmax(ls[i0:i1]))
        d, poke = ls[k] - lm[k], lx[k] - lm[k]
        diffs.append(d)
        flag = "  <-- menonjol" if d > args.limit else ""
        over += d > args.limit
        print(f"{t:7.2f} {lab:12} {ls[k]:9.1f} {lm[k]:7.1f} {d:+8.1f} {poke:+6.1f}{flag}")
    if diffs:
        print(f"median sfx-mus {np.median(diffs):+.1f} LU, maks {max(diffs):+.1f} LU; {over} kejadian di atas {args.limit:+.0f} LU")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
