import { router } from 'expo-router';

import { ThemedText } from '@/components/themed-text';
import { Badge, Button, Card, Meter, Muted, Row, styles } from '@/components/ui';
import type { Runway } from '@/lib/api';
import { bdt, cny, num, shortDate } from '@/lib/format';
import { useSession } from '@/lib/session';

/** Sense: how long the student's money in China lasts, what is on the way, and whether the autopilot is on. */
export function RunwayCard({ runway }: { runway: Runway }) {
  const { t, lang } = useSession();
  const days = runway.days_left ?? 0;
  const covered = runway.in_transit.length > 0 || !!runway.mandate;
  const tone = days < 3 && !covered ? 'block' : days < 10 && !runway.mandate ? 'warn' : 'ok';
  const m = runway.mandate;
  return (
    <Card tone={tone}>
      <Muted>{t('moneyInChina')}</Muted>
      <Row style={styles.between}>
        <ThemedText style={{ fontSize: 30, lineHeight: 36, fontWeight: '700' }}>{cny(runway.balance_cny, lang)}</ThemedText>
        <Badge tone={tone}>
          {num(days, lang)} {t('daysOfMoney')}
        </Badge>
      </Row>
      {runway.in_transit.map((x) => (
        <Muted key={x.arrives + x.amount_cny}>
          {t('onTheWay')}: {cny(x.amount_cny, lang)} · {t('arrivesOn')} {shortDate(x.arrives, lang)}
        </Muted>
      ))}
      {runway.runs_out_on && runway.in_transit.length === 0 && (
        <ThemedText type="smallBold">
          {t('runsOutOn')} {shortDate(runway.runs_out_on, lang)}
        </ThemedText>
      )}
      <Muted>
        {runway.card_usable ? `${t('cardWorksUntil')} ${shortDate(runway.card_works_until, lang)}` : t('cardStopped')}
      </Muted>
      {m ? (
        <>
          <Badge tone="ok" icon="sync">{t('autopilotOn')}</Badge>
          <Meter
            label={t('usedThisMonth')}
            used={Number(m.spent_in_period_bdt)}
            cap={Number(m.max_bdt_per_period)}
            display={`${bdt(m.spent_in_period_bdt, lang)} / ${bdt(m.max_bdt_per_period, lang)}`}
          />
        </>
      ) : (
        <>
          <Badge tone="neutral">{t('autopilotOff')}</Badge>
          <Button title={t('setUpMandate')} onPress={() => router.push('/family')} />
        </>
      )}
    </Card>
  );
}
