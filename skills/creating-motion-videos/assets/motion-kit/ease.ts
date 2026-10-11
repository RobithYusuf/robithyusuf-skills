import {Easing, interpolate} from 'remotion';

// Speed-graph curves (After Effects "easy ease" with strong influence), not CSS defaults.
// Rule of thumb: entrances E.out, exits and whips E.in, camera moves E.inOut, small UI pops E.back.
export const E = {
  out: Easing.bezier(0.16, 1, 0.3, 1), // fast start, long settle (entrances)
  outSoft: Easing.bezier(0.22, 0.9, 0.32, 1),
  in: Easing.bezier(0.7, 0, 0.84, 0), // slow start, fast end (exits, whips)
  inOut: Easing.bezier(0.83, 0, 0.17, 1), // camera moves, whip transitions
  inOutSoft: Easing.bezier(0.65, 0, 0.35, 1),
  back: Easing.bezier(0.34, 1.45, 0.64, 1), // tiny overshoot, small UI pops only
  linear: (t: number) => t,
};

export type Ease = (t: number) => number;

// Tween one value between two frames, clamped on both sides.
export const tw = (f: number, f0: number, f1: number, from: number, to: number, ease: Ease = E.out) =>
  interpolate(f, [f0, f1], [from, to], {easing: ease, extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

// Progress 0..1 between two frames.
export const pr = (f: number, f0: number, f1: number, ease: Ease = E.out) => tw(f, f0, f1, 0, 1, ease);

// Keyframes like an AE timeline: keys = [[frame, value, easeIntoThisKey?], ...]. Each segment has its own curve.
export const keys = (f: number, ks: Array<[number, number, Ease?]>) => {
  if (f <= ks[0][0]) return ks[0][1];
  for (let i = 1; i < ks.length; i++) {
    const [f1, v1, ease] = ks[i];
    const [f0, v0] = ks[i - 1];
    if (f <= f1) return tw(f, f0, f1, v0, v1, ease ?? E.inOutSoft);
  }
  return ks[ks.length - 1][1];
};

export const mix = (a: number, b: number, t: number) => a + (b - a) * t;

// Cubic bezier point, for motion paths (objects that bank along a curve instead of sliding in a straight line).
export const bez = (p0: number[], p1: number[], p2: number[], p3: number[], t: number) => {
  const u = 1 - t;
  return [0, 1].map((i) => u * u * u * p0[i] + 3 * u * u * t * p1[i] + 3 * u * t * t * p2[i] + t * t * t * p3[i]) as [number, number];
};

// Heading of a bezier path in degrees at t (rotate the object so its nose follows the path).
export const bezAngle = (p0: number[], p1: number[], p2: number[], p3: number[], t: number) => {
  const [x0, y0] = bez(p0, p1, p2, p3, t);
  const [x1, y1] = bez(p0, p1, p2, p3, Math.min(1, t + 0.01));
  return (Math.atan2(y1 - y0, x1 - x0) * 180) / Math.PI;
};
