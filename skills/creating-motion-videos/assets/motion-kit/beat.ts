// Edit grid. Every cut, title and accent lands on b(k) (or a half beat). Measure the music's tempo and beat phase with a
// script instead of guessing, then either fit the music to this grid (time-stretch < 1.5 %, cut on bars) or make the
// grid match the music. Beat 0 = frame 0; when the music starts earlier in its file, trim the file, never shift cuts.
export const FPS = 30;
export const BPM = 122;
export const BEAT = (60 / BPM) * FPS; // frames per beat (14.75 at 122 BPM, 30 fps)
export const b = (k: number) => Math.round(k * BEAT);
export const bar = (n: number) => b(n * 4); // 4/4

// Typical 30 s ad at ~122 BPM: drop (signature moment) on beat 16 (~7.9 s), last beat 60, a few frames of tail.
export const DROP = b(16);
export const TOTAL = b(60) + 30;
