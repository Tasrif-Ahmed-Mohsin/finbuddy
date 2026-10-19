// Opening: the friend in his own words, the gaps in the legal channel, and Bluefin's answer.
import React from 'react';
import { AbsoluteFill, Img, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { evolvePath, getPointAtLength, getLength } from '@remotion/paths';
import { C, F } from './theme';
import { Appear, Chip, Counter, EIO, EO, Icon, Panel, Pop, Sfx, Stamp, Words, ease, lerp, pop, useAt, useScene } from './lib';
import { Mascot } from './Mascot';

// ---------------------------------------------------------------- friend, part one
export function FriendA() {
  const f = useCurrentFrame();
  const sc = useScene();
  const at = useAt();
  const t = ease(f, 0, 18);
  const push = lerp(1.0, 1.06, f / sc.frames);
  const chips = [
    { at: at('december'), icon: 'IoCard', text: 'Card endorsed only until 31 December', color: C.amber },
    { at: at('passport'), icon: 'IoDocumentText', text: 'Renewal: in person, with his passport, in Dhaka', color: C.amber },
    { at: at('students'), icon: 'IoSchool', text: 'Students get the shortest period', color: C.red },
  ];
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 150, top: 70, width: 1620, height: 912, borderRadius: 34, overflow: 'hidden', opacity: t, transform: `scale(${lerp(1.04, 1, t)})`, boxShadow: '0 40px 120px rgba(0,0,0,0.6), 0 0 0 1.5px rgba(77,163,255,0.3)' }}>
        <div style={{ position: 'absolute', inset: 0, transform: `scale(${push})` }}>
          <OffthreadVideo src={staticFile('friend_fa.mp4')} muted style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        </div>
        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg, rgba(5,9,20,0) 55%, rgba(5,9,20,0.75) 100%)' }} />
      </div>
      <Appear at={14} x={-40} y={0} style={{ position: 'absolute', left: 200, top: 700 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
          <div style={{ width: 8, height: 78, borderRadius: 4, background: C.neon, boxShadow: `0 0 18px ${C.neon}` }} />
          <div>
            <div style={{ fontFamily: F.sans, fontWeight: 800, fontSize: 40, color: C.white, letterSpacing: '-0.02em' }}>Our friend, a Bangladeshi student in China</div>
            <div style={{ fontFamily: F.sans, fontWeight: 500, fontSize: 26, color: '#C9D6F5', marginTop: 4 }}>Self-funded · studying in China since September 2026</div>
          </div>
        </div>
      </Appear>
      <div style={{ position: 'absolute', right: 200, top: 110, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 16 }}>
        {chips.map((c, i) => (
          <Pop key={i} at={c.at} origin="100% 50%">
            <Chip icon={c.icon} text={c.text} color={c.color} bg="rgba(8,12,26,0.82)" size={26} />
          </Pop>
        ))}
      </div>
      {chips.map((c, i) => <Sfx key={i} at={c.at} name="pop" vol={0.35} />)}
    </AbsoluteFill>
  );
}

// ---------------------------------------------------------------- the problem
const DHAKA = { x: 520, y: 650 };
const BEIJING = { x: 1400, y: 390 };
const ARC = `M ${DHAKA.x} ${DHAKA.y} Q 960 150 ${BEIJING.x} ${BEIJING.y}`;
const pointOn = (path: string, t: number) => getPointAtLength(path, getLength(path) * t);

function Avatar({ x, y, size, children, ring = C.neon }: { x: number; y: number; size: number; children: React.ReactNode; ring?: string }) {
  return (
    <div style={{ position: 'absolute', left: x - size / 2, top: y - size / 2, width: size, height: size, borderRadius: '50%', overflow: 'hidden', border: `4px solid ${ring}`, boxShadow: `0 0 0 10px ${ring}22, 0 0 50px ${ring}66`, background: C.panel }}>
      {children}
    </div>
  );
}

