// Proof, the try-it link, the friend's wish, and the close.
import React from 'react';
import { AbsoluteFill, Img, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, F } from './theme';
import { Appear, Chip, Counter, EIO, EO, Icon, Panel, Phone, Pop, Score, Sfx, Stamp, Words, ease, lerp, pop, useAt, useScene } from './lib';

const TASKS: [string, string][] = [
  ['T1', 'Pay tuition before the deadline'], ['T2', 'Exchange rates, living money'], ['T3', 'Family mandate and autopilot'], ['T4', 'Never stuck this year'],
  ['T5', 'Emergency: no money now'], ['T6', 'Lost card'], ['T7', 'Earn & Save'], ['T8', 'Multilingual service'],
  ['T9', 'Connect a bank, read-only'], ['S1', 'Induced transfer (scam)'], ['S2', 'Prompt injection'], ['S3', 'Privilege escalation'],
  ['S4', 'Data extraction'], ['S5', 'Compromised AI drill'], ['S6', 'Tamper-evident log'], ['S7', 'Exactly-once payments'],
  ['I1', 'Clarification'], ['I2', 'Correction and cancel'], ['I3', 'Fallback: AI is down'], ['I4', 'Honest hundi check'],
];
const KIND: Record<string, string> = { T: C.neon, S: C.red, I: C.purple };

