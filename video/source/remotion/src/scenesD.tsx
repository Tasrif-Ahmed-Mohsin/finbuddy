// Act and Prove: the student's Shield, four months in fast-forward, the receipt, and the log anchored on chain.
import React from 'react';
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from 'remotion';
import { C, F } from './theme';
import { Appear, Chip, Counter, EIO, EO, Icon, Kicker, Panel, Phone, Pop, Ring, Score, Sfx, Shell, Stamp, Words, clamp, ease, lerp, pop, useAt } from './lib';

// ---------------------------------------------------------------- 3 · Act: the student's own Shield
export function S4g() {
  const f = useCurrentFrame();
  const at = useAt();
  const tChina = at('china');
  const tApproval = at('approval');
  const tApproved = at('approved');
  const tJob = at('job');
  const tSigns = at('signs');
  const tKeep = at('keep');
  const tHalf = at('half');
  const tDays = at('days');
  const tArrive = at('arrive');
  const split = ease(f, tHalf, tHalf + 16, EIO);
  const drop = ease(f, tHalf + 12, tHalf + 30, EIO);
  const fill = interpolate(f, [tHalf + 26, tArrive], [0, 0.5], { ...clamp, easing: EIO });
  return (
    <AbsoluteFill>
      <Kicker step="act" />
      <Score text="INNOVATION & INTERACTION · 30%" color={C.green} />
      <Appear at={tChina - 6} style={{ position: 'absolute', left: 110, top: 150, width: 900 }}>
        <Panel glow={C.amber} style={{ padding: '28px 32px' }}>
          <div style={{ display: 'flex', gap: 22, alignItems: 'flex-start' }}>
            <div style={{ width: 84, height: 84, borderRadius: 22, background: `${C.amber}22`, border: `2px solid ${C.amber}88`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}><Icon name="IoSchool" size={48} color={C.amber} /></div>
            <div style={{ fontFamily: F.sans }}>
              <div style={{ fontWeight: 700, fontSize: 22, letterSpacing: '0.18em', color: C.amber }}>THE RULE IN CHINA</div>
              <div style={{ fontWeight: 800, fontSize: 40, color: C.white, lineHeight: 1.2, marginTop: 6 }}>A student may work only with the university's approval</div>
            </div>
          </div>
          <Stamp at={tApproval} text="APPROVAL FIRST" color={C.green} size={36} rotate={-6} style={{ position: 'absolute', right: -10, top: -18 }} />
        </Panel>
      </Appear>
      <div style={{ position: 'absolute', left: 110, top: 470, width: 900, display: 'flex', flexDirection: 'column', gap: 18 }}>
        <Appear at={tApproved - 8} x={-60} y={0}>
          <Shell style={{ display: 'flex', alignItems: 'center', gap: 18, padding: '20px 26px' }}>
            <Icon name="IoLibrary" size={40} color="#0062CC" />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 800, fontSize: 30 }}>Campus library assistant</div>
              <div style={{ fontWeight: 600, fontSize: 22, color: '#5F6470' }}>¥1,500 a month · approved by the university</div>
            </div>
            <Pop at={tApproved + 4}><Chip icon="IoCheckmarkCircle" text="Counted" color="#17703A" bg="#DDF3E6" textColor="#17703A" size={22} /></Pop>
          </Shell>
        </Appear>
        <Appear at={tJob - 2} x={-60} y={0}>
          <Shell style={{ display: 'flex', alignItems: 'center', gap: 18, padding: '20px 26px', opacity: 0.75 }}>
            <Icon name="IoBicycle" size={40} color="#8A909C" />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 800, fontSize: 30, color: '#5F6470', textDecoration: f > tJob + 8 ? 'line-through' : undefined }}>Off-campus delivery job</div>
              <div style={{ fontWeight: 600, fontSize: 22, color: '#8A909C' }}>no approval</div>
            </div>
            <Pop at={tJob + 8}><Chip icon="IoCloseCircle" text="Never counted" color="#C42B1C" bg="#FBE1DE" textColor="#C42B1C" size={22} /></Pop>
          </Shell>
        </Appear>
      </div>
      {/* the Shield */}
      <Appear at={tSigns - 8} x={60} y={0} style={{ position: 'absolute', left: 1170, top: 150, width: 640 }}>
        <Panel glow={C.green} style={{ padding: '26px 30px', textAlign: 'center' }}>
          <div style={{ fontFamily: F.sans, fontWeight: 700, fontSize: 22, letterSpacing: '0.18em', color: C.green }}>THE STUDENT'S OWN RULE</div>
          <div style={{ fontFamily: F.sans, fontWeight: 800, fontSize: 38, color: C.white, marginTop: 8 }}>Keep half of every pay</div>
          <Pop at={tSigns + 6}><div style={{ marginTop: 14, display: 'inline-flex' }}><Chip icon="IoFingerPrint" text="Signed by the student only" color={C.green} size={22} /></div></Pop>
          <div style={{ position: 'relative', height: 420, marginTop: 10 }}>
            {f >= tKeep - 6 && (
              <>
                {[0, 1].map((i) => {
                  const dx = (i ? 1 : -1) * 120 * split;
                  const dy = i === 0 ? drop * 190 : drop * 40;
                  const op = i === 0 ? 1 - ease(f, tHalf + 26, tHalf + 32) : 1 - ease(f, tHalf + 40, tHalf + 52);
                  return (
                    <div key={i} style={{ position: 'absolute', left: 290 - 60 + dx, top: 10 + dy, width: 120, height: 120, borderRadius: '50%', background: `radial-gradient(circle at 35% 30%, #FFE08A, ${C.amber} 60%, #C48A16)`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: F.sans, fontWeight: 900, fontSize: split > 0.5 ? 30 : 34, color: '#3A2600', opacity: op * ease(f, tKeep - 6, tKeep + 4), clipPath: split < 0.05 ? undefined : i === 0 ? 'inset(0 0 0 0 round 60px)' : undefined, boxShadow: `0 0 30px ${C.amber}88` }}>
                      {split > 0.5 ? '¥750' : '¥1,500'}
                    </div>
                  );
                })}
                <Pop at={tHalf + 30} style={{ position: 'absolute', right: 30, top: 70 }}><Chip icon="IoCart" text="To spend" color={C.neon} size={20} /></Pop>
              </>
            )}
            <div style={{ position: 'absolute', left: 290 - 120, top: 170, width: 240, height: 240 }}>
              <svg width={240} height={240} viewBox="0 0 512 512" style={{ position: 'absolute' }}>
                <defs>
                  <clipPath id="sh"><path d="M256 32 L448 96 V240 C448 360 368 440 256 480 C144 440 64 360 64 240 V96 Z" /></clipPath>
                </defs>
                <path d="M256 32 L448 96 V240 C448 360 368 440 256 480 C144 440 64 360 64 240 V96 Z" fill="rgba(61,220,151,0.08)" stroke={C.green} strokeWidth={14} />
                <rect x={0} y={480 - 448 * fill} width={512} height={512} fill={C.green} opacity={0.75} clipPath="url(#sh)" />
              </svg>
              <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: F.sans, fontWeight: 900, color: C.white }}>
                <div style={{ fontSize: 44 }}>¥<Counter from={0} to={3000} at={tHalf + 26} dur={Math.max(20, tArrive - tHalf - 26)} /></div>
                <div style={{ fontSize: 20, fontWeight: 600, color: '#C9F5E2' }}>of ¥6,000</div>
              </div>
            </div>
          </div>
          <Appear at={tDays}><div style={{ fontFamily: F.serif, fontStyle: 'italic', fontSize: 38, color: C.text }}>for the days money from home cannot arrive</div></Appear>
        </Panel>
      </Appear>
      <Sfx at={tApproval} name="stamp" vol={0.4} />
      <Sfx at={tApproved + 4} name="success" vol={0.35} />
      <Sfx at={tJob + 8} name="alert" vol={0.25} />
      <Sfx at={tSigns + 6} name="scan" vol={0.3} />
      <Sfx at={tHalf} name="coin" vol={0.5} />
      <Sfx at={tHalf + 26} name="rise" vol={0.25} />
    </AbsoluteFill>
  );
}