function Coins({ path, from, until, color = C.neon }: { path: string; from: number; until?: number; color?: string }) {
  const f = useCurrentFrame();
  if (f < from) return null;
  const fade = until !== undefined ? 1 - ease(f, until, until + 10) : 1;
  return (
    <>
      {[0, 1, 2].map((i) => {
        const t = (((f - from) / 75) + i / 3) % 1;
        const p = pointOn(path, t);
        const bdt = t < 0.55;
        return (
          <div key={i} style={{ position: 'absolute', left: p.x - 26, top: p.y - 26, width: 52, height: 52, borderRadius: '50%', opacity: fade * Math.min(1, t * 8, (1 - t) * 8), background: bdt ? '#1F7BEA' : C.green, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: F.sans, fontWeight: 800, fontSize: 28, color: '#fff', boxShadow: `0 0 26px ${bdt ? C.neon : C.green}` }}>
            {bdt ? '৳' : '¥'}
          </div>
        );
      })}
    </>
  );
}

const MONTHS = [
  { name: 'October 2026', y: 2026, m: 9 }, { name: 'November 2026', y: 2026, m: 10 }, { name: 'December 2026', y: 2026, m: 11 },
  { name: 'January 2027', y: 2027, m: 0 }, { name: 'February 2027', y: 2027, m: 1 }, { name: 'March 2027', y: 2027, m: 2 },
  { name: 'April 2027', y: 2027, m: 3 }, { name: 'May 2027', y: 2027, m: 4 }, { name: 'June 2027', y: 2027, m: 5 },
];
// The 20 days without money with today's habits (backend /plan/year, strategy "today").
export const STUCK = ['2027-01-11', '2027-02-11', '2027-02-12', '2027-02-13', '2027-02-14', '2027-03-17', '2027-03-18', '2027-03-19', '2027-03-20', '2027-03-21',
  '2027-04-21', '2027-05-22', '2027-05-23', '2027-05-24', '2027-05-25', '2027-05-26', '2027-05-27', '2027-05-28', '2027-05-29', '2027-05-30'];
// Bank closures in either country (same source), drawn as amber underlines.
export const CLOSED: [string, string][] = [['2026-10-20', '2026-10-21'], ['2026-12-16', '2026-12-16'], ['2026-12-25', '2026-12-25'], ['2026-12-31', '2026-12-31'],
  ['2027-01-01', '2027-01-01'], ['2027-02-05', '2027-02-13'], ['2027-02-21', '2027-02-21'], ['2027-03-08', '2027-03-13'], ['2027-03-26', '2027-03-26'],
  ['2027-04-03', '2027-04-05'], ['2027-04-14', '2027-04-14'], ['2027-05-01', '2027-05-05'], ['2027-05-14', '2027-05-20'], ['2027-06-09', '2027-06-09']];