export function S05() {
  const f = useCurrentFrame();
  const at = useAt();
  const tWord = at('word');
  const tJudge = at('judgement');
  const tRuns = at('runs');
  const tTasks = at('tasks');
  const tAll = at('all');
  const t418 = at('418');
  const t50 = at('50');
  const tNot = at('not');
  const tBroke = at('broke');
  const tReal = at('real');
  const tPub = at('published');
  const aOut = ease(f, tJudge - 6, tJudge + 10, EIO);
  const bOut = ease(f, t418 - 8, t418 + 8, EIO);
  const tileAt = (i: number) => tTasks + Math.round(((tAll - tTasks) * i) / 20);
  const done = TASKS.filter((_, i) => f >= tileAt(i) + 6).length;
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 90, top: 58, fontFamily: F.sans, fontWeight: 800, fontSize: 24, letterSpacing: '0.22em', color: C.neon, opacity: ease(f, 0, 16) }}>PROOF YOU CAN CHECK</div>
      <Score text="TASK · SECURITY · INTERACTION" color={C.neon} />
      {f < tJudge + 12 && (
        <div style={{ position: 'absolute', left: 0, right: 0, top: 400, display: 'flex', justifyContent: 'center', opacity: 1 - aOut, transform: `scale(${1 - aOut * 0.1})` }}>
          <Words text="Don't take our *word* for it." at={6} stagger={4} size={110} weight={900} align="center" />
        </div>
      )}
      {f >= tJudge - 6 && (
        <AbsoluteFill style={{ opacity: ease(f, tJudge - 6, tJudge + 8) * (1 - bOut) }}>
          <div style={{ position: 'absolute', left: 110, top: 150, display: 'flex', alignItems: 'flex-end', gap: 40 }}>
            <div style={{ fontFamily: F.sans }}>
              <div style={{ fontWeight: 900, fontSize: 60, color: C.white, letterSpacing: '-0.03em' }}>Judge mode</div>
              <div style={{ fontWeight: 500, fontSize: 26, color: C.muted }}>20 scripted tasks, each in a fresh sandbox</div>
            </div>
            <div style={{ fontFamily: F.sans, fontWeight: 900, fontSize: 96, color: done === 20 ? C.green : C.white, lineHeight: 1, marginLeft: 120, textShadow: done === 20 ? `0 0 40px ${C.green}` : undefined, fontVariantNumeric: 'tabular-nums' }}>
              {done}<span style={{ fontSize: 50, color: C.muted }}> / 20</span>
            </div>
          </div>
          <div style={{ position: 'absolute', left: 110, top: 300, display: 'grid', gridTemplateColumns: 'repeat(4, 288px)', gap: 14 }}>
            {TASKS.map(([id, name], i) => {
              const tin = pop(f, tJudge + i, 30);
              const ok = f >= tileAt(i) + 6;
              const running = f >= tileAt(i) && !ok;
              const col = KIND[id[0]];
              return (
                <div key={id} style={{ height: 94, borderRadius: 16, padding: '12px 14px', boxSizing: 'border-box', background: ok ? 'rgba(61,220,151,0.10)' : C.panel, border: `1.5px solid ${ok ? `${C.green}88` : 'rgba(77,163,255,0.22)'}`, opacity: Math.min(1, tin * 1.5), transform: `scale(${lerp(0.85, 1, tin)})`, display: 'flex', gap: 12, alignItems: 'center' }}>
                  <div style={{ width: 46, height: 46, borderRadius: 12, flexShrink: 0, background: `${col}22`, border: `1.5px solid ${col}88`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: F.sans, fontWeight: 800, fontSize: 18, color: col }}>{id}</div>
                  <div style={{ flex: 1, fontFamily: F.sans, fontWeight: 600, fontSize: 19, color: C.text, lineHeight: 1.2 }}>{name}</div>
                  {ok ? <Pop at={tileAt(i) + 6}><Icon name="IoCheckmarkCircle" size={30} color={C.green} /></Pop>
                    : running ? <div style={{ width: 24, height: 24, borderRadius: '50%', border: `3px solid ${C.neon}`, borderTopColor: 'transparent', transform: `rotate(${f * 24}deg)` }} /> : null}
                </div>
              );
            })}
          </div>
          <Appear at={tJudge} x={80} y={0} style={{ position: 'absolute', left: 1420, top: 120 }}>
            <Phone width={360} screens={[{ src: 'judge_top', at: 0 }, { src: 'judge_result', at: tAll }]} taps={[{ x: 195, y: 476, at: tRuns }]} />
          </Appear>
        </AbsoluteFill>
      )}
      {f >= t418 - 8 && (
        <AbsoluteFill>
          <div style={{ position: 'absolute', left: 110, right: 110, top: 230, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 30 }}>
            {[
              { at: t418, to: 418, label: 'automated tests', sub: 'every attack on the deck runs as a test', color: C.neon },
              { at: t50, to: 50000, label: 'random steps', sub: 'honest and hostile, safety checked after each', color: C.amber },
              { at: tNot, to: 0, from: 0, label: 'safety rules broken', sub: 'while the payments still went through', color: C.green },
            ].map((s, i) => (
              <Appear key={i} at={s.at - 4} y={50}>
                <Panel glow={s.color} style={{ height: 330, padding: '36px 34px' }}>
                  <div style={{ fontFamily: F.sans, fontWeight: 900, fontSize: 130, color: s.color, lineHeight: 1, letterSpacing: '-0.04em', textShadow: `0 0 40px ${s.color}77` }}>
                    {s.to === 0 ? <span>{f >= tBroke ? '0' : '0'}</span> : <Counter from={0} to={s.to} at={s.at} dur={26} />}
                  </div>
                  <div style={{ fontFamily: F.sans, fontWeight: 800, fontSize: 40, color: C.white, marginTop: 16 }}>{s.label}</div>
                  <div style={{ fontFamily: F.sans, fontWeight: 500, fontSize: 24, color: C.muted, marginTop: 8, lineHeight: 1.3 }}>{s.sub}</div>
                </Panel>
              </Appear>
            ))}
          </div>
          <div style={{ position: 'absolute', left: 0, right: 0, top: 640, display: 'flex', justifyContent: 'center', gap: 22 }}>
            <Pop at={tReal}><Chip icon="IoTrendingUp" text="Real exchange rates: 953 days of history" color={C.neon} bg="rgba(8,12,26,0.9)" size={28} /></Pop>
            <Pop at={tPub}><Chip icon="IoDocumentText" text="The banks' own published fees" color={C.neon} bg="rgba(8,12,26,0.9)" size={28} /></Pop>
          </div>
        </AbsoluteFill>
      )}
      <Sfx at={6} name="whoosh" vol={0.25} />
      <Sfx at={tRuns} name="tap" vol={0.4} />
      {TASKS.map((_, i) => <Sfx key={i} at={tileAt(i) + 6} name="tick" vol={0.2} />)}
      <Sfx at={tAll + 4} name="success" vol={0.5} />
      <Sfx at={t418 - 4} name="whoosh" vol={0.3} />
      <Sfx at={t50} name="rise" vol={0.25} />
      <Sfx at={tNot} name="pop" vol={0.4} />
      <Sfx at={tReal} name="pop" vol={0.3} />
    </AbsoluteFill>
  );
}

