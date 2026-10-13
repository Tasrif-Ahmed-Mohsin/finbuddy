import { router } from 'expo-router';
import { useCallback, useState } from 'react';
import { Pressable } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Badge, Banner, Button, Card, ErrorBox, H1, H2, Muted, Row, Screen, styles } from '@/components/ui';
import type { AuditEntry, Receipt } from '@/lib/api';
import { bdt, cny, num, shortDate } from '@/lib/format';
import { KIND_LABEL } from '@/lib/labels';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

/** Prove: a receipt for every payment (who or what allowed it), the tamper-evident log, the payment passport. */
export default function ProofScreen() {
  const { t, lang, call } = useSession();
  const [allLog, setAllLog] = useState(false);
  const { data, error, loading, reload } = useLoad(
    useCallback(async () => {
      const [receipts, audit] = await Promise.all([
        call<Receipt[]>('/receipts'),
        call<{ verify: { valid: boolean; entries: number }; entries: AuditEntry[] }>('/audit?limit=60'),
      ]);
      return { receipts, audit };
    }, [call]),
  );

  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <H1>{t('tabProof')}</H1>
      <Muted>{t('proofIntro')}</Muted>
      <ErrorBox error={error} />
      {data && (
        <>
          <Banner tone={data.audit.verify.valid ? 'ok' : 'block'}>
            {data.audit.verify.valid ? t('chainValid') : t('chainBroken')} ({num(data.audit.verify.entries, lang)})
          </Banner>

          <H2>{t('receiptsTitle')}</H2>
          {data.receipts.length === 0 && <Muted>{t('noPayments')}</Muted>}
          {data.receipts.map((r) => (
            <ReceiptCard key={r.draft.id} r={r} />
          ))}

          <Card tone="info">
            <H2>{t('buildCredit')}</H2>
            <Muted>{t('passportIntro')}</Muted>
            <Button title={t('passport')} onPress={() => router.push('/passport')} />
          </Card>

          <H2>{t('auditLog')}</H2>
          {(allLog ? data.audit.entries : data.audit.entries.slice(0, 12)).map((e) => (
            <Card key={e.seq}>
              <Row style={styles.between}>
                <ThemedText type="smallBold">
                  #{num(e.seq, lang)} {e.event}
                </ThemedText>
                <Badge tone={e.event.includes('denied') || e.event.includes('blocked') ? 'block' : e.permission_level === 'MANDATE' ? 'ok' : 'neutral'}>
                  {e.permission_level}
                </Badge>
              </Row>
              <Muted>
                {e.actor} · {shortDate(e.sim_time ?? e.ts, lang)} · {e.hash.slice(0, 10)}…
              </Muted>
              <ThemedText type="code" numberOfLines={3}>
                {JSON.stringify(e.data)}
              </ThemedText>
            </Card>
          ))}
          {data.audit.entries.length > 12 && (
            <Button title={allLog ? t('showLess') : t('showAll')} variant="secondary" onPress={() => setAllLog(!allLog)} />
          )}
        </>
      )}
    </Screen>
  );
}

function ReceiptCard({ r }: { r: Receipt }) {
  const { t, lang } = useSession();
  const a = r.authority;
  const byMandate = a?.type === 'mandate';
  return (
    <Pressable onPress={() => router.push({ pathname: '/draft/[id]', params: { id: r.draft.id } })}>
      <Card tone={byMandate ? 'ok' : 'info'}>
        <Row style={styles.between}>
          <ThemedText type="smallBold" style={{ flex: 1 }}>
            {byMandate ? '🤖' : '✍️'} {KIND_LABEL[r.draft.kind]} → {r.draft.payee_name}
          </ThemedText>
          <ThemedText type="smallBold">{cny(r.draft.amount_cny, lang)}</ThemedText>
        </Row>
        <Muted>
          {bdt(r.draft.total_bdt, lang)} · {r.sent ? shortDate(r.sent.sim_time, lang) : ''}
          {r.landed ? ` · ${t('landedOn')} ${shortDate(r.landed.sim_time, lang)}` : r.sent?.arrives_at ? ` · ${t('arrivesOn')} ${shortDate(r.sent.arrives_at, lang)}` : ''}
        </Muted>
        {a?.type === 'mandate' && (
          <Muted>
            {t('underMandate')} ({a.signed_by.map((s) => t(s)).join(' + ')}) · #{a.proposal_hash?.slice(0, 10)}
          </Muted>
        )}
        {a?.type === 'approvals' && (
          <Muted>
            {t('approvedByPeople')}: {a.approved_by.map((s) => t(s)).join(' + ')}
          </Muted>
        )}
        <Row>
          <Badge tone="ok">{a?.level ?? '–'}</Badge>
          {r.draft.checks.filter((c) => c.passed).length > 0 && (
            <Badge tone="neutral">
              ✓ {num(r.draft.checks.filter((c) => c.passed).length, lang)}/{num(r.draft.checks.length, lang)} {t('checks')}
            </Badge>
          )}
          {r.sent && (
            <Badge tone="neutral">
              {t('logEntry')} #{num(r.sent.seq, lang)}
            </Badge>
          )}
        </Row>
      </Card>
    </Pressable>
  );
}
