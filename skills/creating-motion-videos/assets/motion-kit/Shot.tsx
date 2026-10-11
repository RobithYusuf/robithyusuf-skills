// One shot on the timeline with whip transitions. A whip is ONE continuous strip: the outgoing shot's exit and the
// incoming shot's enter use the same direction, the same length and the same curve, and they overlap by exactly `len`
// frames, so the seam travels at one speed. Directional blur follows velocity, plus a few px of RGB split (lens
// fringing) at peak speed. Expects src/lib/{context,ease}.
//
//   <Shot name="hook"  from={0}   dur={120} exit={{dir: 'up', len: 16}}>…</Shot>
//   <Shot name="brief" from={104} dur={132} enter={{dir: 'up', len: 16}}>…</Shot>   // 104 = 120 - 16
import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {useDraft} from '../lib/context';
import {E, pr} from '../lib/ease';

export type Dir = 'up' | 'down' | 'left' | 'right';
export type Move = {dir: Dir; len: number};

const vertical = (d: Dir) => d === 'up' || d === 'down';
const sign = (d: Dir) => (d === 'up' || d === 'left' ? 1 : -1);

// Offset along the move axis: enter goes from +size to 0, exit from 0 to -size (signs flip for down/right).
const offsetAt = (f: number, dur: number, w: number, h: number, enter?: Move, exit?: Move) => {
  let o = 0;
  if (enter) o += (1 - pr(f, 0, enter.len, E.inOut)) * sign(enter.dir) * (vertical(enter.dir) ? h : w);
  if (exit) o -= pr(f, dur - exit.len, dur, E.inOut) * sign(exit.dir) * (vertical(exit.dir) ? h : w);
  return o;
};

const Inner: React.FC<{dur: number; enter?: Move; exit?: Move; id: string; maxBlur: number; children: React.ReactNode}> = ({
  dur,
  enter,
  exit,
  id,
  maxBlur,
  children,
}) => {
  const f = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const draft = useDraft();
  const o = offsetAt(f, dur, width, height, enter, exit);
  const v = Math.abs(offsetAt(f + 0.5, dur, width, height, enter, exit) - offsetAt(f - 0.5, dur, width, height, enter, exit));
  const dir: Dir = (enter && f < enter.len ? enter.dir : exit?.dir) ?? 'up';
  const vert = vertical(dir);
  const blur = draft ? 0 : Math.min(maxBlur, v * 0.42);
  const ca = Math.min(9, blur * 0.16); // red and blue drift apart along the move
  const dx = vert ? 0 : ca;
  const dy = vert ? ca : 0;
  const t = vert ? `translateY(${o}px)` : `translateX(${o}px)`;
  const on = blur > 0.6;
  return (
    <AbsoluteFill style={{transform: o ? t : undefined, filter: on ? `url(#${id})` : undefined}}>
      {on ? (
        <svg width="0" height="0" style={{position: 'absolute'}}>
          {/* the id must be unique per shot, otherwise another shot picks up this blur */}
          <filter id={id} x="-5%" y="-10%" width="110%" height="120%" colorInterpolationFilters="sRGB">
            <feGaussianBlur in="SourceGraphic" stdDeviation={vert ? `0 ${blur}` : `${blur} 0`} result="bl" />
            <feColorMatrix in="bl" type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="r" />
            <feOffset in="r" dx={-dx} dy={-dy} result="r2" />
            <feColorMatrix in="bl" type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0" result="g" />
            <feColorMatrix in="bl" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0" result="b" />
            <feOffset in="b" dx={dx} dy={dy} result="b2" />
            <feBlend in="r2" in2="g" mode="screen" result="rg" />
            <feBlend in="rg" in2="b2" mode="screen" />
          </filter>
        </svg>
      ) : null}
      {children}
    </AbsoluteFill>
  );
};

export const Shot: React.FC<{from: number; dur: number; enter?: Move; exit?: Move; name: string; maxBlur?: number; children: React.ReactNode}> = ({
  from,
  dur,
  enter,
  exit,
  name,
  maxBlur = 70,
  children,
}) => (
  <Sequence from={from} durationInFrames={dur} name={name}>
    <Inner dur={dur} enter={enter} exit={exit} id={`whip-${name}`} maxBlur={maxBlur}>
      {children}
    </Inner>
  </Sequence>
);