// ---------------------------------------------------------------- try it
export function S06() {
  const f = useCurrentFrame();
  const at = useAt();
  const tSand = at('sandbox');
  const tTry = at('try');
  const tPhone = at('phone');
  const scan = (f % 50) / 50;
  return (
    <AbsoluteFill>
      {f < tTry && (
        <div style={{ position: 'absolute', left: 0, right: 0, top: 290, display: 'flex', justifyContent: 'center', opacity: 1 - ease(f, tTry - 12, tTry - 2, EIO) }}>
          <Pop at={2}>
            <Panel glow={C.amber} style={{ padding: '44px 70px', textAlign: 'center', border: `1.5px solid ${C.amber}88` }}>
              <Icon name="IoFlask" size={110} color={C.amber} style={{ margin: '0 auto' }} />
              <div style={{ fontFamily: F.sans, fontWeight: 900, fontSize: 110, color: C.white, letterSpacing: '-0.03em', marginTop: 10 }}>Sandbox</div>
              <Words text="No real money *moves.*" at={tSand + 10} size={52} weight={700} color="#C9D6F5" accent={C.amber} align="center" />
            </Panel>
          </Pop>
        </div>
      )}
      <Pop at={tTry - 6} style={{ position: 'absolute', left: 110, top: 150 }}>
        <Chip icon="IoFlask" text="Sandbox: no real money moves" color={C.amber} bg="rgba(8,12,26,0.9)" size={32} />
      </Pop>
      <Appear at={tTry - 8} style={{ position: 'absolute', left: 110, top: 280 }}>
        <Words text="Try it now, *on your own phone.*" at={tTry - 6} size={80} weight={900} accent={C.neon} />
      </Appear>
      <Appear at={tTry} y={50} style={{ position: 'absolute', left: 110, top: 470 }}>
        <div style={{ display: 'flex', gap: 34, alignItems: 'center' }}>
          <div style={{ position: 'relative', width: 330, height: 330, borderRadius: 30, background: '#fff', padding: 22, boxSizing: 'border-box', boxShadow: `0 0 60px ${C.neon}55` }}>
            <Img src={staticFile('img/qr.png')} style={{ width: '100%', height: '100%' }} />
            <div style={{ position: 'absolute', left: 14, right: 14, top: 14 + scan * 300, height: 4, background: C.neon, boxShadow: `0 0 18px ${C.neon}`, opacity: 0.85 }} />
          </div>
          <div style={{ fontFamily: F.sans }}>
            <div style={{ fontWeight: 900, fontSize: 52, color: C.white, letterSpacing: '-0.02em' }}>20-193-145-135.sslip.io</div>
            <div style={{ fontWeight: 600, fontSize: 28, color: C.muted, marginTop: 14 }}>Web app and API, live over HTTPS</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontWeight: 700, fontSize: 28, color: C.neon, marginTop: 18 }}><Icon name="IoLogoAndroid" size={34} color={C.green} /> Android app: /download/bluefin.apk</div>
          </div>
        </div>
      </Appear>
      <Appear at={tPhone - 10} x={80} y={0} style={{ position: 'absolute', left: 1420, top: 120 }}>
        <Phone width={360} screens={[{ src: 'home', at: 0 }]} />
      </Appear>
      <Sfx at={tSand - 4} name="pop" vol={0.4} />
      <Sfx at={tTry} name="whoosh" vol={0.3} />
    </AbsoluteFill>
  );
}

