import { router } from 'expo-router';
import { useCallback } from 'react';
import { Pressable } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Badge, Banner, Card, ErrorBox, H1, H2, Muted, Row, Screen, styles } from '@/components/ui';
import type { AuditEntry, Draft } from '@/lib/api';
import { bdt, cny, num, shortDate } from '@/lib/format';
import { KIND_LABEL, STATUS_TONE } from '@/lib/labels';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

export default function ActivityScreen() {
  const { t, lang, call } = useSession();
  const { data, error, loading, reload } = useLoad(
    useCallback(async () => {
      const [drafts, audit] = await Promise.all([
        call<Draft[]>('/drafts'),
        call<{ verify: { valid: boolean; entries: number }; entries: AuditEntry[] }>('/audit?limit=60'),
      ]);
      return { drafts, audit };
    }, [call]),
  );

  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <H1>{t('tabActivity')}</H1>
      <ErrorBox error={error} />
      {data && (
        <>
          <H2>{t('approvals')}</H2>
          {data.drafts.length === 0 && <Muted>—</Muted>}
          {data.drafts.map((d) => (
            <Pressable key={d.id} onPress={() => router.push({ pathname: '/draft/[id]', params: { id: d.id } })}>
              <Card tone={STATUS_TONE[d.status]}>
                <Row style={styles.between}>
                  <ThemedText type="smallBold">{KIND_LABEL[d.kind]}</ThemedText>
                  <Badge tone={STATUS_TONE[d.status]}>{d.status}</Badge>
                </Row>
                <Row style={styles.between}>
                  <ThemedText>{cny(d.amount_cny, lang)}</ThemedText>
                  <ThemedText type="smallBold">{bdt(d.total_bdt, lang)}</ThemedText>
                </Row>
                <Muted>
                  {d.payee_name} · {t('approvedBy')} {num(d.approved_by.length, lang)}/{num(d.required_approvers.length, lang)}
                </Muted>
              </Card>
            </Pressable>
          ))}

          <H2>{t('auditLog')}</H2>
          <Banner tone={data.audit.verify.valid ? 'ok' : 'block'}>
            {data.audit.verify.valid ? t('chainValid') : t('chainBroken')} ({num(data.audit.verify.entries, lang)})
          </Banner>
          {data.audit.entries.map((e) => (
            <Card key={e.seq}>
              <Row style={styles.between}>
                <ThemedText type="smallBold">
                  #{num(e.seq, lang)} {e.event}
                </ThemedText>
                <Badge tone={e.event.includes('denied') || e.event.includes('blocked') ? 'block' : 'neutral'}>{e.permission_level}</Badge>
              </Row>
              <Muted>
                {e.actor} · {shortDate(e.sim_time ?? e.ts, lang)} · {e.hash.slice(0, 10)}…
              </Muted>
              <ThemedText type="code" numberOfLines={3}>
                {JSON.stringify(e.data)}
              </ThemedText>
            </Card>
          ))}
        </>
      )}
    </Screen>
  );
}
