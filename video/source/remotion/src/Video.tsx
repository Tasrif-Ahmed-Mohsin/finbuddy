// The whole film: backdrop, scenes in order with their voice, captions, music.
import React, { useEffect, useState } from 'react';
import { AbsoluteFill, Audio, Sequence, continueRender, delayRender, staticFile, useCurrentFrame } from 'remotion';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';
import '@fontsource/inter/800.css';
import '@fontsource/inter/900.css';
import '@fontsource/instrument-serif/400.css';
import '@fontsource/instrument-serif/400-italic.css';
import '@fontsource/noto-sans-bengali/500.css';
import '@fontsource/noto-sans-bengali/700.css';
import timeline from './timeline.json';
import { C } from './theme';
import { Backdrop } from './Backdrop';
import { Captions } from './Captions';
import { EIO, SceneCtx, ease } from './lib';
import { FriendA, S02, S03 } from './scenesA';
import { S4a, S4b, S4c } from './scenesB';
import { S4d, S4e, S4f } from './scenesC';
import { S4g, S4h, S4i, S4j } from './scenesD';
import { S05, S06, FriendB, S08 } from './scenesE';

const SCENES: Record<string, { C: React.FC; accent: string }> = {
  fa: { C: FriendA, accent: C.blue },
  '02': { C: S02, accent: C.red },
  '03': { C: S03, accent: C.neon },
  '4a': { C: S4a, accent: C.neon },
  '4b': { C: S4b, accent: C.neon },
  '4c': { C: S4c, accent: C.amber },
  '4d': { C: S4d, accent: C.green },
  '4e': { C: S4e, accent: C.green },
  '4f': { C: S4f, accent: C.red },
  '4g': { C: S4g, accent: C.green },
  '4h': { C: S4h, accent: C.green },
  '4i': { C: S4i, accent: C.purple },
  '4j': { C: S4j, accent: C.purple },
  '05': { C: S05, accent: C.neon },
  '06': { C: S06, accent: C.amber },
  fb: { C: FriendB, accent: C.blue },
  '08': { C: S08, accent: C.neon },
};

// Seconds (scene-relative) where the captions step aside for big type that already says the words.
export const HIDE: Record<string, [number, number][]> = {
  '4f': [[8.4, 14.6]],
  '08': [[6.9, 99]],
};

const OVERLAP = 8; // frames the outgoing scene lingers while the next one enters

function SceneFrame({ s, children }: { s: any; children: React.ReactNode }) {
  const f = useCurrentFrame();
  const out = ease(f, s.frames - 4, s.frames + OVERLAP, EIO);
  return (
    <AbsoluteFill style={{ opacity: 1 - out, transform: `scale(${(1 + 0.022 * Math.min(1, f / s.frames)) * (1 - out * 0.05)})`, filter: out > 0 ? `blur(${out * 10}px)` : undefined }}>
      {children}
    </AbsoluteFill>
  );
}

export const Film: React.FC = () => {
  const [handle] = useState(() => delayRender('fonts'));
  useEffect(() => {
    Promise.all([
      document.fonts.load('800 40px Inter'), document.fonts.load('900 40px Inter'), document.fonts.load('600 40px Inter'),
      document.fonts.load('500 40px Inter'), document.fonts.load('700 40px Inter'), document.fonts.load('italic 400 40px "Instrument Serif"'),
      document.fonts.load('700 40px "Noto Sans Bengali"', 'প্রতি মাসে'), document.fonts.load('500 40px "Noto Sans Bengali"', 'প্রতি মাসে'),
    ]).then(() => continueRender(handle)).catch(() => continueRender(handle));
  }, [handle]);
  const scenes = (timeline as any).scenes as any[];
  const accents = scenes.map((s) => ({ from: s.from, color: SCENES[s.id].accent }));
  return (
    <AbsoluteFill style={{ background: C.bg0 }}>
      <Backdrop accents={accents} />
      {scenes.map((s) => {
        const Cmp = SCENES[s.id].C;
        return (
          <Sequence key={s.id} from={s.from} durationInFrames={s.frames + OVERLAP} name={s.id}>
            <SceneCtx.Provider value={s}>
              <SceneFrame s={s}><Cmp /></SceneFrame>
              <Sequence from={Math.round(s.lead * 30)} layout="none">
                <Audio src={staticFile(s.voice)} volume={1} />
              </Sequence>
            </SceneCtx.Provider>
          </Sequence>
        );
      })}
      <Captions scenes={scenes} hide={HIDE} />
      <Audio src={staticFile('music.wav')} volume={1} />
      <Fade total={(timeline as any).frames} />
    </AbsoluteFill>
  );
};

function Fade({ total }: { total: number }) {
  const f = useCurrentFrame();
  const a = 1 - ease(f, 0, 10);
  const b = ease(f, total - 16, total - 1);
  const o = Math.max(a, b);
  return o > 0 ? <AbsoluteFill style={{ background: '#000', opacity: o }} /> : null;
}