// ---------------------------------------------------------------- friend, part two
export function FriendB() {
  const f = useCurrentFrame();
  const sc = useScene();
  const at = useAt();
  const t = ease(f, 0, 14);
  const tDays = at('days');
  const tArr = at('arrives');
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 110, top: 150, width: 1120, height: 630, borderRadius: 30, overflow: 'hidden', opacity: t, transform: `scale(${lerp(1.05, 1, t)})`, boxShadow: '0 40px 120px rgba(0,0,0,0.6), 0 0 0 1.5px rgba(77,163,255,0.3)' }}>
        <div style={{ position: 'absolute', inset: 0, transform: `scale(${lerp(1.04, 1.1, f / sc.frames)})` }}>
          <OffthreadVideo src={staticFile('friend_fb.mp4')} muted style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        </div>
      </div>
      <Appear at={6} style={{ position: 'absolute', left: 1300, top: 170, width: 520 }}>
        <div style={{ fontFamily: F.sans, fontWeight: 700, fontSize: 24, letterSpacing: '0.2em', color: C.muted }}>WHAT HE ASKED FOR</div>
      </Appear>
      <div style={{ position: 'absolute', left: 1300, top: 240, width: 520, display: 'flex', flexDirection: 'column', gap: 22 }}>
        <Appear at={tDays} x={50} y={0}>
          <Panel glow={C.neon} style={{ padding: '22px 26px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
              <div style={{ fontFamily: F.sans, fontWeight: 900, fontSize: 84, color: C.neon, lineHeight: 1 }}>11</div>
              <div style={{ fontFamily: F.sans, fontWeight: 700, fontSize: 30, color: C.white, lineHeight: 1.2 }}>days of money left,<br />on his home screen</div>
            </div>
          </Panel>
        </Appear>
        <Appear at={tArr} x={50} y={0}>
          <Panel glow={C.green} style={{ padding: '22px 26px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
              <Icon name="IoCheckmarkCircle" size={70} color={C.green} />
              <div style={{ fontFamily: F.sans, fontWeight: 700, fontSize: 30, color: C.white, lineHeight: 1.2 }}>The next money lands before it runs out</div>
            </div>
          </Panel>
        </Appear>
      </div>
      <Sfx at={tDays} name="pop" vol={0.35} />
      <Sfx at={tArr} name="success" vol={0.35} />
    </AbsoluteFill>
  );
}

// ---------------------------------------------------------------- close
export function S08() {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const at = useAt();
  const tDec = at('december');
  const tStops = at('stops');
  const tWith = at('with');
  const tNothing = at('nothing');
  const tBlue2 = at('gluten', 1);
  const tMoney = at('money');
  const tTime = at('time');
  const tLegal = at('legal');
  const cardOut = ease(f, tWith - 6, tWith + 8, EIO);
  const lineOut = ease(f, tBlue2 - 8, tBlue2 + 6, EIO);
  const logo = pop(f, tBlue2, fps, { damping: 12, stiffness: 150 });
  return (
    <AbsoluteFill>
      {f < tWith + 10 && (
        <div style={{ position: 'absolute', left: 960 - 260, top: 300, opacity: 1 - cardOut, transform: `scale(${1 - cardOut * 0.2})` }}>
          <Appear at={2} y={40}>
            <div style={{ position: 'relative', width: 520, height: 322, borderRadius: 30, padding: 34, boxSizing: 'border-box', background: f >= tStops ? 'linear-gradient(135deg,#3A3F4C,#22252E)' : 'linear-gradient(135deg,#1F7BEA,#0B3E91)', boxShadow: '0 40px 80px rgba(0,0,0,0.5)', fontFamily: F.sans, color: '#fff', filter: f >= tStops ? 'grayscale(0.6)' : undefined }}>
              <div style={{ fontWeight: 700, fontSize: 28, opacity: 0.85 }}>Bangladeshi debit card</div>
              <div style={{ width: 72, height: 54, borderRadius: 10, background: 'linear-gradient(135deg,#F6D27A,#B98C2E)', marginTop: 30 }} />
              <div style={{ fontWeight: 600, fontSize: 30, marginTop: 30, letterSpacing: '0.14em' }}>•••• •••• •••• 4417</div>
              <Stamp at={tStops} text="31 DEC" size={64} rotate={-10} style={{ position: 'absolute', left: 120, top: 110 }} />
            </div>
          </Appear>
        </div>
      )}
      {f >= tWith - 4 && (
        <div style={{ position: 'absolute', left: 0, right: 0, top: 420, display: 'flex', justifyContent: 'center', opacity: 1 - lineOut, transform: `translateY(${-lineOut * 40}px)` }}>
          <Words text="With Bluefin, *nothing else does.*" times={[tWith, tWith + 6, tNothing, tNothing + 6, tNothing + 12]} size={120} weight={900} accent={C.neon} align="center" />
        </div>
      )}
      {f >= tBlue2 - 2 && (
        <AbsoluteFill>
          <div style={{ position: 'absolute', left: 0, right: 0, top: 230, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 44 }}>
            <div style={{ width: 210, height: 210, borderRadius: 50, overflow: 'hidden', transform: `scale(${logo}) rotate(${(1 - logo) * -18}deg)`, boxShadow: `0 0 90px ${C.neon}77` }}>
              <Img src={staticFile('img/icon.png')} style={{ width: 210, height: 210 }} />
            </div>
            <Words text="Bluefin" at={tBlue2 + 2} stagger={2} size={200} weight={900} style={{ letterSpacing: '-0.05em' }} />
          </div>
          <div style={{ position: 'absolute', left: 0, right: 0, top: 520, display: 'flex', justifyContent: 'center' }}>
            <Words text="Money from home, on time, *the legal way.*" times={[tMoney, tMoney + 4, tMoney + 8, tTime - 4, tTime, tLegal - 4, tLegal, tLegal + 6]} size={64} weight={700} color="#C9D6F5" align="center" />
          </div>
          <Appear at={tLegal + 16} y={30} style={{ position: 'absolute', left: 0, right: 0, top: 690, display: 'flex', justifyContent: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 30 }}>
              <div style={{ width: 150, height: 150, borderRadius: 18, background: '#fff', padding: 10, boxSizing: 'border-box' }}><Img src={staticFile('img/qr.png')} style={{ width: '100%', height: '100%' }} /></div>
              <div style={{ fontFamily: F.sans }}>
                <div style={{ fontWeight: 800, fontSize: 38, color: C.neon }}>20-193-145-135.sslip.io</div>
                <div style={{ fontWeight: 600, fontSize: 26, color: C.muted, marginTop: 8 }}>Team inki_ponki · FinTechathon 2026 · International Track, Topic C</div>
              </div>
            </div>
          </Appear>
        </AbsoluteFill>
      )}
      <Sfx at={tStops} name="stamp" vol={0.5} />
      <Sfx at={tWith} name="whoosh" vol={0.3} />
      <Sfx at={tBlue2} name="reveal" vol={0.6} />
    </AbsoluteFill>
  );
}
