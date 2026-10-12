import { router } from 'expo-router';
import { useCallback } from 'react';

import { CardControls } from '@/components/card-controls';
import { DataBanner } from '@/components/data-banner';
import { InsightCard } from '@/components/sathi-updates';
import { ThemedText } from '@/components/themed-text';
import { Badge, Button, Card, ErrorBox, H1, H2, Meter, Muted, Row, Screen, Segmented, styles } from '@/components/ui';
import type { Accounts, Insight, Role, Timeline, TimelineItem } from '@/lib/api';
import { bdt, cny, num, shortDate } from '@/lib/format';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

export default function HomeScreen() {
  const { t, lang, role, setRole, call } = useSession();
  const { data, error, loading, reload } = useLoad(
    useCallback(async () => {
      const [timeline, accounts, ins] = await Promise.all([
        call<Timeline>('/timeline'),
        call<Accounts>('/accounts'),
        call<{ insights: Insight[] }>(`/insights?lang=${lang}`),
      ]);
      return { timeline, accounts, insights: ins.insights };
    }, [call, lang]),
  );

  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <H1>{t('appName')}</H1>
      <Muted>{t('tagline')}</Muted>

      <Card>
        <Muted>{t('youAre')}</Muted>
        <Segmented<Role>
          value={role}
          onChange={setRole}
          options={[
            { value: 'parent', label: t('parent') },
            { value: 'student', label: t('student') },
          ]}
        />
      </Card>

      <ErrorBox error={error} />
      <DataBanner dq={data?.timeline.data_quality} />

      {data && (
        <>
          {data.insights.length > 0 && (
            <>
              <H2>{t('updates')}</H2>
              {data.insights.slice(0, 2).map((i) => (
                <InsightCard key={i.id} insight={i} onChanged={reload} />
              ))}
              {data.insights.length > 2 && (
                <Button title={`${t('updates')} (${num(data.insights.length, lang)})`} variant="secondary" onPress={() => router.push('/assistant')} />
              )}
            </>
          )}
          <H2>{t('upcoming')}</H2>
          {data.timeline.items.map((item) => (
            <TimelineCard key={item.type} item={item} />
          ))}

          <Card>
            <H2>{t('cardLimits')}</H2>
            <Meter
              label={t('transactions')}
              used={data.timeline.card_usage.tx_used}
              cap={data.timeline.card_usage.tx_cap}
              display={`${num(data.timeline.card_usage.tx_used, lang)} / ${num(data.timeline.card_usage.tx_cap, lang)}`}
            />
            <Meter
              label={t('amountCharged')}
              used={Number(data.timeline.card_usage.bdt_used)}
              cap={Number(data.timeline.card_usage.bdt_cap)}
              display={`${bdt(data.timeline.card_usage.bdt_used, lang)} / ${bdt(data.timeline.card_usage.bdt_cap, lang)}`}
            />
          </Card>

          <CardControls card={data.timeline.card} onChange={reload} />

          {data.accounts.pending.length > 0 && (
            <Card tone="info">
              <H2>{t('inTransit')}</H2>
              {data.accounts.pending.map((p) => (
                <Row key={p.id} style={styles.between}>
                  <ThemedText>{cny(p.amount_cny, lang)}</ThemedText>
                  <Muted>
                    {t('arrives')} {shortDate(p.arrives_at, lang)}
                  </Muted>
                </Row>
              ))}
            </Card>
          )}

          <Card>
            <H2>{t('balances')}</H2>
            {data.accounts.accounts.map((a) => (
              <Row key={a.id} style={styles.between}>
                <Muted style={{ flex: 1 }}>{a.label}</Muted>
                <ThemedText type="smallBold">{a.currency === 'BDT' ? bdt(a.balance, lang) : cny(a.balance, lang)}</ThemedText>
              </Row>
            ))}
            <Muted>
              {t('sandboxClock')}: {shortDate(data.accounts.now, lang)}
            </Muted>
          </Card>
        </>
      )}
    </Screen>
  );
}

function TimelineCard({ item }: { item: TimelineItem }) {
  const { t, lang } = useSession();
  if (item.type === 'tuition_due') {
    const days = item.days_to_send_by ?? 0;
    const tone = days < 0 ? 'block' : days <= 2 ? 'warn' : 'ok';
    return (
      <Card tone={tone}>
        <Row style={styles.between}>
          <H2>{t('tuition')}</H2>
          <ThemedText type="smallBold">{cny(item.amount_cny ?? 0, lang)}</ThemedText>
        </Row>
        <Muted>
          {t('due')}: {shortDate(item.due, lang)} · {t('sendBy')}: {shortDate(item.send_by, lang)}
        </Muted>
        <Badge tone={tone}>
          {num(days, lang)} {t('daysLeft')}
        </Badge>
        <Button title={t('planIt')} onPress={() => router.push({ pathname: '/plan', params: { mode: 'tuition' } })} />
      </Card>
    );
  }
  if (item.type === 'living_money') {
    return (
      <Card>
        <Row style={styles.between}>
          <H2>{t('living')}</H2>
          <ThemedText type="smallBold">{cny(item.amount_cny ?? 0, lang)}</ThemedText>
        </Row>
        <Button title={t('planIt')} variant="secondary" onPress={() => router.push({ pathname: '/plan', params: { mode: 'living' } })} />
      </Card>
    );
  }
  const title = item.type === 'endorsement_expiry' ? t('endorsement') : t('studentFile');
  const days = item.days_left ?? 0;
  const tone = days < 0 ? 'block' : item.warn ? 'warn' : 'ok';
  return (
    <Card tone={tone}>
      <H2>{title}</H2>
      <Muted>
        {t('expires')}: {shortDate(item.due, lang)}
      </Muted>
      <Row>
        <Badge tone={tone}>
          {num(days, lang)} {t('daysLeft')}
        </Badge>
        {item.warn && <Badge tone="warn">{t('renewSoon')}</Badge>}
      </Row>
      <Button title={t('renewalPlan')} variant={item.warn ? 'primary' : 'secondary'}
        onPress={() => router.push({ pathname: '/renewal/[item]', params: { item: item.type } })} />
    </Card>
  );
}
