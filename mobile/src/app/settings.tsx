import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { useCallback, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { Mascot } from '@/components/mascot';
import { Seal } from '@/components/neo';
import { ThemedText } from '@/components/themed-text';
import { Colors, Space } from '@/constants/theme';
import { WhatsAppCard } from '@/components/whatsapp-card';
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

  async function resetDemo() {
    setError(null);
    try {
      await call('/sandbox/reset', post({}));
      reload();
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
        <Pressable accessibilityRole="button" onPress={() => router.push('/buddy')} style={({ pressed }) => [styles.row, { flexWrap: 'nowrap' }, pressed && { opacity: 0.8 }]}>
          <Mascot size={64} mood="happy" />
          <View style={{ flex: 1, gap: 2 }}>
            <ThemedText type="smallBold">{t('meetSathi')}</ThemedText>
            <Muted>{t('settingsBuddy')}</Muted>
          </View>
          <Ionicons name="chevron-forward" size={20} color={Colors.light.textTertiary} />
        </Pressable>
      </Card>

      <Card>
        <Pressable accessibilityRole="button" onPress={() => router.push('/judge')} style={({ pressed }) => [styles.row, { flexWrap: 'nowrap' }, pressed && { opacity: 0.8 }]}>
          <Seal ok size={56} />
          <View style={{ flex: 1, gap: 2 }}>
            <ThemedText type="smallBold">{t('judgeTitle')}</ThemedText>
            <Muted>{t('settingsJudge')}</Muted>
          </View>
          <Ionicons name="chevron-forward" size={20} color={Colors.light.textTertiary} />
        </Pressable>
      </Card>

      {(
        [
          { href: '/story', icon: 'play', title: 'storyOpen', sub: 'storyTileBody' },
          { href: '/welcome', icon: 'sparkles', title: 'settingsWelcome', sub: 'settingsWelcomeSub' },
          { href: '/banks', icon: 'business', title: 'settingsBanks', sub: 'settingsBanksSub' },
          { href: '/privacy', icon: 'lock-closed', title: 'settingsPrivacy', sub: 'settingsPrivacySub' },
        ] as const
      ).map((l) => (
        <Card key={l.href}>
          <Pressable accessibilityRole="button" onPress={() => router.push(l.href)} style={({ pressed }) => [styles.row, { flexWrap: 'nowrap' }, pressed && { opacity: 0.8 }]}>
            <View style={local.linkIcon}>
              <Ionicons name={l.icon} size={24} color={Space.neon} />
            </View>
            <View style={{ flex: 1, gap: 2 }}>
              <ThemedText type="smallBold">{t(l.title)}</ThemedText>
              <Muted>{t(l.sub)}</Muted>
            </View>
            <Ionicons name="chevron-forward" size={20} color={Colors.light.textTertiary} />
          </Pressable>
        </Card>
      ))}

      <Card>
        <Field label={t('server')} value={server} onChangeText={setServer} autoCapitalize="none" autoCorrect={false} />
        <Button title={t('testConnection')} variant="secondary" onPress={test} />
        {status && <Banner tone="ok">{status}</Banner>}
      </Card>
      <ErrorBox error={error} />

      <WhatsAppCard />

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
        <Button title={t('resetDemo')} variant="secondary" onPress={resetDemo} />
        <Muted>{t('resetDemoHint')}</Muted>
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

const local = StyleSheet.create({
  linkIcon: { width: 56, height: 56, borderRadius: 18, backgroundColor: Space.bg, alignItems: 'center', justifyContent: 'center', boxShadow: '0px 0px 12px rgba(77, 163, 255, 0.35)' },
});
