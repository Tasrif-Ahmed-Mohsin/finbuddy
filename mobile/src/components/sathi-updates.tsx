import { router } from 'expo-router';
import { useCallback } from 'react';

import { ThemedText } from '@/components/themed-text';
import { Badge, Button, Card, ErrorBox, H2, Muted, Row, styles } from '@/components/ui';
import type { InboxSummary, InboxTxn, Insight } from '@/lib/api';
import { bdt, cny, shortDate } from '@/lib/format';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

const TONE = { alert: 'block', warn: 'warn', info: 'info' } as const;

export function InsightCard({ insight }: { insight: Insight }) {
  const { t, lang } = useSession();
  const a = insight.action;
  return (
    <Card tone={TONE[insight.severity]}>
      <Row style={styles.between}>
        <ThemedText type="smallBold" style={{ flex: 1 }}>
          {insight.title}
        </ThemedText>
        <Badge tone={TONE[insight.severity]}>{insight.severity}</Badge>
      </Row>
      <ThemedText type="small">{insight.body}</ThemedText>
      {insight.savings_bdt && Number(insight.savings_bdt) > 0 && (
        <Badge tone="ok">
          {t('couldSave')} {bdt(insight.savings_bdt, lang)}
        </Badge>
      )}
      {a?.screen === 'plan' && (
        <Button title={t('planIt')} variant="secondary" onPress={() => router.push({ pathname: '/plan', params: { mode: a.mode ?? 'living' } })} />
      )}
    </Card>
  );
}

export function SathiUpdates() {
  const { t, lang, call } = useSession();
  const { data, error } = useLoad(
    useCallback(async () => {
      const [ins, txns] = await Promise.all([
        call<{ insights: Insight[]; summary: InboxSummary }>(`/insights?lang=${lang}`),
        call<InboxTxn[]>('/inbox/transactions?limit=12'),
      ]);
      return { ...ins, txns };
    }, [call, lang]),
  );

  return (
    <>
      <ErrorBox error={error} />
      {data && (
        <>
          <Card>
            <Row style={styles.between}>
              <Muted>{t('spentThisMonth')}</Muted>
              <ThemedText type="smallBold">{bdt(data.summary.spent_bdt, lang)}</ThemedText>
            </Row>
            <Row style={styles.between}>
              <Muted>{t('feesThisMonth')}</Muted>
              <ThemedText type="smallBold">{bdt(data.summary.fees_bdt, lang)}</ThemedText>
            </Row>
          </Card>
          {data.insights.length === 0 && <Muted>{t('noUpdates')}</Muted>}
          {data.insights.map((i) => (
            <InsightCard key={i.id} insight={i} />
          ))}
          {data.txns.length > 0 && <H2>{t('recentTxns')}</H2>}
          {data.txns.map((x) => (
            <Card key={x.id}>
              <Row style={styles.between}>
                <ThemedText type="smallBold" style={{ flex: 1 }}>
                  {x.counterparty ?? x.kind} {x.counted_on_card ? '· 💳' : ''}
                </ThemedText>
                <ThemedText type="smallBold" style={{ color: x.direction === 'credit' ? '#15803D' : undefined }}>
                  {x.direction === 'credit' ? '+' : x.direction === 'debit' ? '−' : ''}
                  {x.currency === 'CNY' ? cny(x.amount, lang) : bdt(x.amount, lang)}
                </ThemedText>
              </Row>
              <Muted>
                {x.sender} · {shortDate(x.received_at, lang)} · {x.parser === 'llm' ? 'AI' : 'rules'}
                {x.bdt_is_estimate ? ` · ≈${bdt(x.bdt_value, lang)}` : ''}
              </Muted>
              {x.notes.map((n) => (
                <Muted key={n}>⚠ {n}</Muted>
              ))}
            </Card>
          ))}
        </>
      )}
    </>
  );
}
