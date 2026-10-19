// Shared motion primitives: anchors to spoken words, easing, kinetic text, counters, panels, the phone, sound cues.
import React, { createContext, useContext } from 'react';
import * as Io from 'react-icons/io5';
import {
  AbsoluteFill, Audio, Easing, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';
import { C, F, STEP } from './theme';

export type Word = { w: string; s: number; e: number };
export type SceneData = { id: string; words: Word[]; env: number[]; frames: number; lead: number; captions: any[]; bangla?: { s: number; e: number } };

export const SceneCtx = createContext<SceneData | null>(null);
export const useScene = () => useContext(SceneCtx)!;

export const EO = Easing.bezier(0.16, 1, 0.3, 1); // fast out, long settle
export const EIO = Easing.bezier(0.65, 0, 0.35, 1);
export const EI = Easing.bezier(0.5, 0, 0.75, 0);

export const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

/** 0→1 between two frames (eased, clamped). */
export const ease = (f: number, a: number, b: number, e = EO) => interpolate(f, [a, b], [0, 1], { ...clamp, easing: e });
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/** A spring that starts at `at` (0 before). */
export const pop = (f: number, at: number, fps = 30, cfg: any = { damping: 13, stiffness: 170, mass: 0.9 }) =>
  f < at ? 0 : spring({ frame: f - at, fps, config: cfg });

const normWord = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '');

/** Frame (scene-relative) when the n-th word starting with `word` is spoken. */
export function useAt() {
  const sc = useScene();
  const { fps } = useVideoConfig();
  return (word: string, n = 0, offset = 0, edge: 's' | 'e' = 's') => {
    const k = normWord(word);
    const exact = k.length <= 2; // "I", "it", "AI", "20": whole words only
    let c = 0;
    for (const w of sc.words) {
      const nw = normWord(w.w);
      if (exact ? nw === k : nw.startsWith(k)) {
        if (c === n) return Math.round(w[edge] * fps) + offset;
        c++;
      }
    }
    throw new Error(`anchor '${word}' #${n} not found in scene ${sc.id}`);
  };
}

/** Voice loudness (0..1) at this frame of the scene: drives waveforms and glows. */
export function useEnv(f: number) {
  const sc = useScene();
  const i = Math.round(f - sc.lead * 30);
  if (i < 0 || i >= sc.env.length) return 0;
  return sc.env[i];
}

export function Icon({ name, size = 40, color = C.text, style }: { name: string; size?: number; color?: string; style?: React.CSSProperties }) {
  const Cmp = (Io as any)[name];
  if (!Cmp) throw new Error(`no icon ${name}`);
  return <Cmp size={size} color={color} style={{ display: 'block', ...style }} />;
}

/** Fade + rise + de-blur in at `at`; optional exit at `out`. */
export function Appear({ at, out, dur = 16, y = 28, x = 0, blur = 10, scale = 1, children, style }: {
  at: number; out?: number; dur?: number; y?: number; x?: number; blur?: number; scale?: number; children: React.ReactNode; style?: React.CSSProperties;
}) {
  const f = useCurrentFrame();
  const t = ease(f, at, at + dur);
  const o = out !== undefined ? 1 - ease(f, out, out + 12, EIO) : 1;
  if (t <= 0 || o <= 0) return null;
  return (
    <div style={{
      opacity: t * o,
      transform: `translate(${(1 - t) * x}px, ${(1 - t) * y + (1 - o) * -16}px) scale(${lerp(scale, 1, t)})`,
      filter: blur && t < 1 ? `blur(${(1 - t) * blur}px)` : undefined,
      ...style,
    }}>{children}</div>
  );
}