const iso = (y: number, m: number, d: number) => `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
const isClosed = (s: string) => CLOSED.some(([a, b]) => s >= a && s <= b);

/** The student's year, month by month; red days light up from `redAt`, and turn green from `greenAt`. */
export function YearGrid({ at, redAt, greenAt, scanAt, cell = 30, monthW = 330, gap = 18, x = 0, y = 0, cardStopAt }: {
  at: number; redAt?: number; greenAt?: number; scanAt?: number; cell?: number; monthW?: number; gap?: number; x?: number; y?: number; cardStopAt?: number;
}) {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scanDay = scanAt !== undefined ? Math.floor(Math.max(0, f - scanAt) * 3.2) : -1; // days swept so far
  let dayIndex = 0;
  return (
    <div style={{ position: 'absolute', left: x, top: y, display: 'grid', gridTemplateColumns: `repeat(3, ${monthW}px)`, gap }}>
      {MONTHS.map((mo, mi) => {
        const s = pop(f, at + mi * 3, fps);
        const first = new Date(Date.UTC(mo.y, mo.m, 1)).getUTCDay(); // 0 = Sunday
        const offset = (first + 6) % 7; // Monday first
        const days = new Date(Date.UTC(mo.y, mo.m + 1, 0)).getUTCDate();
        return (
          <div key={mi} style={{ opacity: Math.min(1, s * 1.5), transform: `translateY(${(1 - s) * 40}px) scale(${lerp(0.9, 1, s)})` }}>
            <Panel pad={16} style={{ borderRadius: 20 }}>
              <div style={{ fontFamily: F.sans, fontWeight: 700, fontSize: 19, color: C.text, marginBottom: 8, letterSpacing: '0.01em' }}>{mo.name}</div>
              <div style={{ display: 'grid', gridTemplateColumns: `repeat(7, ${(monthW - 32) / 7}px)`, rowGap: 4 }}>
                {Array.from({ length: offset }).map((_, i) => <div key={`o${i}`} />)}
                {Array.from({ length: days }).map((_, d) => {
                  const ds = iso(mo.y, mo.m, d + 1);
                  const inHorizon = ds >= '2026-10-12' && ds <= '2027-06-29';
                  const idx = inHorizon ? dayIndex++ : -1;
                  const stuck = STUCK.indexOf(ds);
                  let bg = inHorizon ? 'rgba(142,154,192,0.22)' : 'rgba(142,154,192,0.07)';
                  let glow = 'none';
                  let k = 1;
                  if (stuck >= 0 && redAt !== undefined && f >= redAt + stuck * 2) {
                    const r = ease(f, redAt + stuck * 2, redAt + stuck * 2 + 8);
                    k = lerp(1.8, 1, r);
                    bg = C.red;
                    glow = `0 0 12px ${C.red}`;
                    if (greenAt !== undefined && f >= greenAt + stuck * 2) {
                      bg = C.green;
                      glow = `0 0 12px ${C.green}`;
                      k = lerp(1.6, 1, ease(f, greenAt + stuck * 2, greenAt + stuck * 2 + 8));
                    }
                  }
                  const scanned = idx >= 0 && idx <= scanDay;
                  const head = idx >= 0 && Math.abs(idx - scanDay) < 2;
                  if (scanned && bg.startsWith('rgba')) bg = 'rgba(77,163,255,0.42)';
                  const cardStop = ds === '2026-12-31' && cardStopAt !== undefined && f >= cardStopAt;
                  return (
                    <div key={d} style={{ height: cell * 0.72, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
                      <div style={{ width: cell * 0.5, height: cell * 0.5, borderRadius: cell * 0.16, background: head ? C.white : bg, boxShadow: head ? `0 0 14px ${C.neon}` : glow, transform: `scale(${k})` }} />
                      {inHorizon && isClosed(ds) && <div style={{ position: 'absolute', bottom: 0, width: cell * 0.5, height: 2.5, borderRadius: 2, background: C.amber, opacity: 0.85 }} />}
                      {cardStop && <div style={{ position: 'absolute', inset: -4, borderRadius: 8, border: `2.5px solid ${C.amber}`, boxShadow: `0 0 12px ${C.amber}` }} />}
                    </div>
                  );
                })}
              </div>
            </Panel>
          </div>
        );
      })}
    </div>
  );
}

export function S02() {
  const f = useCurrentFrame();
  const at = useAt();
  const tStudies = at('studies');
  const tFather = at('father');
  const tBank = at('bank');
  const tLegal = at('legal');
  const tGap = at('gap');
  const tCard = at('card');
  const tDec = at('december');
  const tEid = at('eid');
  const tSpring = at('spring');
  const tPut = at('put');
  const t20 = at('20');
  const tHundi = at('thats', 1);
  // friend avatar flies from centre to Beijing
  const fly = ease(f, tStudies - 4, tStudies + 22, EIO);
  const ax = lerp(960, BEIJING.x, fly);
  const ay = lerp(480, BEIJING.y, fly);
  const asz = lerp(340, 150, fly);
  const mapOut = ease(f, tPut, tPut + 14, EIO);
  const arcDraw = ease(f, tBank - 10, tBank + 18, EIO);
  const broken = ease(f, tGap, tGap + 10);
  const ev = evolvePath(arcDraw, ARC);
  const calIn = tPut + 6;
  const hundiK = ease(f, tHundi, tHundi + 14);
  return (
    <AbsoluteFill>
      {/* the map */}
      <AbsoluteFill style={{ opacity: 1 - mapOut, transform: `scale(${lerp(1, 0.9, mapOut)})`, filter: mapOut > 0 ? `blur(${mapOut * 8}px)` : undefined }}>
        <svg width={1920} height={1080} style={{ position: 'absolute' }}>
          <path d={ARC} fill="none" stroke={broken > 0 ? `rgba(255,92,92,${0.25 + 0.35 * (1 - broken)})` : C.neon} strokeWidth={6} strokeDasharray={ev.strokeDasharray} strokeDashoffset={ev.strokeDashoffset} strokeLinecap="round" style={{ filter: `drop-shadow(0 0 12px ${broken > 0 ? C.red : C.neon})` }} />
        </svg>
        {f >= tBank && <Coins path={ARC} from={tBank + 14} until={tGap} />}
        {[0.3, 0.55, 0.8].map((p, i) => {
          const pt = pointOn(ARC, p);
          return (
            <Pop key={i} at={tGap + i * 5} style={{ position: 'absolute', left: pt.x - 30, top: pt.y - 30 }}>
              <div style={{ width: 60, height: 60, borderRadius: '50%', background: '#2A0E14', border: `3px solid ${C.red}`, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 0 30px ${C.red}` }}>
                <Icon name="IoClose" size={40} color={C.red} />
              </div>
            </Pop>
          );
        })}
        <Pop at={tBank + 8} style={{ position: 'absolute', left: 960 - 250, top: 190 }}>
          <Chip icon="IoBusiness" text="Bank transfer" color={C.neon} bg="rgba(8,12,26,0.85)" />
        </Pop>
        <Pop at={tLegal} style={{ position: 'absolute', left: 960 + 20, top: 190 }}>
          <Chip icon="IoCheckmarkCircle" text="Legal" color={C.green} bg="rgba(8,12,26,0.85)" />
        </Pop>
        {/* father in Dhaka */}
        <Pop at={tFather} style={{ position: 'absolute', left: 0, top: 0 }}>
          <Avatar x={DHAKA.x} y={DHAKA.y} size={150} ring={C.neon}>
            <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(160deg,#1E2A4A,#0E1324)' }}>
              <Icon name="IoPerson" size={80} color="#C9D6F5" />
            </div>
          </Avatar>
          <div style={{ position: 'absolute', left: DHAKA.x - 160, top: DHAKA.y + 92, width: 320, textAlign: 'center', fontFamily: F.sans }}>
            <div style={{ fontWeight: 800, fontSize: 30, color: C.white }}>His father</div>
            <div style={{ fontWeight: 700, fontSize: 20, color: C.neon, letterSpacing: '0.2em', marginTop: 4 }}>DHAKA · BANGLADESH</div>
          </div>
        </Pop>
        {/* the friend, flying to Beijing */}
        <Avatar x={ax} y={ay} size={asz} ring={C.neon}>
          <Img src={staticFile('img/friend_end.jpg')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: '50% 30%', transform: 'scale(1.7)' }} />
        </Avatar>
        <Appear at={tStudies + 14} style={{ position: 'absolute', left: BEIJING.x - 160, top: BEIJING.y + 90, width: 320, textAlign: 'center', fontFamily: F.sans }}>
          <div style={{ fontWeight: 800, fontSize: 30, color: C.white }}>Our friend</div>
          <div style={{ fontWeight: 700, fontSize: 20, color: C.neon, letterSpacing: '0.2em', marginTop: 4 }}>BEIJING · CHINA</div>
        </Appear>
        {/* the card stops */}
        <Appear at={tCard} x={60} y={0} style={{ position: 'absolute', left: 1420, top: 650 }}>
          <div style={{ position: 'relative', width: 380, height: 236, borderRadius: 24, padding: 26, background: f >= tDec ? 'linear-gradient(135deg,#3A3F4C,#22252E)' : 'linear-gradient(135deg,#1F7BEA,#0B3E91)', boxShadow: '0 30px 60px rgba(0,0,0,0.45)', fontFamily: F.sans, color: '#fff', filter: f >= tDec ? 'grayscale(0.6)' : undefined }}>
            <div style={{ fontWeight: 700, fontSize: 22, opacity: 0.85 }}>Bangladeshi debit card</div>
            <div style={{ width: 54, height: 40, borderRadius: 8, background: 'linear-gradient(135deg,#F6D27A,#B98C2E)', marginTop: 22 }} />
            <div style={{ fontWeight: 600, fontSize: 22, marginTop: 24, letterSpacing: '0.14em' }}>•••• •••• •••• 4417</div>
            <div style={{ fontWeight: 500, fontSize: 18, marginTop: 8, opacity: 0.85 }}>Abroad until 31 Dec 2026</div>
            <Stamp at={tDec} text="STOPS 31 DEC" size={40} rotate={-10} style={{ position: 'absolute', left: 40, top: 80 }} />
          </div>
        </Appear>
        <Pop at={tEid} style={{ position: 'absolute', left: DHAKA.x - 190, top: DHAKA.y + 190 }}>
          <Chip icon="IoMoon" text="Eid · banks closed" color={C.amber} bg="rgba(8,12,26,0.85)" />
        </Pop>
        <Pop at={tSpring} style={{ position: 'absolute', left: BEIJING.x - 250, top: BEIJING.y + 170 }}>
          <Chip icon="IoSparkles" text="Spring Festival · banks closed" color={C.amber} bg="rgba(8,12,26,0.85)" />
        </Pop>
      </AbsoluteFill>
      {/* the year on a calendar */}
      {f >= calIn && (
        <AbsoluteFill style={{ opacity: 1 - hundiK * 0.55, filter: hundiK > 0 ? `blur(${hundiK * 5}px)` : undefined }}>
          <Appear at={calIn} style={{ position: 'absolute', left: 120, top: 70 }}>
            <div style={{ fontFamily: F.sans, fontWeight: 700, fontSize: 22, letterSpacing: '0.2em', color: C.muted }}>HIS YEAR, DAY BY DAY · TODAY'S HABITS</div>
          </Appear>
          <YearGrid at={calIn + 2} redAt={t20 - 18} x={120} y={120} cell={30} monthW={330} gap={16} />
          <Appear at={t20 - 8} style={{ position: 'absolute', left: 1240, top: 300, width: 560 }}>
            <div style={{ fontFamily: F.sans, fontWeight: 900, fontSize: 260, lineHeight: 0.9, color: C.red, letterSpacing: '-0.05em', textShadow: `0 0 60px ${C.red}88` }}>
              <Counter from={0} to={20} at={t20 - 18} dur={40} />
            </div>
            <div style={{ fontFamily: F.sans, fontWeight: 800, fontSize: 54, color: C.white, letterSpacing: '-0.02em', marginTop: 10 }}>days without money</div>
            <div style={{ fontFamily: F.sans, fontWeight: 500, fontSize: 26, color: C.muted, marginTop: 12, lineHeight: 1.35 }}>The card stopping, Eid and Spring Festival, and transfers sent too late.</div>
          </Appear>
        </AbsoluteFill>
      )}
      {/* the hundi offer */}
      {f >= tHundi && (
        <div style={{ position: 'absolute', left: 1010, top: 250, opacity: hundiK, transform: `translateX(${(1 - hundiK) * 120}px) rotate(${(1 - hundiK) * 4}deg)` }}>
          <div style={{ width: 760, borderRadius: 30, padding: '28px 32px', background: 'linear-gradient(160deg,#1B1F2B,#11141C)', border: `2px solid ${C.red}66`, boxShadow: `0 40px 100px rgba(0,0,0,0.6), 0 0 60px ${C.red}33`, fontFamily: F.sans }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <div style={{ width: 56, height: 56, borderRadius: '50%', background: '#2A2F3D', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name="IoPersonOutline" size={32} color="#9AA6C2" /></div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 26, color: C.white }}>Unknown number</div>
                <div style={{ fontWeight: 500, fontSize: 20, color: C.muted }}>WhatsApp · just now</div>
              </div>
            </div>
            <div style={{ marginTop: 20, fontWeight: 500, fontSize: 32, lineHeight: 1.35, color: '#E8EEFF' }}>
              Need money in China fast? Better rate than the bank, no papers. Cash tomorrow.
            </div>
            <div style={{ display: 'flex', gap: 12, marginTop: 22 }}>
              <Pop at={tHundi + 26}><Chip icon="IoWarning" text="Hundi: illegal" color={C.red} size={22} /></Pop>
              <Pop at={tHundi + 34}><Chip icon="IoSnow" text="Can freeze his account" color={C.red} size={22} /></Pop>
            </div>
          </div>
        </div>
      )}
      <Sfx at={tStudies} name="whoosh" vol={0.3} />
      <Sfx at={tBank} name="rise" vol={0.25} />
      <Sfx at={tGap} name="crack" vol={0.45} />
      <Sfx at={tDec} name="stamp" vol={0.5} />
      <Sfx at={tPut} name="whoosh" vol={0.3} />
      {STUCK.map((_, i) => <Sfx key={i} at={t20 - 18 + i * 2} name="tick" vol={0.18} />)}
      <Sfx at={tHundi} name="notify" vol={0.45} />
    </AbsoluteFill>
  );
}

