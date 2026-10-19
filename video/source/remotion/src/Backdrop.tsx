// The deep-space stage under every scene: drifting colour fields, the app's neon grid, slow particles, a vignette.
import React from 'react';
import { AbsoluteFill, interpolateColors, random, useCurrentFrame } from 'remotion';
import { C } from './theme';

const DOTS = Array.from({ length: 46 }, (_, i) => ({
  x: random(`x${i}`) * 1920, y: random(`y${i}`) * 1080, r: 1 + random(`r${i}`) * 2.2, v: 0.15 + random(`v${i}`) * 0.45, a: 0.15 + random(`a${i}`) * 0.4,
}));

export function Backdrop({ accents }: { accents: { from: number; color: string }[] }) {
  const f = useCurrentFrame();
  // accent colour follows the scene, blending over 24 frames at each change
  let i = 0;
  while (i + 1 < accents.length && accents[i + 1].from <= f) i++;
  const cur = accents[i];
  const prev = accents[Math.max(0, i - 1)];
  const accent = i > 0 && f - cur.from < 24 ? interpolateColors(f - cur.from, [0, 24], [prev.color, cur.color]) : cur.color;
  const blob = (x: number, y: number, size: number, color: string, alpha: number) => (
    <div style={{
      position: 'absolute', left: x - size / 2, top: y - size / 2, width: size, height: size, borderRadius: '50%',
      background: `radial-gradient(circle, ${color} 0%, transparent 68%)`, opacity: alpha,
    }} />
  );
  return (
    <AbsoluteFill style={{ background: `radial-gradient(120% 90% at 50% 40%, ${C.bg1} 0%, ${C.bg0} 70%)`, overflow: 'hidden' }}>
      {blob(320 + 180 * Math.sin(f / 170), 260 + 120 * Math.cos(f / 210), 1500, accent, 0.26)}
      {blob(1580 + 150 * Math.cos(f / 190), 840 + 110 * Math.sin(f / 160), 1400, C.blue, 0.2)}
      {blob(980 + 320 * Math.sin(f / 260), 540 + 180 * Math.sin(f / 230), 1100, '#1F4FEA', 0.12)}
      <AbsoluteFill style={{
        backgroundImage: `linear-gradient(rgba(77,163,255,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(77,163,255,0.07) 1px, transparent 1px)`,
        backgroundSize: '64px 64px', backgroundPosition: `${(f * 0.35) % 64}px ${(f * 0.2) % 64}px`,
        WebkitMaskImage: 'radial-gradient(75% 70% at 50% 45%, black 20%, transparent 85%)',
        maskImage: 'radial-gradient(75% 70% at 50% 45%, black 20%, transparent 85%)',
      }} />
      {DOTS.map((d, k) => {
        const y = (d.y - f * d.v + 1080 * 4) % 1080;
        return <div key={k} style={{ position: 'absolute', left: d.x, top: y, width: d.r * 2, height: d.r * 2, borderRadius: '50%', background: C.neon, opacity: d.a * (0.6 + 0.4 * Math.sin(f / 30 + k)) }} />;
      })}
      <AbsoluteFill style={{ background: 'radial-gradient(90% 80% at 50% 45%, transparent 55%, rgba(0,0,0,0.6) 100%)' }} />
    </AbsoluteFill>
  );
}