/** Springy scale-in (overshoot), for icons, chips and stamps. */
export function Pop({ at, out, children, style, from = 0.4, origin = '50% 50%' }: {
  at: number; out?: number; children: React.ReactNode; style?: React.CSSProperties; from?: number; origin?: string;
}) {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = pop(f, at, fps);
  const o = out !== undefined ? 1 - ease(f, out, out + 10, EIO) : 1;
  if (f < at || o <= 0) return null;
  return (
    <div style={{ opacity: Math.min(1, s * 1.6) * o, transform: `scale(${lerp(from, 1, s) * lerp(1, 0.9, 1 - o)})`, transformOrigin: origin, ...style }}>
      {children}
    </div>
  );
}

/**
 * Kinetic line: words rise in one by one. `*word*` is set in the serif italic accent.
 * `times` (frames) can pin each word to when it is spoken; otherwise words stagger from `at`.
 */
export function Words({ text, at, stagger = 3, size = 64, color = C.text, accent = C.neon, weight = 800, times, style, align = 'left', out, lineHeight = 1.08 }: {
  text: string; at: number; stagger?: number; size?: number; color?: string; accent?: string; weight?: number; times?: number[];
  style?: React.CSSProperties; align?: 'left' | 'center' | 'right'; out?: number; lineHeight?: number;
}) {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const parts = text.split(' ');
  // *one or more words* are set in the serif italic accent
  let inside = false;
  const emph = parts.map((p) => {
    const start = p.startsWith('*');
    if (start) inside = true;
    const on = inside;
    if (p.endsWith('*') && (p.length > 1 || !start)) inside = false;
    return on;
  });
  const o = out !== undefined ? 1 - ease(f, out, out + 12, EIO) : 1;
  if (o <= 0) return null;
  return (
    <div style={{ fontFamily: F.sans, fontWeight: weight, fontSize: size, color, letterSpacing: '-0.025em', lineHeight, textAlign: align, opacity: o, ...style }}>
      {parts.map((p, i) => {
        const em = emph[i];
        const word = p.replace(/\*/g, '');
        const t0 = times ? times[Math.min(i, times.length - 1)] : at + i * stagger;
        const s = pop(f, t0, fps, { damping: 16, stiffness: 190, mass: 0.7 });
        const k = Math.min(1, s);
        return (
          <span key={i} style={{
            display: 'inline-block', whiteSpace: 'pre', opacity: Math.min(1, s * 1.8),
            transform: `translateY(${(1 - s) * 0.55 * size}px) rotate(${(1 - k) * 3}deg)`,
            filter: k < 0.98 ? `blur(${(1 - k) * 8}px)` : undefined,
            fontFamily: em ? F.serif : F.sans, fontStyle: em ? 'italic' : 'normal', fontWeight: em ? 400 : weight,
            fontSize: em ? size * 1.12 : size, color: em ? accent : color, letterSpacing: em ? '-0.01em' : '-0.025em',
          }}>{word}{i < parts.length - 1 ? ' ' : ''}</span>
        );
      })}
    </div>
  );
}

/** A number that counts from → to between two frames, with a format function. */
export function Counter({ from, to, at, dur = 24, format = (n: number) => Math.round(n).toLocaleString('en-US'), style, e = EO }: {
  from: number; to: number; at: number; dur?: number; format?: (n: number) => string; style?: React.CSSProperties; e?: any;
}) {
  const f = useCurrentFrame();
  const t = ease(f, at, at + dur, e);
  return <span style={{ fontVariantNumeric: 'tabular-nums', ...style }}>{format(lerp(from, to, t))}</span>;
}

/** Deep-space panel with a neon rim and the app's faint grid. */
export function Panel({ children, style, glow = C.neon, grid = true, pad = 28 }: { children?: React.ReactNode; style?: React.CSSProperties; glow?: string; grid?: boolean; pad?: number }) {
  return (
    <div style={{
      position: 'relative', borderRadius: 28, padding: pad, overflow: 'hidden',
      background: `linear-gradient(160deg, ${C.panel2} 0%, ${C.panel} 60%, #0A0F1E 100%)`,
      border: `1.5px solid ${C.rim}`,
      boxShadow: `0 30px 80px rgba(0,0,0,0.45), 0 0 0 1px rgba(255,255,255,0.03) inset, 0 0 60px ${glow}22`,
      ...style,
    }}>
      {grid && <div style={{
        position: 'absolute', inset: 0, opacity: 0.9, pointerEvents: 'none',
        backgroundImage: `linear-gradient(${C.grid} 1px, transparent 1px), linear-gradient(90deg, ${C.grid} 1px, transparent 1px)`,
        backgroundSize: '28px 28px',
      }} />}
      <div style={{ position: 'relative' }}>{children}</div>
    </div>
  );
}

