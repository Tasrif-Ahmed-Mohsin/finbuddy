import { useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';

import { ListenButton } from '@/components/listen-button';
import { ThemedText } from '@/components/themed-text';
import { Badge, Banner, Button, Card, ErrorBox, H1, H2, Muted, Row, Screen, styles } from '@/components/ui';
import type { Draft } from '@/lib/api';
import { bdt, cny, num } from '@/lib/format';
import { STATUS_TONE } from '@/lib/labels';
import { confirmPresence } from '@/lib/presence';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

const CHECK_ICON = { pass: '✓', warn: '!', block: '✕' } as const;

export default function DraftScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { t, lang, role, call } = useSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const { data: d, error: loadError, reload } = useLoad(useCallback(() => call<Draft>(`/drafts/${id}`), [call, id]));

  async function approve() {
    if (!d) return;
    const ok = await confirmPresence(`${t('approve')}: ${bdt(d.total_bdt, lang)} → ${d.payee_name}`);
    if (!ok) return;
    setBusy(true);
    setError(null);
    try {
      await call(`/drafts/${d.id}/approve`, { method: 'POST' });
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function execute() {
    if (!d) return;
    setBusy(true);
    setError(null);
    try {
      await call(`/drafts/${d.id}/execute`, { method: 'POST' });
      setDone(t('executed'));
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!d) {
    return (
      <Screen>
        <ErrorBox error={loadError} />
      </Screen>
    );
  }

  const blockedReasons = d.checks.filter((c) => !c.passed && c.severity === 'block');
  const canApprove = d.required_approvers.includes(role) && !d.approved_by.includes(role) && (d.status === 'draft' || d.status === 'approved');
  return (
    <Screen>
      <H1>{t('draft')}</H1>
      <Badge tone={STATUS_TONE[d.status]}>{d.status}</Badge>
      {d.status === 'blocked' && (
        <Banner tone="block">
          {t('blocked')}: {blockedReasons.map((c) => c.message).join(' · ')}
        </Banner>
      )}
      {done && <Banner tone="ok">{done}</Banner>}
      <ErrorBox error={error} />

      {d.summary && (
        <Card tone="info">
          <H2>{t('whatYouApprove')}</H2>
          <ThemedText>{d.summary[lang]}</ThemedText>
          <ListenButton text={d.summary[lang]} lang={lang} />
          <Muted>{t('readAloudHint')}</Muted>
        </Card>
      )}

      <Card>
        <Row style={styles.between}>
          <Muted>{t('payee')}</Muted>
          <ThemedText type="smallBold">{d.payee_name}</ThemedText>
        </Row>
        <Row style={styles.between}>
          <Muted>{t('amount')}</Muted>
          <ThemedText type="smallBold">{cny(d.amount_cny, lang)}</ThemedText>
        </Row>
        <Row style={styles.between}>
          <Muted>{t('total')}</Muted>
          <ThemedText type="smallBold">{bdt(d.total_bdt, lang)}</ThemedText>
        </Row>
        {d.rate_bdt_per_cny && (
          <Row style={styles.between}>
            <Muted>{t('rate')}</Muted>
            <ThemedText type="small">৳{num(d.rate_bdt_per_cny, lang)} / ¥1</ThemedText>
          </Row>
        )}
        {d.withdrawals.length > 0 && <Muted>ATM: {d.withdrawals.map((w) => cny(w, lang)).join(' + ')}</Muted>}
        {d.memo ? <Muted>“{d.memo}”</Muted> : null}
      </Card>

      <Card>
        <H2>{t('checks')}</H2>
        {d.checks.map((c) => {
          const kind = c.passed ? (c.severity === 'warn' ? 'warn' : 'pass') : c.severity === 'block' ? 'block' : 'warn';
          const tone = kind === 'pass' ? 'ok' : kind;
          return (
            <Row key={c.id} style={{ alignItems: 'flex-start' }}>
              <Badge tone={tone}>{CHECK_ICON[kind]}</Badge>
              <ThemedText type="small" style={{ flex: 1 }}>
                {c.message}
              </ThemedText>
            </Row>
          );
        })}
      </Card>

      <Card>
        <Row>
          <Muted>{t('needs')}:</Muted>
          {d.required_approvers.map((r) => (
            <Badge key={r} tone={d.approved_by.includes(r) ? 'ok' : 'neutral'}>
              {d.approved_by.includes(r) ? '✓ ' : ''}
              {t(r)}
            </Badge>
          ))}
        </Row>
        {canApprove && <Button title={t('approve')} onPress={approve} loading={busy} />}
        {!canApprove && d.status === 'draft' && (
          <Banner tone="info">
            {t('waitingFor')}: {d.required_approvers.filter((r) => !d.approved_by.includes(r)).map((r) => t(r)).join(', ')}
          </Banner>
        )}
        {d.status === 'approved' && <Button title={t('execute')} onPress={execute} loading={busy} />}
      </Card>
    </Screen>
  );
}
