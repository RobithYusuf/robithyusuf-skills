// Kinetic type that reads as motion design, not as a web page. Expects src/lib/ease.
import React, {CSSProperties} from 'react';
import {useCurrentFrame} from 'remotion';
import {E, pr, tw} from '../lib/ease';

export type Seg = {t: string; accent?: boolean};

const DISPLAY = '"Inter", system-ui, sans-serif'; // replace with the project's display family

type LineProps = {
  segs: Seg[] | string; // [{t: 'Satu brief,'}, {t: 'satu feed', accent: true}]
  start: number; // frame the first word starts rising
  size: number;
  color?: string;
  weight?: number;
  stagger?: number; // frames between words (2-3)
  dur?: number; // frames per word
  out?: number; // frame where the words leave (upwards, through the same mask)
  tracking?: number; // em
  accent?: string; // CSS gradient for accent words; without it accent words are only italic
  font?: string;
  lineHeight?: number;
  style?: CSSProperties;
};

// Every word rises through its own mask with a small rotation that settles. The mask keeps 0.36em below the baseline
// so descenders (g, j, p, y) are never clipped, and words are hidden before and after their move so a word waiting
// below the mask never shows through at large sizes.
export const Line: React.FC<LineProps> = ({
  segs,
  start,
  size,
  color = '#fff',
  weight = 800,
  stagger = 2.5,
  dur = 18,
  out,
  tracking = -0.035,
  accent,
  font = DISPLAY,
  lineHeight = 1.02,
  style,
}) => {
  const frame = useCurrentFrame();
  const parts: Seg[] = typeof segs === 'string' ? [{t: segs}] : segs;
  const words: Array<{w: string; accent?: boolean}> = [];
  parts.forEach((p) => p.t.split(' ').filter(Boolean).forEach((w) => words.push({w, accent: p.accent})));
  return (
    <div style={{fontFamily: font, fontSize: size, fontWeight: weight, color, letterSpacing: `${tracking}em`, lineHeight, whiteSpace: 'nowrap', ...style}}>
      {words.map(({w, accent: acc}, i) => {
        const p = pr(frame, start + i * stagger, start + i * stagger + dur, E.out);
        const q = out === undefined ? 0 : pr(frame, out + i * 1.4, out + i * 1.4 + 11, E.in);
        const y = (1 - p) * 112 - q * 112;
        const rot = (1 - p) * 7 - q * 3;
        const shown = p > 0 && q < 1;
        return (
          <React.Fragment key={i}>
            <span style={{display: 'inline-block', overflow: 'hidden', verticalAlign: 'top', padding: '0.08em 0.16em 0.36em 0.04em', margin: '-0.08em -0.16em -0.36em -0.04em'}}>
              <span
                style={{
                  display: 'inline-block',
                  transform: `translateY(${y}%) rotate(${rot}deg)`,
                  transformOrigin: '0% 100%',
                  opacity: shown ? 1 : 0,
                  fontStyle: acc ? 'italic' : 'normal',
                  ...(acc && accent
                    ? {backgroundImage: accent, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', padding: '0 0.08em 0.32em 0', margin: '0 -0.02em -0.32em 0'}
                    : {}),
                }}
              >
                {w}
              </span>
            </span>
            {i < words.length - 1 ? ' ' : null}
          </React.Fragment>
        );
      })}
    </div>
  );
};

// Impact word: lands from a slight over-scale while the blur clears and the tracking tightens.
export const Slam: React.FC<{text: string; start: number; size: number; color?: string; accent?: string; italic?: boolean; out?: number; font?: string; style?: CSSProperties}> = ({
  text,
  start,
  size,
  color = '#fff',
  accent,
  italic = false,
  out,
  font = DISPLAY,
  style,
}) => {
  const frame = useCurrentFrame();
  const p = pr(frame, start, start + 13, E.out);
  const q = out === undefined ? 0 : pr(frame, out, out + 10, E.in);
  const scale = 1.34 - 0.34 * p + q * 0.12;
  const blur = (1 - p) * 16 + q * 10;
  return (
    <div
      style={{
        fontFamily: font,
        fontSize: size,
        fontWeight: 800,
        fontStyle: italic ? 'italic' : 'normal',
        letterSpacing: `${tw(frame, start, start + 16, 0.04, -0.045)}em`,
        lineHeight: 1,
        whiteSpace: 'nowrap',
        transform: `scale(${scale})`,
        transformOrigin: '0% 70%',
        filter: blur > 0.2 ? `blur(${blur}px)` : undefined,
        opacity: Math.min(1, p * 2.4) * (1 - q),
        ...(accent ? {backgroundImage: accent, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', padding: '0 0.1em 0.3em 0', marginBottom: '-0.3em'} : {color}),
        ...style,
      }}
    >
      {text}
    </div>
  );
};

// Editorial caption instead of a web pill: a dim index number, then the text rising through a mask. No background, no
// border, no hairline between number and text (a short rule there reads as a dash).
export const Caption: React.FC<{text: string; start: number; index?: string; color?: string; size?: number; font?: string; style?: CSSProperties}> = ({
  text,
  start,
  index,
  color = '#0f1424',
  size = 32,
  font = DISPLAY,
  style,
}) => {
  const frame = useCurrentFrame();
  const num = pr(frame, start, start + 12, E.out);
  const word = pr(frame, start + 4, start + 18, E.out);
  return (
    <div style={{display: 'flex', alignItems: 'center', gap: size * 0.45, fontFamily: font, color, ...style}}>
      {index ? (
        <span style={{fontSize: size * 0.62, fontWeight: 600, letterSpacing: '0.08em', opacity: 0.6 * Math.min(1, num * 2), fontVariantNumeric: 'tabular-nums'}}>{index}</span>
      ) : null}
      <span style={{display: 'inline-block', overflow: 'hidden', padding: '0.06em 0.1em 0.3em 0', margin: '-0.06em -0.1em -0.3em 0'}}>
        <span style={{display: 'inline-block', fontSize: size, fontWeight: 700, letterSpacing: '-0.01em', transform: `translateY(${(1 - word) * 110}%)`}}>{text}</span>
      </span>
    </div>
  );
};