/** The light neumorphic shell card of the app (messages, receipts). */
export function Shell({ children, style }: { children?: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: C.shell, borderRadius: 22, padding: '18px 22px', color: C.ink, fontFamily: F.sans,
      boxShadow: '0 18px 40px rgba(0,0,0,0.35), -6px -6px 14px rgba(255,255,255,0.08) inset, 6px 6px 14px rgba(0,0,0,0.06) inset',
      border: '1px solid rgba(255,255,255,0.7)', ...style,
    }}>{children}</div>
  );
}

export function Chip({ icon, text, color = C.neon, bg, style, size = 26, textColor }: { icon?: string; text: string; color?: string; bg?: string; style?: React.CSSProperties; size?: number; textColor?: string }) {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 12, padding: `${size * 0.45}px ${size * 0.8}px`, borderRadius: 999,
      background: bg ?? `${color}1F`, border: `1.5px solid ${color}66`, color: textColor ?? C.text, fontFamily: F.sans, fontWeight: 600,
      fontSize: size, whiteSpace: 'nowrap', boxShadow: `0 0 24px ${color}22`, ...style,
    }}>
      {icon && <Icon name={icon} size={size * 1.15} color={color} />}
      <span>{text}</span>
    </div>
  );
}

/** Loop position, top left: the four steps with the current one lit. */
export function Kicker({ step, at = 0 }: { step: keyof typeof STEP; at?: number }) {
  const f = useCurrentFrame();
  const t = ease(f, at, at + 18);
  const st = STEP[step];
  return (
    <div style={{ position: 'absolute', left: 90, top: 58, display: 'flex', alignItems: 'center', gap: 22, opacity: t, transform: `translateX(${(1 - t) * -30}px)` }}>
      <div style={{ display: 'flex', gap: 8 }}>
        {(Object.keys(STEP) as (keyof typeof STEP)[]).map((k) => (
          <div key={k} style={{ width: k === step ? 46 : 22, height: 8, borderRadius: 4, background: STEP[k].n <= st.n ? STEP[k].color : 'rgba(255,255,255,0.14)', opacity: k === step ? 1 : 0.75 }} />
        ))}
      </div>
      <div style={{ fontFamily: F.sans, fontWeight: 800, fontSize: 24, letterSpacing: '0.22em', color: st.color }}>{st.n} · {st.label}</div>
    </div>
  );
}

