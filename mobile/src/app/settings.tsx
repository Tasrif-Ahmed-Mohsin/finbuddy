import { useCallback, useState } from 'react';

import { ThemedText } from '@/components/themed-text';
import { Badge, Banner, Button, Card, ErrorBox, Field, H1, H2, Muted, Row, Screen, Segmented, styles } from '@/components/ui';
import { post, type Accounts, type CorridorParam, type Role, type Sources } from '@/lib/api';
import { shortDate } from '@/lib/format';
import type { Lang } from '@/lib/i18n';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

const CONFIDENCE_TONE = { official: 'ok', secondary: 'warn', field: 'info', assumption: 'neutral', sample: 'block' } as const;

export default function SettingsScreen() {
  const { t, lang, setLang, role, setRole, apiBase, setApiBase, call } = useSession();
  const [server, setServer] = useState(apiBase);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data, reload } = useLoad(
    useCallback(async () => {
      const [accounts, corridor, sources, agent] = await Promise.all([
        call<Accounts>('/accounts'),
        call<{ name: string; reviewed: string; params: Record<string, CorridorParam> }>('/corridor'),
        call<Sources>('/inbox/sources'),
        call<{ llm: boolean; provider: string | null; model: string | null }>('/agent/status'),
      ]);
      return { accounts, corridor, sources, agent };
    }, [call]),
  );

  async function test() {
    setError(null);
    setApiBase(server.replace(/\/$/, ''));
    try {
      const res = await fetch(`${server.replace(/\/$/, '')}/health`);
      setStatus(res.ok ? t('connected') : `HTTP ${res.status}`);
    } catch {
      setStatus(null);
      setError(`Cannot reach ${server}`);
    }
  }

  async function seedDemo() {
    setError(null);
    try {
      const r = await call<{ ingested: number; kept: number }>('/inbox/demo/seed', { method: 'POST' });
      setStatus(`${r.kept}/${r.ingested} demo messages kept`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function advance(days: number) {
    setError(null);
    try {
      await call('/sandbox/advance', post({ days }));
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <Screen>
      <H1>{t('tabSettings')}</H1>
      <Card>
        <Muted>{t('role')}</Muted>
        <Segmented<Role> value={role} onChange={setRole} options={[{ value: 'parent', label: t('parent') }, { value: 'student', label: t('student') }]} />
        <Muted>{t('language')}</Muted>
        <Segmented<Lang>
          value={lang}
          onChange={setLang}
          options={[
            { value: 'en', label: 'English' },
            { value: 'bn', label: 'বাংলা' },
            { value: 'zh', label: '中文' },
          ]}
        />
      </Card>

      <Card>
        <Field label={t('server')} value={server} onChangeText={setServer} autoCapitalize="none" autoCorrect={false} />
        <Button title={t('testConnection')} variant="secondary" onPress={test} />
        {status && <Banner tone="ok">{status}</Banner>}
      </Card>
      <ErrorBox error={error} />

      {data && (
        <Card>
          <H2>{t('sources')}</H2>
          <Badge tone={data.agent.llm ? 'ok' : 'neutral'}>
            {data.agent.llm ? `${t('aiOn')}: ${data.agent.provider} ${data.agent.model}` : t('aiOff')}
          </Badge>
          {(['share_paste', 'webhook', 'email', 'sms_auto_read'] as const).map((k) => (
            <Row key={k} style={{ alignItems: 'flex-start' }}>
              <Badge tone={data.sources[k].available ? 'ok' : 'neutral'}>{data.sources[k].available ? '✓' : '–'}</Badge>
              <ThemedText type="small" style={{ flex: 1 }}>
                <ThemedText type="smallBold">{k.replace(/_/g, ' ')}: </ThemedText>
                {data.sources[k].note}
              </ThemedText>
            </Row>
          ))}
          <H2>{t('privacy')}</H2>
          {data.sources.privacy.map((p) => (
            <Muted key={p}>🔒 {p}</Muted>
          ))}
          <Button title={t('loadDemo')} variant="secondary" onPress={seedDemo} />
          <Muted>{t('demoNote')}</Muted>
        </Card>
      )}

      <Card>
        <H2>{t('sandboxClock')}</H2>
        <Muted>{data ? shortDate(data.accounts.now, lang) : '…'}</Muted>
        <Row>
          {[1, 7, 30].map((d) => (
            <Button key={d} title={`+${d}d`} variant="secondary" onPress={() => advance(d)} />
          ))}
        </Row>
      </Card>

      {data && (
        <Card>
          <H2>{t('rulePack')}</H2>
          <Muted>
            {data.corridor.name} · reviewed {data.corridor.reviewed}
          </Muted>
          {Object.entries(data.corridor.params).map(([name, p]) => (
            <Card key={name} style={{ padding: 10 }}>
              <Row style={styles.between}>
                <ThemedText type="smallBold" style={{ flex: 1 }}>
                  {name}
                </ThemedText>
                <ThemedText type="smallBold">{p.value}</ThemedText>
              </Row>
              <Badge tone={CONFIDENCE_TONE[p.confidence as keyof typeof CONFIDENCE_TONE] ?? 'neutral'}>{p.confidence}</Badge>
              <Muted>{p.source}</Muted>
            </Card>
          ))}
        </Card>
      )}
    </Screen>
  );
}
