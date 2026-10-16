import { useCallback, useState } from 'react';
import { View } from 'react-native';

import { DataBanner } from '@/components/data-banner';
import { ThemedText } from '@/components/themed-text';
import { Badge, Button, Card, ErrorBox, H2, Muted, Row, styles } from '@/components/ui';
import { Tone } from '@/constants/theme';
import type { StressTest, YearEvent, YearPlan } from '@/lib/api';
import { bdt, cny, localDigits, num, shortDate } from '@/lib/format';
import type { Lang } from '@/lib/i18n';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

const CONFIDENCE_TONE = { official: 'ok', secondary: 'warn', field: 'info', assumption: 'neutral', sample: 'block' } as const;

/** Plan: the "never stuck" year. Same day-by-day rule as the live autopilot. */
export function YearPlanView() {
  const { t, lang, call } = useSession();
  const { data: yp, error } = useLoad(useCallback(() => call<YearPlan>('/plan/year'), [call]));
  const [all, setAll] = useState(false);
  if (!yp) return <ErrorBox error={error} />;
  const h = yp.headline;
  const today = yp.strategies.today;
  const truth = yp.cost_truth[0];
  const events = yp.events.filter((e) => e.type !== 'bank_closure' || e.country);
  const shown = all ? events : events.slice(0, 12);
  return (
    <>
      <DataBanner dq={yp.data_quality} />
      <Card>
        <H2>{t('yearTitle')}</H2>
        <Row style={{ alignItems: 'stretch' }}>
          <BigStat label={t('stuckToday')} value={num(h.stuck_days_today, lang)} unit={t('stuckDays')} tone="block" />
          <BigStat label={t('stuckSathi')} value={num(h.stuck_days_sathi, lang)} unit={t('stuckDays')} tone="ok" />
        </Row>
        <Muted>
          {shortDate(yp.horizon.from, lang)} → {shortDate(yp.horizon.to, lang)}
        </Muted>
      </Card>

      {today.stuck_periods.length > 0 && (
        <Card tone="block">
          <H2>{t('whyStuck')}</H2>
          {today.stuck_periods.map((p) => (
            <View key={p.from} style={{ gap: 2 }}>
              <ThemedText type="smallBold">
                {shortDate(p.from, lang)} → {shortDate(p.to, lang)} · {num(p.days, lang)} {t('stuckDays')}
              </ThemedText>
              {p.reasons.map((r) => (
                <Muted key={r}>• {r}</Muted>
              ))}
            </View>
          ))}
        </Card>
      )}

      <Card>
        <H2>{t('whereMoneyGoes')}</H2>
        {truth && (
          <>
            <Muted>
              {t('realPayment')}: {truth.bank}, {cny(truth.amount_cny, lang)} @ ৳{localDigits(truth.bdt_per_cny_paid, lang)}
            </Muted>
            <SplitBar rate={Number(truth.rate_markup_bdt)} fees={Number(truth.fee_bdt)} lang={lang} />
            {truth.fee_vs_rate && (
              <ThemedText type="smallBold">
                {t('fixedFees')} = {localDigits(Number(truth.fee_vs_rate).toFixed(1), lang)}
                {t('feeTimesRate')}
              </ThemedText>
            )}
            {truth.fee_note ? <Muted>ℹ️ {truth.fee_note}</Muted> : null}
            {truth.published_same_window && (
              <Muted>
                {t('comparedPublished')} ৳{localDigits(truth.published_same_window.avg, lang)} ({num(truth.published_same_window.sheets, lang)}{' '}
                {t('sheetsLabel')}: ৳{localDigits(truth.published_same_window.low, lang)}–{localDigits(truth.published_same_window.high, lang)})
              </Muted>
            )}
            <Muted>{truth.note}</Muted>
          </>
        )}
        {h.fees_share_today_pct && (
          <ThemedText type="small">
            {localDigits(`${Math.round(Number(h.fees_share_today_pct))}%`, lang)} {t('feesShare')}
          </ThemedText>
        )}
        <Row style={styles.between}>
          <Muted>
            {t('overheadYear')} · {t('stuckToday')}
          </Muted>
          <ThemedText type="small">
            {bdt(h.overhead_today_bdt, lang)} ({localDigits(h.overhead_today_pct, lang)}%)
          </ThemedText>
        </Row>
        <Row style={styles.between}>
          <Muted>
            {t('overheadYear')} · {t('stuckSathi')}
          </Muted>
          <ThemedText type="smallBold">
            {bdt(h.overhead_sathi_bdt, lang)} ({localDigits(h.overhead_sathi_pct, lang)}%)
          </ThemedText>
        </Row>
        {Number(h.saved_bdt) > 0 && (
          <Badge tone="ok">
            {bdt(h.saved_bdt, lang)} {t('savedSameMoney')}
          </Badge>
        )}
      </Card>

      <StressCard />

      <Card>
        <H2>{t('planTimeline')}</H2>
        {shown.map((e, i) => (
          <EventRow key={`${e.date}-${e.type}-${i}`} e={e} />
        ))}
        {events.length > 12 && <Button title={all ? t('showLess') : t('showAll')} variant="secondary" onPress={() => setAll(!all)} />}
      </Card>

      <Card>
        <H2>{t('assumptionsUsed')}</H2>
        {yp.assumptions.map((a) => (
          <Row key={a.name} style={{ alignItems: 'flex-start' }}>
            <Badge tone={CONFIDENCE_TONE[a.confidence as keyof typeof CONFIDENCE_TONE] ?? 'neutral'}>{a.confidence}</Badge>
            <ThemedText type="small" style={{ flex: 1 }}>
              <ThemedText type="smallBold">{a.name.replace(/_/g, ' ')} = {a.value}. </ThemedText>
              {a.source}
            </ThemedText>
          </Row>
        ))}
        <Muted>{yp.method}</Muted>
      </Card>
    </>
  );
}