/** Which judging criterion this scene answers, top right. */
export function Score({ text, color = C.neon, at = 6 }: { text: string; color?: string; at?: number }) {
  const f = useCurrentFrame();
  const t = ease(f, at, at + 18);
  return (
    <div style={{ position: 'absolute', right: 90, top: 46, opacity: t, transform: `translateX(${(1 - t) * 30}px)` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 22px', borderRadius: 999, border: `1.5px solid ${color}55`, background: `${color}14`, fontFamily: F.sans, fontWeight: 700, fontSize: 22, letterSpacing: '0.08em', color }}>
        <Icon name="IoRibbon" size={24} color={color} />
        {text}
      </div>
    </div>
  );
}

/** A sound effect at a scene frame. */
export function Sfx({ at, name, vol = 0.5 }: { at: number; name: string; vol?: number }) {
  if (at < 0) return null;
  return (
    <Sequence from={at} durationInFrames={90} layout="none">
      <Audio src={staticFile(`sfx/${name}.wav`)} volume={vol} />
    </Sequence>
  );
}

// ---- the phone ----------------------------------------------------------------------------------------------
export const PHONE_RATIO = 2532 / 1170;
export type Screen = { src: string; at: number; scroll?: number };
export type Tap = { x: number; y: number; at: number }; // CSS px of the 390-wide screen

/** A phone with the app's real screens: cross-fades between them, tap ripples, optional zoom on a point. */
export function Phone({ screens, taps = [], width = 430, tiltY = -12, tiltX = 4, float = true, zoom, style }: {
  screens: Screen[]; taps?: Tap[]; width?: number; tiltY?: number; tiltX?: number; float?: boolean;
  zoom?: { at: number; out?: number; x: number; y: number; k: number }; style?: React.CSSProperties;
}) {
  const f = useCurrentFrame();
  const h = width * PHONE_RATIO;
  const bez = width * 0.045;
  const sw = width - bez * 2;
  const s = sw / 390; // CSS px → screen px
  const bob = float ? Math.sin(f / 38) * 6 : 0;
  const ry = tiltY + (float ? Math.sin(f / 55) * 2.5 : 0);
  const z = zoom ? ease(f, zoom.at, zoom.at + 22, EIO) * (zoom.out !== undefined ? 1 - ease(f, zoom.out, zoom.out + 20, EIO) : 1) : 0;
  const zk = zoom ? lerp(1, zoom.k, z) : 1;
  return (
    <div style={{ perspective: 2200, ...style }}>
      <div style={{ width, height: h, transform: `translateY(${bob}px) rotateY(${ry}deg) rotateX(${tiltX}deg)`, transformStyle: 'preserve-3d', position: 'relative' }}>
        <div style={{ position: 'absolute', inset: 0, borderRadius: width * 0.14, background: 'linear-gradient(145deg,#2A2F3D,#0B0E16 60%,#1A1F2C)', boxShadow: `0 50px 120px rgba(0,0,0,0.55), 0 0 90px ${C.neon}30, inset 0 0 0 2px rgba(255,255,255,0.08)` }} />
        <div style={{ position: 'absolute', left: bez, top: bez, width: sw, height: h - bez * 2, borderRadius: width * 0.11, overflow: 'hidden', background: C.shell }}>
          <div style={{ position: 'absolute', inset: 0, transform: zoom ? `scale(${zk})` : undefined, transformOrigin: zoom ? `${zoom.x * s}px ${zoom.y * s}px` : undefined }}>
            {screens.map((sc, i) => {
              const nxt = screens[i + 1];
              const tin = i === 0 ? 1 : ease(f, sc.at, sc.at + 10);
              const tout = nxt ? ease(f, nxt.at, nxt.at + 10) : 0;
              if (f < sc.at && i > 0) return null;
              if (tout >= 1) return null;
              const scrollY = sc.scroll ?? 0;
              return (
                <Img key={i} src={staticFile(`shots/${sc.src}.png`)} style={{
                  position: 'absolute', left: 0, top: -scrollY * s, width: sw, opacity: i === 0 ? 1 : tin,
                  transform: `translateY(${(1 - tin) * 18}px)`,
                }} />
              );
            })}
            {taps.map((t, i) => {
              const k = ease(f, t.at, t.at + 16);
              if (f < t.at - 8 || k >= 1) return null;
              const pre = ease(f, t.at - 8, t.at);
              return (
                <div key={i} style={{ position: 'absolute', left: t.x * s, top: t.y * s, width: 0, height: 0 }}>
                  <div style={{ position: 'absolute', left: -60 * s * (0.3 + k), top: -60 * s * (0.3 + k), width: 120 * s * (0.3 + k), height: 120 * s * (0.3 + k), borderRadius: '50%', background: `rgba(0,122,255,${0.35 * (1 - k)})`, border: `3px solid rgba(255,255,255,${0.9 * (1 - k)})` }} />
                  <div style={{ position: 'absolute', left: -22 * s, top: -22 * s, width: 44 * s, height: 44 * s, borderRadius: '50%', background: `rgba(255,255,255,${0.75 * pre * (1 - k)})`, boxShadow: '0 4px 14px rgba(0,0,0,0.3)' }} />
                </div>
              );
            })}
          </div>
        </div>
        <div style={{ position: 'absolute', left: '50%', top: bez + 10, width: width * 0.24, height: width * 0.055, marginLeft: -width * 0.12, borderRadius: 99, background: '#05070C' }} />
      </div>
    </div>
  );
}

/** Highlight ring drawn around a box (absolute coordinates in the parent). */
export function Ring({ at, x, y, w, h, color = C.neon, r = 18, out }: { at: number; x: number; y: number; w: number; h: number; color?: string; r?: number; out?: number }) {
  const f = useCurrentFrame();
  const t = ease(f, at, at + 18, EIO);
  const o = out !== undefined ? 1 - ease(f, out, out + 10) : 1;
  if (t <= 0 || o <= 0) return null;
  const per = 2 * (w + h);
  return (
    <svg style={{ position: 'absolute', left: x - 6, top: y - 6, overflow: 'visible', opacity: o }} width={w + 12} height={h + 12}>
      <rect x={3} y={3} width={w + 6} height={h + 6} rx={r} fill="none" stroke={color} strokeWidth={4}
        strokeDasharray={per} strokeDashoffset={per * (1 - t)} style={{ filter: `drop-shadow(0 0 10px ${color})` }} />
    </svg>
  );
}

/** A stamp that slams down (REFUSED, APPROVED, SCAM). */
export function Stamp({ at, text, color = C.red, size = 120, rotate = -8, icon, style }: { at: number; text: string; color?: string; size?: number; rotate?: number; icon?: string; style?: React.CSSProperties }) {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (f < at) return null;
  const s = spring({ frame: f - at, fps, config: { damping: 11, stiffness: 260, mass: 0.6 } });
  const k = lerp(2.4, 1, s);
  return (
    <div style={{ transform: `rotate(${rotate}deg) scale(${k})`, opacity: Math.min(1, (f - at) / 3), ...style }}>
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: size * 0.18, padding: `${size * 0.12}px ${size * 0.3}px`, border: `${size * 0.07}px solid ${color}`,
        borderRadius: size * 0.16, color, fontFamily: F.sans, fontWeight: 900, fontSize: size, letterSpacing: '0.06em',
        background: `${color}12`, boxShadow: `0 0 60px ${color}55, inset 0 0 40px ${color}22`, textShadow: `0 0 30px ${color}88`,
      }}>
        {icon && <Icon name={icon} size={size * 0.9} color={color} />}
        {text}
      </div>
    </div>
  );
}

/** Frame-based camera shake for impacts. */
export function shake(f: number, at: number, amp = 14, dur = 10) {
  if (f < at || f > at + dur) return { x: 0, y: 0 };
  const k = 1 - (f - at) / dur;
  return { x: Math.sin((f - at) * 2.9) * amp * k, y: Math.cos((f - at) * 3.7) * amp * k * 0.7 };
}

export function Full({ children, style }: { children?: React.ReactNode; style?: React.CSSProperties }) {
  return <AbsoluteFill style={style}>{children}</AbsoluteFill>;
}

/** Typing reveal of a string between two frames, with a caret. */
export function Typed({ text, at, end, style, caret = true }: { text: string; at: number; end: number; style?: React.CSSProperties; caret?: boolean }) {
  const f = useCurrentFrame();
  const chars = Array.from(text);
  const n = Math.round(interpolate(f, [at, end], [0, chars.length], clamp));
  const blink = caret && f < end + 30 && Math.floor(f / 8) % 2 === 0;
  return (
    <span style={style}>
      {chars.slice(0, n).join('')}
      <span style={{ opacity: blink ? 1 : 0, color: C.neon }}>|</span>
    </span>
  );
}
