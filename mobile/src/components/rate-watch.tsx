import { useCallback } from 'react';
import { View } from 'react-native';
import Svg, { Polyline } from 'react-native-svg';

import { ThemedText } from '@/components/themed-text';
import { Badge, Card, H2, Muted, Row, styles } from '@/components/ui';
import { Brand, Tone } from '@/constants/theme';
import type { BankPrices } from '@/lib/api';
import { bdt, localDigits, num, shortDate } from '@/lib/format';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

const POSITION = { high: { key: 'positionHigh', tone: 'warn' }, usual: { key: 'positionUsual', tone: 'neutral' }, low: { key: 'positionLow', tone: 'ok' } } as const;

/** A bank's published CNY price against the market, and a backtest of "wait for a better day". */
export function RateWatchCard() {
  const { t, lang, call } = useSession();
  const { data: prices } = useLoad(useCallback(() => call<BankPrices>('/market/prices'), [call]));
  const rw = prices?.rate_watch;
  if (!prices || !rw) return null;
  const fee = prices.quotes.find((q) => q.quote_id === 'ebl-published')?.fee_example;
  const pct = (v: number) => localDigits(`${v.toFixed(2)}%`, lang);
  const pos = POSITION[rw.latest.position];
  const bt = rw.timing_backtest;

  const width = 300;
  const height = 110;
  const all = rw.series.flatMap((p) => [p.market, p.bank]);
  const min = Math.min(...all);
  const span = Math.max(...all) - min || 1;
  const line = (key: 'market' | 'bank') =>
    rw.series
      .map((p, i) => `${((i / (rw.series.length - 1)) * width).toFixed(1)},${(height - 6 - ((p[key] - min) / span) * (height - 12)).toFixed(1)}`)
      .join(' ');

  return (
    <Card>
      <H2>{t('rateWatchTitle')}</H2>
      <Muted>
        {num(rw.sheets, lang)} {t('publishedSheets')} · {shortDate(rw.from, lang)} → {shortDate(rw.to, lang)}
      </Muted>
      <Svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <Polyline points={line('market')} fill="none" stroke={Tone.neutral.fg} strokeWidth={1.5} />
        <Polyline points={line('bank')} fill="none" stroke={Brand.primary} strokeWidth={2} />
      </Svg>
      <Row style={styles.between}>
        <ThemedText type="small" style={{ color: Brand.primary }}>
          ■ {t('legendBank')}
        </ThemedText>
        <ThemedText type="small" style={{ color: Tone.neutral.fg }}>
          ■ {t('legendMarket')}
        </ThemedText>
      </Row>
      <Row style={styles.between}>
        <Muted style={{ flex: 1 }}>{t('markupUsually')}</Muted>
        <ThemedText type="smallBold">
          {pct(rw.markup.median)} ({pct(rw.markup.p25)}–{pct(rw.markup.p75)})
        </ThemedText>
      </Row>
      <Row style={styles.between}>
        <Muted style={{ flex: 1 }}>
          {t('markupToday')} ({shortDate(rw.latest.date, lang)})
        </Muted>
        <ThemedText type="smallBold">{pct(rw.latest.markup_pct)}</ThemedText>
        <Badge tone={pos.tone}>{t(pos.key)}</Badge>
      </Row>
      {bt.mean_saving_pct !== null && (
        <View style={{ gap: 4, padding: 10, borderRadius: 10, backgroundColor: Tone.info.bg }}>
          <ThemedText type="smallBold">{t('timingVerdict')}</ThemedText>
          <ThemedText type="small">
            {t('timingBacktest')} {bdt(bt.saving_per_lakh_bdt ?? 0, lang)} {t('perLakh')} ({num(bt.cheaper_cases, lang)}/
            {num(bt.cases, lang)} {t('timesCheaper')}).
            {fee ? ` ${t('feesOneTransfer')} ${bdt(fee.total_bdt, lang)}.` : ''}
          </ThemedText>
          <Muted>{t('timingConclusion')}</Muted>
        </View>
      )}
    </Card>
  );
}
