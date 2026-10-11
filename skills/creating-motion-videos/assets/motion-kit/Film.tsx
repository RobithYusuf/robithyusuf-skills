// Film layer helpers: motion blur, grain, vignette, photographed backdrop, handheld drift, idle float, depth particles.
// Expects src/lib/context.tsx (useDraft) and @remotion/motion-blur + @remotion/noise at the same version as remotion.
import {CameraMotionBlur} from '@remotion/motion-blur';
import {noise2D} from '@remotion/noise';
import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {useDraft} from '../lib/context';

// Real sub-frame motion blur (renders the subtree `samples` times across the shutter). Costly: wrap only layers that
// move fast (flying objects, cards entering), never the whole composition.
export const MB: React.FC<{children: React.ReactNode; samples?: number; shutter?: number}> = ({children, samples = 8, shutter = 210}) => {
  const draft = useDraft();
  if (draft) return <AbsoluteFill>{children}</AbsoluteFill>;
  return (
    <CameraMotionBlur samples={samples} shutterAngle={shutter}>
      {children}
    </CameraMotionBlur>
  );
};

// Animated film grain: fresh monochrome noise every frame, overlay blend. 6-8 % reads as film, more reads as dirt.
export const Grain: React.FC<{opacity?: number}> = ({opacity = 0.07}) => {
  const frame = useCurrentFrame();
  const draft = useDraft();
  if (draft) return null;
  return (
    <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'overlay', opacity}}>
      <svg width="100%" height="100%">
        <filter id="film-grain" x="0" y="0" width="100%" height="100%">
          <feTurbulence type="fractalNoise" baseFrequency="0.82" numOctaves="2" seed={(frame * 7) % 211} stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
          <feComponentTransfer>
            <feFuncR type="linear" slope="1.6" intercept="-0.3" />
            <feFuncG type="linear" slope="1.6" intercept="-0.3" />
            <feFuncB type="linear" slope="1.6" intercept="-0.3" />
          </feComponentTransfer>
        </filter>
        <rect width="100%" height="100%" filter="url(#film-grain)" />
      </svg>
    </AbsoluteFill>
  );
};

export const Vignette: React.FC<{strength?: number}> = ({strength = 0.4}) => (
  <AbsoluteFill
    style={{pointerEvents: 'none', background: `radial-gradient(ellipse 85% 70% at 50% 46%, transparent 52%, rgba(0,0,0,${strength}) 100%)`}}
  />
);

// Photographed backdrop (an empty studio cyclorama, a plaster wall) with a slow dolly push over the shot.
// A photo plate instead of a CSS gradient is one of the biggest steps away from the "web page" look.
export const Plate: React.FC<{src: string; push?: number; brightness?: number; y?: number; fallback?: string}> = ({
  src,
  push = 0.05,
  brightness = 1,
  y = 0,
  fallback = '#111',
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const s = 1.06 + (push * frame) / durationInFrames;
  return (
    <AbsoluteFill style={{background: fallback, overflow: 'hidden'}}>
      <Img
        src={staticFile(src)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `translateY(${y}px) scale(${s})`,
          filter: brightness !== 1 ? `brightness(${brightness})` : undefined,
        }}
      />
    </AbsoluteFill>
  );
};

// Handheld drift (Perlin) for a whole shot, in px / degrees. Keep amp <= 6: felt, not seen.
export const useDrift = (seed: string, amp = 5, speed = 0.018) => {
  const frame = useCurrentFrame();
  return {
    x: noise2D(seed + 'x', frame * speed, 0) * amp,
    y: noise2D(seed + 'y', 0, frame * speed) * amp,
    r: noise2D(seed + 'r', frame * speed * 0.7, 3) * amp * 0.05,
  };
};

// Idle life for every asset: slow bob + Perlin drift + tiny breathing, each instance on its own phase (seed) so a group
// never moves in lockstep.
const phaseOf = (seed: string) => {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) % 9973;
  return (h / 9973) * Math.PI * 2;
};

export type FloatOpts = {amp?: number; rot?: number; breathe?: number; speed?: number};

export const floatAt = (frame: number, seed: string, {amp = 9, rot = 0.7, breathe = 0.006, speed = 1}: FloatOpts = {}) => {
  const t = (frame / 30) * speed;
  const ph = phaseOf(seed);
  return {
    x: noise2D(seed + 'fx', t * 0.32, 0) * amp * 0.55,
    y: Math.sin(t * 1.45 + ph) * amp + noise2D(seed + 'fy', 0, t * 0.4) * amp * 0.3,
    r: Math.sin(t * 1.05 + ph * 1.7) * rot + noise2D(seed + 'fr', t * 0.25, 7) * rot * 0.4,
    s: 1 + Math.sin(t * 0.9 + ph * 2.3) * breathe,
  };
};

export const useFloat = (seed: string, opts?: FloatOpts) => floatAt(useCurrentFrame(), seed, opts);

export const floatCss = (fl: {x: number; y: number; r: number; s: number}) =>
  `translate(${fl.x.toFixed(2)}px, ${fl.y.toFixed(2)}px) rotate(${fl.r.toFixed(3)}deg) scale(${fl.s.toFixed(4)})`;

export const Float: React.FC<{seed: string; opts?: FloatOpts; style?: React.CSSProperties; children: React.ReactNode}> = ({seed, opts, style, children}) => {
  const fl = useFloat(seed, opts);
  return <div style={{position: 'absolute', inset: 0, transform: floatCss(fl), ...style}}>{children}</div>;
};

// Depth particles (keyed photos of real paper scraps, leaves, dust...). Near pieces: big, soft, fast (parallax).
// Far pieces: small, crisp, slow. Position in px at frame 0, velocity in px per frame.
export type Particle = {src: string; w: number; h: number; x: number; y: number; scale: number; blur: number; vx: number; vy: number; rot: number; spin: number; opacity?: number};

export const Particles: React.FC<{items: Particle[]; seed: string}> = ({items, seed}) => {
  const f = useCurrentFrame();
  const draft = useDraft();
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {items.map((p, k) => {
        const fl = floatAt(f, `${seed}${k}`, {amp: 10, rot: 2, breathe: 0});
        const x = p.x + p.vx * f + fl.x;
        const y = p.y + p.vy * f + fl.y;
        return (
          <Img
            key={k}
            src={staticFile(p.src)}
            style={{
              position: 'absolute',
              left: x - p.w / 2,
              top: y - p.h / 2,
              width: p.w,
              height: p.h,
              opacity: p.opacity ?? 1,
              transform: `rotate(${p.rot + p.spin * f + fl.r}deg) scale(${p.scale})`,
              filter: !draft && p.blur > 0.3 ? `blur(${p.blur}px) drop-shadow(0 12px 18px rgba(0,0,0,0.35))` : 'drop-shadow(0 10px 14px rgba(0,0,0,0.3))',
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
