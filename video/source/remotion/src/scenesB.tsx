// Sense and Plan: bank messages sorted, money left in China, and the whole year planned.
import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, F } from './theme';
import { Appear, Chip, Counter, EIO, EO, Icon, Kicker, Panel, Phone, Pop, Score, Sfx, Shell, Words, ease, lerp, pop, useAt } from './lib';
import { YearGrid } from './scenesA';

// ---------------------------------------------------------------- 1 · Sense: the bank messages
const MSGS = [
  { from: 'BRAC Bank', icon: 'IoBusiness', text: 'Tk 1,16,598 sent abroad: student living money, ref TT-0001', kind: 'money' },
  { from: 'bKash', icon: 'IoKey', text: 'Your one-time code is 482913. Do not share it.', kind: 'otp' },
  { from: 'Alipay', icon: 'IoWallet', text: 'You paid ¥38.50 at the campus canteen', kind: 'money' },
  { from: 'Daraz', icon: 'IoPricetag', text: 'Mega sale! 50% off sneakers this weekend', kind: 'promo' },
  { from: '+880 1XXX', icon: 'IoWarning', text: 'Your BRAC account is locked. Verify now: brac-secure-login.top', kind: 'phish' },
  { from: 'Bank of China', icon: 'IoBusiness', text: 'CNY 6,100.00 credited to account ****3317', kind: 'money' },
];

export function S4a() {
  const f = useCurrentFrame();
  const at = useAt();
  const tIn = at('family');
  const tCodes = at('codes');
  const tKeeps = at('keeps');
  const tMoney = at('money');
  const tFlags = at('flags');
  const tTap = at('bluefin');
  const H = 90;
  let y = 0;
  const rows = MSGS.map((m, i) => {
    const drop = m.kind === 'otp' || m.kind === 'promo' ? ease(f, tKeeps + (m.kind === 'promo' ? 4 : 0), tKeeps + 16, EIO) : 0;
    const row = { m, i, y, drop };
    y += (H + 12) * (1 - drop);
    return row;
  });
  return (
    <AbsoluteFill>
      <Kicker step="sense" />
      <Score text="TASK COMPLETION · 40%" />
      <Appear at={4} style={{ position: 'absolute', left: 110, top: 150 }}>
        <Words text="Bank messages, *sorted.*" at={4} size={64} />
      </Appear>
      <div style={{ position: 'absolute', left: 110, top: 255, width: 900 }}>
        {rows.map(({ m, i, y: ry, drop }) => {
          const tin = ease(f, tIn + i * 5, tIn + i * 5 + 16, EO);
          if (tin <= 0 || drop >= 1) return null;
          const redact = m.kind === 'otp' ? ease(f, tCodes - 4, tCodes + 10, EIO) : 0;
          const phish = m.kind === 'phish' && f >= tFlags;
          const shakeX = phish && f < tFlags + 14 ? Math.sin((f - tFlags) * 2.2) * 10 * (1 - (f - tFlags) / 14) : 0;
          const okTag = m.kind === 'money' && f >= tMoney + i * 2;
          return (
            <div key={i} style={{ position: 'absolute', left: 0, top: ry, width: 900, opacity: tin * (1 - drop), transform: `translateX(${(1 - tin) * -140 - drop * 260 + shakeX}px)` }}>
              <Shell style={{ display: 'flex', alignItems: 'center', gap: 20, height: H, padding: '0 26px', border: phish ? `3px solid ${C.red}` : undefined, boxShadow: phish ? `0 0 40px ${C.red}88` : undefined }}>
                <div style={{ width: 58, height: 58, borderRadius: 16, background: phish ? '#FBE1DE' : '#DCEBFF', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <Icon name={m.icon} size={32} color={phish ? '#C42B1C' : '#0062CC'} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 22, color: '#5F6470' }}>{m.from}</div>
                  <div style={{ fontWeight: 600, fontSize: 25, color: C.ink, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', position: 'relative' }}>
                    {m.kind === 'otp' && redact > 0 ? (
                      <span>Your one-time code is <span style={{ background: C.ink, color: C.ink, borderRadius: 6, padding: '0 6px', clipPath: `inset(0 ${(1 - redact) * 100}% 0 0)` }}>482913</span>. Do not share it.</span>
                    ) : m.text}
                  </div>
                </div>
                {m.kind === 'otp' && <Pop at={tCodes + 4}><Chip icon="IoEyeOff" text="Code removed" color="#8A5300" bg="#FBEFCF" textColor="#8A5300" size={20} /></Pop>}
                {okTag && <Pop at={tMoney + i * 2}><Chip icon="IoCheckmarkCircle" text="Money" color="#17703A" bg="#DDF3E6" textColor="#17703A" size={20} /></Pop>}
                {phish && <Pop at={tFlags}><Chip icon="IoWarning" text="Phishing" color="#C42B1C" bg="#FBE1DE" textColor="#C42B1C" size={20} /></Pop>}
              </Shell>
            </div>
          );
        })}
      </div>
      <Appear at={8} x={80} y={0} style={{ position: 'absolute', left: 1320, top: 120 }}>
        <Phone width={370} screens={[{ src: 'st_messages_show', at: 0 }, { src: 'st_messages_result', at: tTap + 10 }]} taps={[{ x: 195, y: 404, at: tTap }]} />
      </Appear>
      {MSGS.map((_, i) => <Sfx key={i} at={tIn + i * 5} name="tick" vol={0.22} />)}
      <Sfx at={tCodes} name="swipe" vol={0.35} />
      <Sfx at={tKeeps} name="whoosh" vol={0.25} />
      <Sfx at={tFlags} name="alert" vol={0.45} />
      <Sfx at={tTap} name="tap" vol={0.4} />
    </AbsoluteFill>
  );
}

// ---------------------------------------------------------------- 1 · Sense: how long the money lasts
export function S4b() {
  const f = useCurrentFrame();
  const at = useAt();
  const t11 = at('11');
  const R = 210;
  const per = 2 * Math.PI * R;
  const fill = ease(f, 6, t11 + 10, EIO) * 0.37;
  return (
    <AbsoluteFill>
      <Kicker step="sense" />
      <Score text="TASK COMPLETION · 40%" />
      <div style={{ position: 'absolute', left: 250, top: 230, width: 2 * R + 60, height: 2 * R + 60 }}>
        <svg width={2 * R + 60} height={2 * R + 60} style={{ position: 'absolute', transform: 'rotate(-90deg)' }}>
          <circle cx={R + 30} cy={R + 30} r={R} fill="none" stroke="rgba(142,154,192,0.18)" strokeWidth={26} />
          <circle cx={R + 30} cy={R + 30} r={R} fill="none" stroke={C.neon} strokeWidth={26} strokeLinecap="round" strokeDasharray={per} strokeDashoffset={per * (1 - fill)} style={{ filter: `drop-shadow(0 0 18px ${C.neon})` }} />
        </svg>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: F.sans }}>
          <div style={{ fontWeight: 900, fontSize: 210, color: C.white, lineHeight: 0.9, letterSpacing: '-0.05em', textShadow: `0 0 50px ${C.neon}66` }}>
            <Counter from={0} to={11} at={8} dur={Math.max(12, t11 - 4)} />
          </div>
          <div style={{ fontWeight: 800, fontSize: 40, color: C.neon, letterSpacing: '0.12em', marginTop: 8 }}>DAYS LEFT</div>
        </div>
      </div>
      <Appear at={t11} style={{ position: 'absolute', left: 820, top: 380 }}>
        <div style={{ fontFamily: F.sans }}>
          <div style={{ fontWeight: 800, fontSize: 64, color: C.white, letterSpacing: '-0.03em' }}>¥2,300 in China</div>
          <div style={{ fontWeight: 500, fontSize: 32, color: C.muted, marginTop: 10 }}>Runs out on 23 October</div>
        </div>
      </Appear>
      <Appear at={4} x={80} y={0} style={{ position: 'absolute', left: 1360, top: 130 }}>
        <Phone width={360} screens={[{ src: 'home', at: 0 }]} zoom={{ at: t11 - 6, x: 195, y: 500, k: 1.55 }} />
      </Appear>
      <Sfx at={8} name="rise" vol={0.25} />
      <Sfx at={t11} name="pop" vol={0.45} />
    </AbsoluteFill>
  );
}

