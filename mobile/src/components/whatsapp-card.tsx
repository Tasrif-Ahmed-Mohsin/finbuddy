import { useCallback, useState } from 'react';

import { ThemedText } from '@/components/themed-text';
import { Badge, Banner, Button, Card, ErrorBox, Field, H2, Muted, Row, styles } from '@/components/ui';
import { post } from '@/lib/api';
import { shortDate } from '@/lib/format';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

type WaStatus = {
  mode: 'off' | 'dry_run' | 'live';
  configured: boolean;
  recipient: string | null;
  lang: string;
  rules: string[];
  outbox: { at: string; to: string; kind: string; key: string; mode: string; status: string; detail: string }[];
};

const MODE_TONE = { off: 'neutral', dry_run: 'info', live: 'ok' } as const;
const STATUS_TONE: Record<string, 'ok' | 'info' | 'warn' | 'block'> = {
  sent: 'ok', sent_template: 'ok', logged: 'info', rate_limited: 'warn', failed: 'block',
};

/** WhatsApp alerts for the parent: notifications only (approvals stay in the app with fingerprint). */
export function WhatsAppCard() {
  const { t, lang, call } = useSession();
  const [number, setNumber] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { data, reload } = useLoad(useCallback(() => call<WaStatus>('/notify/whatsapp'), [call]));

  async function save() {
    setError(null);
    try {
      await call('/notify/whatsapp/recipient', post({ number, lang }));
      setMsg(t('waSaved'));
      setNumber('');
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function test() {
    setError(null);
    try {
      const r = await call<{ status: string; detail: string }>('/notify/whatsapp/test', { method: 'POST' });
      setMsg(`${t('waTest')}: ${r.status}${r.detail && r.status !== 'logged' ? ` (${r.detail})` : ''}`);
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  if (!data) return null;
  const modeLabel = data.mode === 'live' ? t('waLive') : data.mode === 'dry_run' ? t('waDryRun') : t('waOff');
  return (
    <Card>
      <H2>{t('waTitle')}</H2>
      <Row>
        <Badge tone={MODE_TONE[data.mode]}>{modeLabel}</Badge>
        {data.recipient && <Badge tone="neutral">{data.recipient}</Badge>}
      </Row>
      <Muted>{t('waIntro')}</Muted>
      <Field label={t('waNumber')} value={number} onChangeText={setNumber} placeholder="+8801712345678" keyboardType="phone-pad" />
      <Row>
        <Button title={t('waSave')} onPress={save} disabled={number.trim().length < 8} />
        <Button title={t('waTest')} variant="secondary" onPress={test} disabled={!data.recipient || data.mode === 'off'} />
      </Row>
      {msg && <Banner tone="ok">{msg}</Banner>}
      <ErrorBox error={error} />
      {data.outbox.slice(0, 5).map((e, i) => (
        <Card key={`${e.at}-${i}`} style={{ padding: 10 }}>
          <Row style={styles.between}>
            <ThemedText type="smallBold">
              {e.kind} · {e.key}
            </ThemedText>
            <Badge tone={STATUS_TONE[e.status] ?? 'neutral'}>{e.status}</Badge>
          </Row>
          <Muted>
            {shortDate(e.at, lang)} → {e.to}
          </Muted>
          {e.detail ? (
            <ThemedText type="small" numberOfLines={6}>
              {e.detail}
            </ThemedText>
          ) : null}
        </Card>
      ))}
      {data.rules.map((r) => (
        <Muted key={r}>🔒 {r}</Muted>
      ))}
    </Card>
  );
}