/** Stress test: the same year re-run with messy spending, late transfers and moved holidays. */
function StressCard() {
  const { t, lang, call } = useSession();
  const { data: st } = useLoad(useCallback(() => call<StressTest>('/plan/stress'), [call]));
  if (!st) return null;
  const { today, sathi } = st.stuck_days;
  const days = (n: number) => `${num(n, lang)} ${t('daysShort')}`;
  const rows: [string, string, string][] = [
    [t('stressZero'), localDigits(`${Math.round(today.zero_share_pct)}%`, lang), localDigits(`${Math.round(sathi.zero_share_pct)}%`, lang)],
    [t('stressMedian'), days(today.median), days(sathi.median)],
    [t('stressWorst'), days(today.worst), days(sathi.worst)],
  ];
  return (
    <Card>
      <H2>{t('stressTitle')}</H2>
      <Muted>
        {num(st.runs, lang)} {t('stressRuns')}. {t('stressExplain')}
      </Muted>
      <Row style={styles.between}>
        <Muted style={{ flex: 1 }}>{t('stuckDaysHead')}</Muted>
        <ThemedText type="smallBold" style={{ width: 96, textAlign: 'right', color: Tone.block.fg }}>
          {t('stuckToday')}
        </ThemedText>
        <ThemedText type="smallBold" style={{ width: 96, textAlign: 'right', color: Tone.ok.fg }}>
          {t('stuckSathi')}
        </ThemedText>
      </Row>
      {rows.map(([label, a, b]) => (
        <Row key={label} style={{ ...styles.between, flexWrap: 'nowrap' }}>
          <ThemedText type="small" style={{ flex: 1 }}>
            {label}
          </ThemedText>
          <ThemedText type="small" style={{ width: 96, textAlign: 'right' }}>
            {a}
          </ThemedText>
          <ThemedText type="smallBold" style={{ width: 96, textAlign: 'right' }}>
            {b}
          </ThemedText>
        </Row>
      ))}
      <H2>{t('whatIfTitle')}</H2>
      {st.what_if.map((w) => {
        const more = Number(w.change_bdt);
        return (
          <View key={w.key} style={{ gap: 2 }}>
            <ThemedText type="smallBold">{t(`wi_${w.key}`)}</ThemedText>
            <Row style={{ gap: 6 }}>
              <Badge tone={w.stuck_days_sathi === 0 ? 'ok' : 'warn'}>
                {t('stuckSathi')}: {days(w.stuck_days_sathi)}
              </Badge>
              <Badge tone="block">
                {t('stuckToday')}: {days(w.stuck_days_today)}
              </Badge>
              {w.stuck_days_sathi_shield !== undefined && w.stuck_days_sathi_shield !== null && (
                <Badge tone={w.stuck_days_sathi_shield === 0 ? 'ok' : 'warn'}>
                  🛡️ {t('withShield')}: {days(w.stuck_days_sathi_shield)}
                </Badge>
              )}
              <Muted>{more > 0 ? `+${bdt(more, lang)} ${t('wiMoreForYear')}` : t('wiSameCost')}</Muted>
            </Row>
          </View>
        );
      })}
    </Card>
  );
}

