// Word-synced captions: the current phrase, the word being spoken lit in neon.
import React from 'react';
import { useCurrentFrame } from 'remotion';
import { C, F } from './theme';
import { ease, EO } from './lib';

export function Captions({ scenes, hide }: { scenes: any[]; hide: Record<string, [number, number][]> }) {
  const f = useCurrentFrame();
  const sc = [...scenes].reverse().find((s) => s.from <= f);
  if (!sc) return null;
  const t = (f - sc.from) / 30;
  if ((hide[sc.id] ?? []).some(([a, b]) => t >= a && t < b)) return null;
  const idx = sc.captions.findIndex((c: any) => t >= c.s && t < c.e);
  if (idx < 0) return null;
  const c = sc.captions[idx];
  const cf = f - sc.from - Math.round(c.s * 30);
  const k = ease(cf, 0, 7, EO);
  const out = ease(f - sc.from, Math.round(c.e * 30) - 5, Math.round(c.e * 30), EO);
  const bn = !!c.bangla;
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, bottom: 58, display: 'flex', justifyContent: 'center', pointerEvents: 'none' }}>
      <div style={{
        maxWidth: 1500, padding: '14px 30px', borderRadius: 18, background: 'rgba(6,10,22,0.78)', border: '1px solid rgba(77,163,255,0.22)',
        boxShadow: '0 12px 40px rgba(0,0,0,0.45)', opacity: k * (1 - out), transform: `translateY(${(1 - k) * 10}px)`,
        fontFamily: bn ? F.serif : F.sans, fontStyle: bn ? 'italic' : 'normal', fontWeight: bn ? 400 : 600, fontSize: bn ? 40 : 36,
        color: C.text, letterSpacing: bn ? 0 : '-0.01em', lineHeight: 1.25, textAlign: 'center',
      }}>
        {c.words.map((w: any, i: number) => {
          const spoken = t >= w.s;
          const now = t >= w.s && t < w.e + 0.08;
          return (
            <span key={i} style={{ color: bn ? C.text : now ? C.neon : spoken ? C.text : 'rgba(232,238,255,0.5)', transition: 'none' }}>
              {w.w}{i < c.words.length - 1 ? ' ' : ''}
            </span>
          );
        })}
      </div>
    </div>
  );
}
