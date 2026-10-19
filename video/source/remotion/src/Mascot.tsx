// The app's Bluefin robot, redrawn from mobile/src/components/mascot.tsx and driven by frames:
// it breathes, blinks, shakes its head at an attack, nods when something is right, and raises a badge.
import React from 'react';
import { useCurrentFrame, useVideoConfig, spring } from 'remotion';
import { C } from './theme';
import { Icon, lerp } from './lib';

type Eye = 'open' | 'happy' | 'small' | 'focused';

export function Mascot({ size = 220, shakeAt = [], nodAt = [], jumpAt = [], badge, eye = 'open', glow = 0.35, look = 0, talk }: {
  size?: number; shakeAt?: number[]; nodAt?: number[]; jumpAt?: number[]; badge?: { at: number; icon: string; color?: string; out?: number };
  eye?: Eye; glow?: number; look?: number; talk?: number;
}) {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const k = size / 200;
  const bob = Math.sin(f / 16) * 3;
  // blink every ~3 s
  const bp = f % 92;
  const blink = bp < 3 ? lerp(1, 0.1, bp / 3) : bp < 7 ? lerp(0.1, 1, (bp - 3) / 4) : 1;
  let rot = 0;
  for (const s of shakeAt) {
    const d = f - s;
    if (d >= 0 && d < 24) rot += Math.sin(d * 0.9) * 9 * (1 - d / 24);
  }
  let headY = 0;
  for (const s of nodAt) {
    const d = f - s;
    if (d >= 0 && d < 18) headY += Math.abs(Math.sin(d * 0.35)) * 6 * (1 - d / 18);
  }
  let jump = 0;
  for (const s of jumpAt) {
    const d = f - s;
    if (d >= 0 && d < 20) jump -= Math.sin((d / 20) * Math.PI) * 22;
  }
  const lid = blink * (talk !== undefined ? lerp(0.55, 1, talk) : 1);
  const b = badge && f >= badge.at ? spring({ frame: f - badge.at, fps, config: { damping: 11, stiffness: 200 } }) * (badge.out !== undefined && f > badge.out ? Math.max(0, 1 - (f - badge.out) / 8) : 1) : 0;
  const eyeEl = (left: number) => (
    <div style={{ position: 'absolute', left: (33 + left + look) * k, top: (31 + 28) * k, width: 22 * k, height: 26 * k, transform: `scaleY(${lid})` }}>
      <svg width={22 * k} height={26 * k} viewBox="0 0 22 26">
        {eye === 'happy' ? <path d="M3,18 Q11,4 19,18" stroke="#F5F5F7" strokeWidth="5.5" strokeLinecap="round" fill="none" />
          : eye === 'small' ? <rect x="4" y="5" width="14" height="17" rx="5" fill="#F5F5F7" />
            : eye === 'focused' ? <rect x="0" y="8" width="22" height="18" rx="6" fill="#F5F5F7" />
              : <rect x="0" y="0" width="22" height="26" rx="7" fill="#F5F5F7" />}
      </svg>
    </div>
  );
  return (
    <div style={{ width: size, height: size * 1.1, position: 'relative' }}>
      <svg style={{ position: 'absolute', left: 50 * k, top: 204 * k }} width={100 * k} height={14 * k} viewBox="0 0 100 14">
        <ellipse cx="50" cy="7" rx="50" ry="7" fill="#000" opacity={0.35} />
      </svg>
      <div style={{ position: 'absolute', inset: 0, transform: `translateY(${(bob + jump) * k}px)` }}>
        {[46, 128].map((x, i) => (
          <svg key={i} style={{ position: 'absolute', left: x * k, top: 144 * k, transform: `rotate(${i ? -6 : 6}deg)`, transformOrigin: i ? '20% 14%' : '80% 14%' }} width={26 * k} height={40 * k} viewBox="0 0 26 40">
            <defs><linearGradient id={`lb${i}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#7B7E82" /><stop offset="1" stopColor="#505357" /></linearGradient></defs>
            <rect x="4" y="2" width="18" height="34" rx="9" fill={`url(#lb${i})`} />
          </svg>
        ))}
        <svg style={{ position: 'absolute', left: 64 * k, top: 122 * k }} width={72 * k} height={82 * k} viewBox="0 0 72 82">
          <defs><linearGradient id="mb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#7B7E82" /><stop offset="1" stopColor="#4B4E52" /></linearGradient></defs>
          <path d="M14,0 H58 Q72,0 72,14 V62 Q72,80 56,80 H44 Q38,80 36,73 Q34,80 28,80 H16 Q0,80 0,62 V14 Q0,0 14,0 Z" fill="url(#mb)" />
          <ellipse cx="26" cy="22" rx="14" ry="6" fill="#FFFFFF" opacity={0.1} />
        </svg>
        <div style={{ position: 'absolute', left: 12 * k, top: (4 + headY) * k, width: 176 * k, height: 140 * k, transform: `rotate(${rot}deg)`, transformOrigin: '50% 94%' }}>
          <svg width={176 * k} height={140 * k} viewBox="0 0 176 140" style={{ position: 'absolute' }}>
            <defs>
              <linearGradient id="mh" x1="0" y1="0" x2="0.35" y2="1"><stop offset="0" stopColor="#9C9FA3" /><stop offset="0.55" stopColor="#74777B" /><stop offset="1" stopColor="#56595D" /></linearGradient>
              <linearGradient id="me" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#6F7276" /><stop offset="1" stopColor="#45484C" /></linearGradient>
              <linearGradient id="mv" x1="0" y1="0" x2="0.3" y2="1"><stop offset="0" stopColor="#2E2E33" /><stop offset="0.5" stopColor="#1D1D1F" /><stop offset="1" stopColor="#0E0E10" /></linearGradient>
              <radialGradient id="mg" cx="50%" cy="50%" r="50%"><stop offset="0" stopColor={C.blue} stopOpacity={0.55} /><stop offset="1" stopColor={C.blue} stopOpacity={0} /></radialGradient>
            </defs>
            <rect x="0" y="48" width="18" height="42" rx="7" fill="url(#me)" />
            <rect x="158" y="48" width="18" height="42" rx="7" fill="url(#me)" />
            <rect x="10" y="2" width="156" height="132" rx="46" fill="url(#mh)" />
            <ellipse cx="72" cy="20" rx="50" ry="11" fill="#FFFFFF" opacity={0.16} />
            <rect x="28" y="26" width="120" height="90" rx="34" fill="#3D4044" />
            <rect x="28.5" y="26.5" width="119" height="89" rx="33.5" fill="none" stroke={C.neon} strokeWidth="1.6" opacity={0.85} />
            <rect x="33" y="31" width="110" height="80" rx="30" fill="url(#mv)" />
            <ellipse cx="88" cy="71" rx="45" ry="35" fill="url(#mg)" opacity={glow + 0.25 * Math.sin(f / 20) ** 2} />
            <path d="M47,52 Q50,40 64,38" stroke="#FFFFFF" strokeWidth="4.5" strokeLinecap="round" fill="none" opacity={0.2} />
            <rect x="6" y="56" width="6" height="26" rx="3" fill={C.neon} opacity={0.6 + 0.4 * glow} />
            <rect x="164" y="56" width="6" height="26" rx="3" fill={C.neon} opacity={0.6 + 0.4 * glow} />
          </svg>
          {eyeEl(28)}
          {eyeEl(60)}
        </div>
      </div>
      {badge && b > 0 && (
        <div style={{ position: 'absolute', left: 146 * k, top: -2 * k, width: 52 * k, height: 52 * k, borderRadius: '50%', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${b})`, boxShadow: `0 6px 20px rgba(0,0,0,0.35), 0 0 30px ${badge.color ?? C.blue}66` }}>
          <Icon name={badge.icon} size={30 * k} color={badge.color ?? C.blue} />
        </div>
      )}
    </div>
  );
}