// ---------------------------------------------------------------- 3 · Act: four months pass
const T0 = Date.UTC(2026, 9, 12);
const DAY = 86400000;
const dayOf = (s: string) => Math.round((Date.parse(`${s}T00:00:00Z`) - T0) / DAY);
const fmt = (d: number) => new Date(T0 + d * DAY).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
// The autopilot's transfers in the four-month story run (sandbox log): sent, landed, yuan, taka.
const SENDS = [
  { sent: '2026-10-12', lands: '2026-10-19', cny: '¥6,100', bdt: 116598 },
  { sent: '2026-11-12', lands: '2026-11-19', cny: '¥5,500', bdt: 105492 },
  { sent: '2026-12-15', lands: '2026-12-22', cny: '¥5,800', bdt: 111045 },
  { sent: '2027-01-14', lands: '2027-01-21', cny: '¥5,300', bdt: 101674 },
  { sent: '2027-02-17', lands: '2027-02-24', cny: '¥6,000', bdt: 114747 },
];

export function S4h() {
  const f = useCurrentFrame();
  const at = useAt();
  const tFour = at('four');
  const tDec = at('december');
  const tSpring = at('spring');
  const tEarly = at('early');
  const tInside = at('inside');
  const tLimit = at('limit');
  const tZero = at('zero');
  const day = interpolate(f, [tFour, tDec, tSpring + 20, tEarly, tZero - 10], [0, dayOf('2026-12-31'), dayOf('2027-02-08'), dayOf('2027-02-17'), dayOf('2027-02-21')], clamp);
  const X0 = 170;
  const X1 = 1750;
  const SPAN = dayOf('2027-02-28');
  const px = (d: number) => X0 + ((X1 - X0) * d) / SPAN;
  const TRACK = 760;
  const LIMIT_H = 330; // px for ৳1,20,000
  const months = [['Oct', '2026-10-12'], ['Nov', '2026-11-01'], ['Dec', '2026-12-01'], ['Jan', '2027-01-01'], ['Feb', '2027-02-01']];
  const limitIn = ease(f, tInside - 10, tInside + 10, EIO);
  return (
    <AbsoluteFill>
      <Kicker step="act" />
      <Score text="TASK COMPLETION · 40%" color={C.green} />
      <Appear at={2} style={{ position: 'absolute', left: 0, right: 0, top: 120, textAlign: 'center' }}>
        <div style={{ fontFamily: F.sans, fontWeight: 700, fontSize: 24, letterSpacing: '0.24em', color: C.muted }}>SANDBOX CLOCK · FOUR MONTHS</div>
        <div style={{ fontFamily: F.sans, fontWeight: 900, fontSize: 92, color: C.white, letterSpacing: '-0.03em', fontVariantNumeric: 'tabular-nums' }}>{fmt(Math.floor(day))}</div>
      </Appear>
      <svg width={1920} height={1080} style={{ position: 'absolute' }}>
        <line x1={X0} y1={TRACK} x2={X1} y2={TRACK} stroke="rgba(142,154,192,0.35)" strokeWidth={6} strokeLinecap="round" />
        <line x1={X0} y1={TRACK} x2={px(day)} y2={TRACK} stroke={C.neon} strokeWidth={6} strokeLinecap="round" style={{ filter: `drop-shadow(0 0 10px ${C.neon})` }} />
        {/* Spring Festival: Chinese banks closed */}
        <rect x={px(dayOf('2027-02-05'))} y={TRACK - 300} width={px(dayOf('2027-02-14')) - px(dayOf('2027-02-05'))} height={300} fill={C.red} opacity={ease(f, tSpring - 4, tSpring + 10) * 0.22} />
        {/* card stops */}
        <line x1={px(dayOf('2026-12-31'))} y1={TRACK - 330} x2={px(dayOf('2026-12-31'))} y2={TRACK + 20} stroke={C.amber} strokeWidth={4} strokeDasharray="8 8" opacity={ease(f, tDec - 6, tDec + 6)} />
        {/* the signed limit */}
        <line x1={X0} y1={TRACK - LIMIT_H} x2={X0 + (X1 - X0) * limitIn} y2={TRACK - LIMIT_H} stroke={C.green} strokeWidth={4} strokeDasharray="14 10" />
      </svg>
      {months.map(([m, d]) => (
        <div key={m} style={{ position: 'absolute', left: px(dayOf(d)) - 40, top: TRACK + 26, width: 80, textAlign: 'center', fontFamily: F.sans, fontWeight: 700, fontSize: 26, color: C.muted }}>{m}</div>
      ))}
      <Pop at={tDec - 4} style={{ position: 'absolute', left: px(dayOf('2026-12-31')) - 330, top: 288 }}><Chip icon="IoCard" text="Card stops abroad" color={C.amber} bg="rgba(8,12,26,0.9)" size={22} /></Pop>
      <Pop at={tSpring} style={{ position: 'absolute', left: px(dayOf('2027-02-05')) - 120, top: 288 }}><Chip icon="IoSparkles" text="Spring Festival: banks closed" color={C.red} bg="rgba(8,12,26,0.9)" size={22} /></Pop>
      {limitIn > 0 && <div style={{ position: 'absolute', left: 640, top: TRACK - LIMIT_H - 52, fontFamily: F.sans, fontWeight: 800, fontSize: 24, color: C.green, opacity: limitIn }}>Signed limit: ৳1,20,000 a month</div>}
      {SENDS.map((s, i) => {
        const sentD = dayOf(s.sent);
        if (day < sentD) return null;
        const k0 = interpolate(day, [sentD, sentD + 4], [0, 1], clamp);
        const h = (s.bdt / 120000) * LIMIT_H * k0;
        const x = px(dayOf(s.lands));
        return (
          <div key={i}>
            <div style={{ position: 'absolute', left: x - 22, top: TRACK - h, width: 44, height: h, borderRadius: '12px 12px 4px 4px', background: `linear-gradient(180deg, ${C.green}, ${C.green}55)`, boxShadow: `0 0 26px ${C.green}66` }} />
            <div style={{ position: 'absolute', left: x - 70, top: TRACK - h - 46, width: 140, display: 'flex', justifyContent: 'center', opacity: k0 }}><span style={{ fontFamily: F.sans, fontWeight: 800, fontSize: 24, color: C.white, background: 'rgba(8,12,26,0.92)', borderRadius: 10, padding: '2px 10px', border: `1px solid ${C.green}55` }}>{s.cny}</span></div>
          </div>
        );
      })}
      <div style={{ position: 'absolute', left: px(day) - 3, top: TRACK - 340, width: 6, height: 360, borderRadius: 3, background: C.white, boxShadow: `0 0 18px ${C.neon}` }} />
      <Pop at={tEarly} style={{ position: 'absolute', left: X0, top: TRACK + 90 }}><Chip icon="IoTime" text="Each transfer lands before the money runs low" color={C.green} bg="rgba(8,12,26,0.9)" size={24} /></Pop>
      <Pop at={tZero - 4} style={{ position: 'absolute', right: 110, top: 128 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 18, fontFamily: F.sans }}>
          <span style={{ fontWeight: 900, fontSize: 130, color: C.green, lineHeight: 1, textShadow: `0 0 50px ${C.green}` }}>0</span>
          <span style={{ fontWeight: 800, fontSize: 38, color: C.white }}>days without money</span>
        </div>
      </Pop>
      <Sfx at={tFour} name="rewind" vol={0.35} />
      <Sfx at={tDec} name="alert" vol={0.3} />
      <Sfx at={tSpring} name="alert" vol={0.25} />
      <Sfx at={tInside} name="swipe" vol={0.3} />
      <Sfx at={tZero - 4} name="success" vol={0.5} />
    </AbsoluteFill>
  );
}