// ---------------------------------------------------------------- 2 · Plan: the year, day by day, and the real leak
export function S4c() {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const at = useAt();
  const tPlans = at('plans');
  const tDay = at('day');
  const tHol = at('holidays');
  const tCard = at('card');
  const tToday = at('todays');
  const t20 = at('20');
  const tPlan = at('plan', 1);
  const t0 = at('0');
  const tCost = at('cost');
  const tMost = at('most');
  const tFees = at('fees');
  const tFx = at('exchange');
  const gridOut = ease(f, tCost - 6, tCost + 14, EIO);
  const barsIn = ease(f, tCost, tCost + 18, EO);
  const feeW = ease(f, tMost, tMost + 26, EIO);
  const fxW = ease(f, tFx - 10, tFx + 14, EIO);
  return (
    <AbsoluteFill>
      <Kicker step="plan" />
      <Score text="TASK COMPLETION · 40%" color={C.amber} />
      <AbsoluteFill style={{ opacity: 1 - gridOut, transform: `translateX(${-gridOut * 200}px) scale(${1 - gridOut * 0.15})`, filter: gridOut > 0 ? `blur(${gridOut * 8}px)` : undefined }}>
        <YearGrid at={tPlans - 4} scanAt={tDay} redAt={tToday} greenAt={tPlan} cardStopAt={tCard} x={110} y={140} cell={28} monthW={300} gap={16} />
        <div style={{ position: 'absolute', left: 1110, top: 160, width: 700, display: 'flex', flexDirection: 'column', gap: 26 }}>
          <Pop at={tHol} origin="0% 50%"><Chip icon="IoCalendar" text="Bank holidays in both countries" color={C.amber} bg="rgba(8,12,26,0.85)" size={26} /></Pop>
          <Pop at={tCard} origin="0% 50%"><Chip icon="IoCard" text="Card stops abroad: 31 Dec" color={C.amber} bg="rgba(8,12,26,0.85)" size={26} /></Pop>
          <Appear at={tToday} x={40} y={0}>
            <Panel glow={C.red} style={{ padding: '22px 30px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
                <div style={{ fontFamily: F.sans, fontWeight: 900, fontSize: 120, color: C.red, width: 170, lineHeight: 1, textShadow: `0 0 40px ${C.red}88` }}><Counter from={0} to={20} at={tToday} dur={Math.max(14, t20 - tToday + 10)} /></div>
                <div style={{ fontFamily: F.sans }}>
                  <div style={{ fontWeight: 800, fontSize: 34, color: C.white }}>days without money</div>
                  <div style={{ fontWeight: 600, fontSize: 24, color: C.muted, marginTop: 4 }}>with today's habits</div>
                </div>
              </div>
            </Panel>
          </Appear>
          <Appear at={tPlan - 4} x={40} y={0}>
            <Panel glow={C.green} style={{ padding: '22px 30px', border: `1.5px solid ${C.green}66` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
                <div style={{ fontFamily: F.sans, fontWeight: 900, fontSize: 120, color: C.green, width: 170, lineHeight: 1, textShadow: `0 0 40px ${C.green}88` }}><Counter from={20} to={0} at={tPlan} dur={Math.max(14, t0 - tPlan + 8)} /></div>
                <div style={{ fontFamily: F.sans }}>
                  <div style={{ fontWeight: 800, fontSize: 34, color: C.white }}>days without money</div>
                  <div style={{ fontWeight: 600, fontSize: 24, color: C.muted, marginTop: 4 }}>with Bluefin's plan</div>
                </div>
              </div>
            </Panel>
          </Appear>
        </div>
      </AbsoluteFill>
      {f >= tCost && (
        <AbsoluteFill style={{ opacity: barsIn }}>
          <div style={{ position: 'absolute', left: 150, top: 165 }}>
            <Words text="Fees, not the exchange rate, *are the leak.*" at={tCost} size={66} accent={C.amber} />
            <div style={{ fontFamily: F.sans, fontWeight: 500, fontSize: 28, color: C.muted, marginTop: 14 }}>One real tuition payment: ¥35,200 through BRAC Bank, in taka</div>
          </div>
          <div style={{ position: 'absolute', left: 150, top: 400, width: 1100 }}>
            {[
              { label: 'Fixed bank charge', v: 8000, w: feeW, color: C.red },
              { label: 'Exchange-rate markup (0.22%)', v: 1448, w: fxW, color: C.neon },
            ].map((b, i) => (
              <div key={i} style={{ marginBottom: 46 }}>
                <div style={{ fontFamily: F.sans, fontWeight: 700, fontSize: 30, color: C.text, marginBottom: 12 }}>{b.label}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 22 }}>
                  <div style={{ height: 86, width: (b.v / 8000) * 860 * b.w, borderRadius: 18, background: `linear-gradient(90deg, ${b.color}AA, ${b.color})`, boxShadow: `0 0 40px ${b.color}66` }} />
                  <div style={{ fontFamily: F.sans, fontWeight: 900, fontSize: 60, color: b.color, opacity: b.w }}>৳<Counter from={0} to={b.v} at={i === 0 ? tMost : tFx - 10} dur={24} /></div>
                </div>
              </div>
            ))}
          </div>
          <Pop at={tFees + 6} style={{ position: 'absolute', left: 1350, top: 360 }}>
            <Panel glow={C.amber} style={{ width: 400, textAlign: 'center', padding: '34px 20px' }}>
              <div style={{ fontFamily: F.sans, fontWeight: 900, fontSize: 150, color: C.amber, lineHeight: 1, letterSpacing: '-0.04em', textShadow: `0 0 40px ${C.amber}88` }}>5.5×</div>
              <div style={{ fontFamily: F.sans, fontWeight: 600, fontSize: 28, color: C.text, marginTop: 12 }}>the charge, against the markup</div>
            </Panel>
          </Pop>
          <Pop at={tFx + 8} style={{ position: 'absolute', left: 1350, top: 700 }}>
            <Chip icon="IoPieChart" text="89% of a year's loss is fees" color={C.amber} bg="rgba(8,12,26,0.85)" size={26} />
          </Pop>
        </AbsoluteFill>
      )}
      <Sfx at={tPlans} name="whoosh" vol={0.3} />
      <Sfx at={tDay} name="scan" vol={0.3} />
      <Sfx at={tToday} name="alert" vol={0.3} />
      <Sfx at={tPlan} name="success" vol={0.45} />
      <Sfx at={tCost} name="whoosh" vol={0.3} />
      <Sfx at={tMost} name="rise" vol={0.25} />
      <Sfx at={tFees + 6} name="pop" vol={0.45} />
    </AbsoluteFill>
  );
}