function BigStat({ label, value, unit, tone }: { label: string; value: string; unit: string; tone: 'ok' | 'block' }) {
  return (
    <View style={{ flex: 1, minWidth: 140, borderRadius: 12, padding: 12, backgroundColor: Tone[tone].bg, gap: 2 }}>
      <ThemedText type="small">{label}</ThemedText>
      <ThemedText style={{ fontSize: 34, lineHeight: 40, fontWeight: '700', color: Tone[tone].fg }}>{value}</ThemedText>
      <ThemedText type="small">{unit}</ThemedText>
    </View>
  );
}

/** Rate markup vs fixed fees for one real payment, as one bar. */
function SplitBar({ rate, fees, lang }: { rate: number; fees: number; lang: Lang }) {
  const { t } = useSession();
  const total = Math.max(rate + fees, 1);
  return (
    <View style={{ gap: 6 }}>
      <View style={{ flexDirection: 'row', height: 14, borderRadius: 7, overflow: 'hidden' }}>
        <View style={{ width: `${(rate / total) * 100}%`, backgroundColor: Tone.info.fg }} />
        <View style={{ width: `${(fees / total) * 100}%`, backgroundColor: Tone.warn.fg }} />
      </View>
      <Row style={styles.between}>
        <ThemedText type="small" style={{ color: Tone.info.fg }}>
          ■ {t('rateMarkup')} {bdt(rate, lang)}
        </ThemedText>
        <ThemedText type="small" style={{ color: Tone.warn.fg }}>
          ■ {t('fixedFees')} {bdt(fees, lang)}
        </ThemedText>
      </Row>
    </View>
  );
}

function EventRow({ e }: { e: YearEvent }) {
  const { t, lang } = useSession();
  const when = shortDate(e.date, lang);
  let icon = '•';
  let text = '';
  let tone: 'ok' | 'warn' | 'block' | 'info' | 'neutral' = 'neutral';
  if (e.type === 'transfer_send') {
    icon = '🏦';
    tone = 'ok';
    text = `${t('eventTransfer')} ${cny(e.amount_cny ?? 0, lang)} (${bdt(e.total_bdt ?? 0, lang)}) → ${t('eventLands')} ${shortDate(e.lands, lang)}`;
  } else if (e.type === 'atm_bridge') {
    icon = '🏧';
    text = `${t('eventBridge')} ${cny(e.amount_cny ?? 0, lang)}`;
  } else if (e.type === 'card_stops') {
    icon = '💳';
    tone = 'warn';
    text = t('eventCardStops');
  } else if (e.type === 'tuition_send_by') {
    icon = '🎓';
    tone = 'info';
    text = `${t('eventTuition')} · ${cny(e.amount_cny ?? 0, lang)}`;
  } else if (e.type === 'bank_closure') {
    icon = e.country === 'BD' ? '🇧🇩' : '🇨🇳';
    const name = lang === 'bn' ? e.name_bn : lang === 'zh' ? e.name_zh : e.name;
    text = `${t('eventClosure')}: ${name} → ${shortDate(e.to, lang)}`;
  } else if (e.type === 'stuck_without_sathi') {
    icon = '⛔';
    tone = 'block';
    text = `${t('eventStuck')} ${num(e.days ?? 0, lang)} ${t('stuckDays')} → ${shortDate(e.to, lang)}`;
  }
  return (
    <Row style={{ alignItems: 'flex-start', flexWrap: 'nowrap' }}>
      <Muted style={{ width: 86 }}>{when}</Muted>
      <ThemedText type="small" style={{ flex: 1, color: tone === 'neutral' ? undefined : Tone[tone].fg }}>
        {icon} {text}
      </ThemedText>
      {e.type === 'bank_closure' && e.confidence && e.confidence !== 'official' && <Badge tone="neutral">{e.confidence}</Badge>}
    </Row>
  );
}