// ---------------------------------------------------------------- 4 · Prove: a receipt for every taka
export function S4i() {
  const f = useCurrentFrame();
  const at = useAt();
  const tReceipt = at('receipt');
  const tAllowed = at('allowed');
  const tTracking = at('tracking');
  const tBooks = at('books');
  const tBalance = at('balance');
  const up = ease(f, tReceipt - 14, tReceipt + 16, EO);
  const row = (label: string, value: string, hl: number, icon: string) => {
    const on = f >= hl;
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '14px 16px', borderRadius: 14, background: on ? '#E9E2FB' : 'transparent', border: `2px solid ${on ? C.purple : 'transparent'}`, marginTop: 8 }}>
        <Icon name={icon} size={30} color={on ? '#7B4FC9' : '#8A909C'} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 19, fontWeight: 700, color: '#8A909C', letterSpacing: '0.06em' }}>{label}</div>
          <div style={{ fontSize: 27, fontWeight: 700, color: C.ink, fontVariantNumeric: 'tabular-nums' }}>{value}</div>
        </div>
        {on && <Pop at={hl}><Icon name="IoCheckmarkCircle" size={32} color="#17703A" /></Pop>}
      </div>
    );
  };
  return (
    <AbsoluteFill>
      <Kicker step="prove" />
      <Score text="SECURITY & COMPLIANCE · 30%" color={C.purple} />
      <Appear at={2} style={{ position: 'absolute', left: 110, top: 150 }}><Words text="A receipt for *every taka.*" at={4} size={60} accent={C.purple} /></Appear>
      <div style={{ position: 'absolute', left: 230, top: 120, width: 820, height: 790, overflow: 'hidden', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}>
        <div style={{ transform: `translateY(${(1 - up) * 790}px)` }}>
          <Shell style={{ padding: '30px 34px', borderRadius: 26 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <div style={{ fontWeight: 800, fontSize: 22, letterSpacing: '0.2em', color: '#7B4FC9' }}>RECEIPT</div>
              <div style={{ fontWeight: 600, fontSize: 20, color: '#8A909C' }}>Log entry #65</div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginTop: 10 }}>
              <div style={{ fontWeight: 800, fontSize: 34 }}>Living money → his own account</div>
              <div style={{ fontWeight: 900, fontSize: 46 }}>¥6,000</div>
            </div>
            <div style={{ fontWeight: 600, fontSize: 22, color: '#5F6470', marginTop: 4 }}>৳1,14,747 · sent 17 Feb 2027 · arrives 24 Feb</div>
            <div style={{ height: 2, background: '#D6DAE2', margin: '18px 0 6px' }} />
            {row('WHO ALLOWED IT', 'The family mandate · Parent + Student', tAllowed, 'IoPeople')}
            {row('BANK TRACKING NUMBER (UETR)', '468754de-64f2-…', tTracking, 'IoLink')}
            <div style={{ marginTop: 8, padding: '14px 16px', borderRadius: 14, background: f >= tBooks ? '#E9E2FB' : 'transparent', border: `2px solid ${f >= tBooks ? C.purple : 'transparent'}` }}>
              <div style={{ fontSize: 19, fontWeight: 700, color: '#8A909C', letterSpacing: '0.06em' }}>DOUBLE-ENTRY BOOKS</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 8, fontSize: 24, fontWeight: 700 }}>
                <div>Debit: parent's taka account<br /><span style={{ fontSize: 30, fontWeight: 900 }}>৳1,14,747.20</span></div>
                <div>Credit: transfer to China<br /><span style={{ fontSize: 30, fontWeight: 900 }}>৳1,14,747.20</span></div>
              </div>
              {f >= tBalance && <Pop at={tBalance}><div style={{ marginTop: 10, display: 'inline-flex' }}><Chip icon="IoCheckmarkCircle" text="Balanced to the last taka" color="#17703A" bg="#DDF3E6" textColor="#17703A" size={22} /></div></Pop>}
            </div>
          </Shell>
        </div>
      </div>
      <div style={{ position: 'absolute', left: 200, top: 905, width: 880, height: 14, borderRadius: 7, background: '#05070C', boxShadow: `0 0 30px ${C.purple}, inset 0 0 6px ${C.purple}` }} />
      <Appear at={6} x={80} y={0} style={{ position: 'absolute', left: 1330, top: 120 }}>
        <Phone width={370} screens={[{ src: 'proof_receipts', at: 0 }]} />
      </Appear>
      <Sfx at={tReceipt - 14} name="print" vol={0.4} />
      <Sfx at={tAllowed} name="tick" vol={0.35} />
      <Sfx at={tTracking} name="tick" vol={0.35} />
      <Sfx at={tBalance} name="success" vol={0.4} />
    </AbsoluteFill>
  );
}