// ---------------------------------------------------------------- Bluefin
export function S03() {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const at = useAt();
  const tKeeps = at('keeps');
  const tYear = at('year');
  const tBank = at('bank');
  const tActs = at('acts');
  const tLimit = at('limit');
  const tSigned = at('signed');
  const tLoop = at('one');
  const nodesAt = [at('since'), at('plan'), at('act', 1), at('proof')];
  const logoS = pop(f, 4, fps, { damping: 12, stiffness: 140 });
  const up = ease(f, tKeeps - 6, tKeeps + 16, EIO);
  const sweep = ease(f, 14, 40, EIO);
  const arcOut = ease(f, tActs - 4, tActs + 10);
  const boxIn = ease(f, tActs, tActs + 20, EIO);
  const boxOut = ease(f, tLoop - 6, tLoop + 8);
  const loopIn = ease(f, tLoop, tLoop + 18, EO);
  const SEALED = 'M 520 760 Q 960 440 1400 600';
  const ev = evolvePath(ease(f, tKeeps + 6, tKeeps + 26, EIO), SEALED);
  // mascot wandering inside the signed limit
  const wx = 960 + Math.sin((f - tActs) / 14) * 330;
  const wy = 640 + Math.sin((f - tActs) / 9) * 70;
  const hitL = Math.abs(Math.sin((f - tActs) / 14)) > 0.97;
  const R = 250;
  const CX = 960;
  const CY = 620;
  const nodes = [
    { label: 'Sense', icon: 'IoMail', color: C.neon, a: -90 },
    { label: 'Plan', icon: 'IoCalendar', color: C.amber, a: 0 },
    { label: 'Act', icon: 'IoFingerPrint', color: C.green, a: 90 },
    { label: 'Prove', icon: 'IoReceipt', color: C.purple, a: 180 },
  ];
  const comet = ((f - tLoop) / 50) * Math.PI * 2 - Math.PI / 2;
  return (
    <AbsoluteFill>
      {/* logo */}
      <div style={{ position: 'absolute', left: 0, right: 0, top: lerp(330, 92, up), display: 'flex', flexDirection: 'column', alignItems: 'center', transform: `scale(${lerp(1, 0.52, up)})`, transformOrigin: '50% 0%' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 40 }}>
          <div style={{ position: 'relative', width: 200, height: 200, transform: `scale(${logoS}) rotate(${(1 - logoS) * -20}deg)`, borderRadius: 48, overflow: 'hidden', boxShadow: `0 0 80px ${C.neon}66` }}>
            <Img src={staticFile('img/icon.png')} style={{ width: 200, height: 200 }} />
            <div style={{ position: 'absolute', top: -40, bottom: -40, width: 60, left: lerp(-120, 260, sweep), background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.65), transparent)', transform: 'rotate(18deg)' }} />
          </div>
          <Words text="Bluefin" at={10} stagger={2} size={190} weight={900} style={{ letterSpacing: '-0.05em' }} />
        </div>
        <Words text="Money from home, on time, *the legal way.*" at={22} stagger={3} size={56} weight={700} color="#C9D6F5" style={{ marginTop: 26 }} out={tKeeps - 4} />
      </div>
      {/* funded all year, through the bank */}
      <AbsoluteFill style={{ opacity: 1 - arcOut }}>
        <svg width={1920} height={1080} style={{ position: 'absolute' }}>
          <path d={SEALED} fill="none" stroke={C.neon} strokeWidth={7} strokeDasharray={ev.strokeDasharray} strokeDashoffset={ev.strokeDashoffset} strokeLinecap="round" style={{ filter: `drop-shadow(0 0 14px ${C.neon})` }} />
        </svg>
        {f > tKeeps + 20 && <Coins path={SEALED} from={tKeeps + 20} />}
        <Pop at={tKeeps + 6} style={{ position: 'absolute', left: 520 - 60, top: 760 - 60 }}>
          <div style={{ width: 120, height: 120, borderRadius: '50%', background: C.panel, border: `3px solid ${C.neon}`, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 0 40px ${C.neon}88` }}><Icon name="IoHome" size={56} color={C.neon} /></div>
        </Pop>
        <Pop at={tKeeps + 22} style={{ position: 'absolute', left: 1400 - 60, top: 600 - 60 }}>
          <div style={{ width: 120, height: 120, borderRadius: '50%', background: C.panel, border: `3px solid ${C.green}`, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 0 40px ${C.green}88` }}><Icon name="IoSchool" size={56} color={C.green} /></div>
        </Pop>
        <Pop at={tYear} style={{ position: 'absolute', left: 700, top: 820 }}><Chip icon="IoCalendar" text="Funded all year" color={C.green} bg="rgba(8,12,26,0.85)" size={30} /></Pop>
        <Pop at={tBank} style={{ position: 'absolute', left: 1040, top: 820 }}><Chip icon="IoBusiness" text="Through the bank" color={C.neon} bg="rgba(8,12,26,0.85)" size={30} /></Pop>
      </AbsoluteFill>
      {/* acts only inside a limit his family signed */}
      {f >= tActs && (
        <AbsoluteFill style={{ opacity: boxIn * (1 - boxOut) }}>
          <svg width={1920} height={1080} style={{ position: 'absolute' }}>
            <rect x={540} y={430} width={840} height={420} rx={40} fill="rgba(77,163,255,0.05)" stroke={hitL ? C.white : C.neon} strokeWidth={4} strokeDasharray="18 12" strokeDashoffset={-f * 1.5} style={{ filter: `drop-shadow(0 0 14px ${C.neon})` }} />
          </svg>
          <div style={{ position: 'absolute', left: 540, width: 840, top: 404, display: 'flex', justifyContent: 'center' }}>
            <Pop at={tLimit}><Chip icon="IoLockClosed" text="The limit his family signed" color={C.neon} bg={C.bg1} size={30} /></Pop>
          </div>
          <Pop at={tSigned} style={{ position: 'absolute', left: 1330, top: 380 }}>
            <div style={{ display: 'flex', gap: 10 }}>
              {[0, 1].map((i) => <div key={i} style={{ width: 70, height: 70, borderRadius: '50%', background: C.green, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 0 30px ${C.green}` }}><Icon name="IoFingerPrint" size={42} color="#05121A" /></div>)}
            </div>
          </Pop>
          <div style={{ position: 'absolute', left: wx - 90, top: wy - 120 }}><Mascot size={170} glow={0.6} /></div>
        </AbsoluteFill>
      )}
      {/* one loop */}
      {f >= tLoop && (
        <AbsoluteFill style={{ opacity: loopIn }}>
          <svg width={1920} height={1080} style={{ position: 'absolute' }}>
            <circle cx={CX} cy={CY} r={R} fill="none" stroke="rgba(77,163,255,0.25)" strokeWidth={4} strokeDasharray="6 10" />
            <circle cx={CX + Math.cos(comet) * R} cy={CY + Math.sin(comet) * R} r={12} fill={C.white} style={{ filter: `drop-shadow(0 0 16px ${C.neon})` }} />
          </svg>
          <div style={{ position: 'absolute', left: CX - 80, top: CY - 80, width: 160, height: 160, borderRadius: 40, overflow: 'hidden', transform: `scale(${loopIn})`, boxShadow: `0 0 60px ${C.neon}66` }}>
            <Img src={staticFile('img/icon.png')} style={{ width: 160, height: 160 }} />
          </div>
          {nodes.map((n, i) => {
            const x = CX + Math.cos((n.a * Math.PI) / 180) * R;
            const y = CY + Math.sin((n.a * Math.PI) / 180) * R;
            const lx = n.a === 0 || n.a === 90 ? 70 : n.a === 180 ? -330 : -130;
            const ly = n.a === -90 ? -120 : -26;
            return (
              <Pop key={i} at={nodesAt[i]} style={{ position: 'absolute', left: x - 56, top: y - 56 }}>
                <div style={{ width: 112, height: 112, borderRadius: '50%', background: C.panel, border: `4px solid ${n.color}`, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 0 44px ${n.color}99` }}>
                  <Icon name={n.icon} size={54} color={n.color} />
                </div>
                <div style={{ position: 'absolute', left: 56 + lx, top: 56 + ly, width: 260, textAlign: n.a === 0 || n.a === 90 ? 'left' : n.a === 180 ? 'right' : 'center', fontFamily: F.sans, fontWeight: 900, fontSize: 52, color: n.color, letterSpacing: '-0.02em' }}>{n.label}</div>
              </Pop>
            );
          })}
        </AbsoluteFill>
      )}
      <Sfx at={4} name="reveal" vol={0.55} />
      <Sfx at={tKeeps + 6} name="rise" vol={0.25} />
      <Sfx at={tActs} name="whoosh" vol={0.3} />
      {nodesAt.map((t, i) => <Sfx key={i} at={t} name="pop" vol={0.4} />)}
    </AbsoluteFill>
  );
}