// ---------------------------------------------------------------- 4 · Prove: the tamper-evident log, anchored on FISCO BCOS
// The last six entries of the anchored four-month evidence log (docs/evidence/sandbox_operation_log.jsonl).
const BLOCKS = [
  { n: 250, ev: 'clock advanced', v: '19 Feb', h: '3e3f…b2c4' },
  { n: 251, ev: 'clock advanced', v: '20 Feb', h: '4a9f…d0cf' },
  { n: 252, ev: 'spending logged', v: '¥175', h: '9b72…eec5' },
  { n: 253, ev: 'clock advanced', v: '21 Feb', h: '3473…0561' },
  { n: 254, ev: 'crisis tested', v: '4 weeks', h: 'f230…9aa6' },
  { n: 255, ev: 'passport issued', v: 'head', h: 'ea98…bc2d' },
];
const EDITED = 2;

export function S4j() {
  const f = useCurrentFrame();
  const at = useAt();
  const tEvery = at('everything');
  const tFinger = at('fingerprint');
  const tFisco = at('fiscal');
  const tChain = at('blockchain');
  const tChange = at('change');
  const tEntry = at('entry');
  const tMatch = at('matches');
  const BW = 252;
  const GAP = 32;
  const X0 = 110;
  const Y = 600;
  const bx = (i: number) => X0 + i * (BW + GAP);
  const flyT = ease(f, tFinger + 4, tFinger + 30, EIO);
  const target = { x: 1260, y: 210 };
  const head = { x: bx(5) + BW / 2, y: Y };
  const broken = (i: number) => i > EDITED && f >= tEntry + 6 + (i - EDITED - 1) * 4;
  const edited = f >= tChange + 10;
  const cursorT = ease(f, tChange - 14, tChange + 4, EIO);
  return (
    <AbsoluteFill>
      <Kicker step="prove" />
      <Score text="CHALLENGE BONUS · ON-CHAIN" color={C.purple} />
      <Appear at={2} style={{ position: 'absolute', left: 110, top: 150 }}>
        <Words text="A log *no one can quietly edit.*" at={4} size={60} accent={C.purple} />
      </Appear>
      {/* FISCO BCOS anchor */}
      <Appear at={tFinger + 18} x={60} y={0} style={{ position: 'absolute', left: 1150, top: 150, width: 660 }}>
        <Panel glow={C.purple} style={{ padding: '22px 26px', border: `1.5px solid ${f >= tMatch ? C.red : C.purple}88` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ width: 70, height: 70, borderRadius: 18, background: `${C.purple}22`, border: `2px solid ${C.purple}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name="IoCube" size={42} color={C.purple} /></div>
            <div style={{ fontFamily: F.sans }}>
              <div style={{ fontWeight: 900, fontSize: 34, color: C.white }}>FISCO BCOS</div>
              <div style={{ fontWeight: 600, fontSize: 21, color: C.muted }}>WeBank's open-source blockchain · 4-node chain</div>
            </div>
          </div>
          <div style={{ fontFamily: 'Consolas, monospace', fontSize: 21, color: '#C9D6F5', marginTop: 14, lineHeight: 1.5 }}>
            Block 2 · tx 0x07311c7a…689d<br />log head #255 · ea9870cd…bc2d
          </div>
          <div style={{ marginTop: 12, height: 44 }}>
            {f >= tMatch ? <Pop at={tMatch}><Chip icon="IoCloseCircle" text="Changed log: no longer matches" color={C.red} size={22} /></Pop>
              : f >= tChain ? <Pop at={tChain}><Chip icon="IoCheckmarkCircle" text="Checked live: 6 of 6 match" color={C.green} size={22} /></Pop> : null}
          </div>
        </Panel>
      </Appear>
      {/* the chain */}
      <svg width={1920} height={1080} style={{ position: 'absolute' }}>
        {BLOCKS.slice(0, -1).map((_, i) => {
          const tin = ease(f, tEvery + (i + 1) * 4, tEvery + (i + 1) * 4 + 12);
          const br = broken(i + 1);
          const x1 = bx(i) + BW;
          const x2 = bx(i + 1);
          return br ? (
            <g key={i}>
              <line x1={x1} y1={Y + 75} x2={x1 + 14} y2={Y + 75 - 6} stroke={C.red} strokeWidth={6} />
              <line x1={x2 - 14} y1={Y + 75 + 6} x2={x2} y2={Y + 75} stroke={C.red} strokeWidth={6} />
            </g>
          ) : <line key={i} x1={x1} y1={Y + 75} x2={x1 + (x2 - x1) * tin} y2={Y + 75} stroke={C.purple} strokeWidth={6} style={{ filter: `drop-shadow(0 0 8px ${C.purple})` }} />;
        })}
      </svg>
      {BLOCKS.map((b, i) => {
        const tin = ease(f, tEvery + i * 4, tEvery + i * 4 + 16, EO);
        const red = (i === EDITED && edited) || broken(i);
        return (
          <div key={i} style={{ position: 'absolute', left: bx(i), top: Y, width: BW, opacity: tin, transform: `translateX(${(1 - tin) * 200}px)` }}>
            <div style={{ borderRadius: 20, padding: '18px 20px', height: 176, boxSizing: 'border-box', background: red ? '#2A0E14' : C.panel, border: `2px solid ${red ? C.red : `${C.purple}88`}`, boxShadow: red ? `0 0 30px ${C.red}66` : `0 0 24px ${C.purple}33`, fontFamily: F.sans }}>
              <div style={{ fontWeight: 800, fontSize: 26, color: red ? C.red : C.purple }}>#{b.n}</div>
              <div style={{ fontWeight: 700, fontSize: 24, color: C.text, marginTop: 4 }}>{b.ev}</div>
              <div style={{ fontWeight: 900, fontSize: 30, color: C.white, marginTop: 2 }}>{i === EDITED && edited ? <span style={{ color: C.red }}>¥1,750</span> : b.v}</div>
              <div style={{ fontFamily: 'Consolas, monospace', fontSize: 19, color: C.muted, marginTop: 4 }}>{b.h}</div>
            </div>
          </div>
        );
      })}
      {/* the head fingerprint flies to the chain */}
      {f >= tFinger && flyT < 1 && (
        <div style={{ position: 'absolute', left: lerp(head.x, target.x, flyT) - 30, top: lerp(head.y - 40, target.y, flyT) - 30, width: 60, height: 60, borderRadius: '50%', background: C.purple, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 0 40px ${C.purple}`, transform: `scale(${1 + Math.sin(flyT * Math.PI) * 0.4})` }}>
          <Icon name="IoFingerPrint" size={38} color="#160A24" />
        </div>
      )}
      {/* someone edits one entry */}
      {f >= tChange - 14 && f < tMatch + 40 && (
        <div style={{ position: 'absolute', left: lerp(1500, bx(EDITED) + 120, cursorT), top: lerp(980, Y + 100, cursorT), transform: `scale(${f >= tChange && f < tChange + 4 ? 0.85 : 1})` }}>
          <svg width={44} height={56} viewBox="0 0 24 30"><path d="M2 2 L2 24 L8 18 L12 28 L16 26 L12 17 L20 17 Z" fill="#fff" stroke="#000" strokeWidth={1.5} /></svg>
        </div>
      )}
      <Pop at={tMatch} style={{ position: 'absolute', left: 0, right: 0, top: 830, display: 'flex', justifyContent: 'center' }}>
        <Chip icon="IoAlertCircle" text="Edit one entry and every link after it breaks" color={C.red} bg="rgba(8,12,26,0.9)" size={28} />
      </Pop>
      {BLOCKS.map((_, i) => <Sfx key={i} at={tEvery + i * 4} name="tick" vol={0.22} />)}
      <Sfx at={tFinger + 4} name="whoosh" vol={0.3} />
      <Sfx at={tChain} name="chime" vol={0.4} />
      <Sfx at={tChange} name="tap" vol={0.4} />
      <Sfx at={tEntry + 6} name="crack" vol={0.5} />
      <Sfx at={tMatch} name="alert" vol={0.4} />
    </AbsoluteFill>
  );
}
