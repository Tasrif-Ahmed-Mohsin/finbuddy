import { router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { View } from 'react-native';

import { Mascot, type MascotMood } from '@/components/mascot';
import { Kicker, Panel, SpaceText } from '@/components/neo';
import { ThemedText } from '@/components/themed-text';
import { Badge, Button, Card, ErrorBox, H2, Muted, Screen } from '@/components/ui';
import { Tone } from '@/constants/theme';
import { post, type EmergencyView } from '@/lib/api';
import type { StringKey } from '@/lib/i18n';
import { confirmPresence } from '@/lib/presence';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

type Situation = 'no_money' | 'card_lost' | 'scam_call' | 'family_call';

const CHOICES: Record<'student' | 'parent', [Situation, StringKey][]> = {
  student: [
    ['no_money', 'emNoMoneyStudent'],
    ['card_lost', 'emCardLost'],
    ['scam_call', 'emScamCall'],
  ],
  parent: [
    ['family_call', 'emFamilyCall'],
    ['no_money', 'emNoMoneyParent'],
    ['scam_call', 'emScamCallParent'],
  ],
};

/** Emergency: the fastest SAFE way through. Nothing moves without the parent's fingerprint. */
export default function EmergencyScreen() {
  const { t, lang, role, call } = useSession();
  const [situation, setSituation] = useState<Situation | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { data: em, reload } = useLoad(useCallback(() => call<EmergencyView>(`/emergency?lang=${lang}`), [call, lang]));
  const openCheck = em?.safety_checks.find((c) => c.status === 'open');
  const lastCheck = em?.safety_checks[0];

  // The parent waits for the student's answer: refresh every few seconds while a check is open.
  useEffect(() => {
    if (!openCheck) return;
    const id = setInterval(reload, 4000);
    return () => clearInterval(id);
  }, [openCheck, reload]);

  async function act(path: string, message: string, needsPresence = false) {
    if (needsPresence && !(await confirmPresence(t('emImSafe')))) return;
    setBusy(true);
    setError(null);
    try {
      const r = await call<{ draft?: { id: string } | null }>(`${path}?lang=${lang}`, post({}));
      setDone(message || null);
      reload();
      if (role === 'parent' && r?.draft?.id) router.push({ pathname: '/draft/[id]', params: { id: r.draft.id } });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const calmMood: MascotMood = situation === 'scam_call' || situation === 'family_call' || situation === 'card_lost' ? 'protect' : done ? 'happy' : 'idle';
  return (
    <Screen>
      <Panel tone="red">
        <Kicker dark color={Tone.block.neon}>{t('emKicker')}</Kicker>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
          <Mascot size={88} mood={calmMood} />
          <SpaceText style={{ flex: 1 }}>{done ?? t('emSay')}</SpaceText>
        </View>
      </Panel>
      {role === 'student' && openCheck && (
        <Card tone="warn">
          <H2 icon="hand-left">{t('emFamilyAsks')}</H2>
          <Button title={t('emImSafe')} onPress={() => act(`/emergency/safety-checks/${openCheck.id}/safe`, t('emToldSafe'), true)} loading={busy} />
        </Card>
      )}
      {role === 'parent' && lastCheck && (
        <Card tone={lastCheck.status === 'safe' ? 'ok' : 'warn'}>
          <ThemedText type="smallBold">{lastCheck.status === 'safe' ? `✅ ${t('emSafeConfirmed')}` : `⏳ ${t('emWaitingSafe')}`}</ThemedText>
          {lastCheck.answered_at && <Muted>{lastCheck.answered_at.replace('T', ' ').slice(0, 16)}</Muted>}
        </Card>
      )}

      <Card tone="block">
        <H2 icon="alert-circle">{t('emWhat')}</H2>
        {CHOICES[role].map(([key, label]) => (
          <Button key={key} title={t(label)} variant={situation === key ? 'primary' : 'secondary'} onPress={() => { setSituation(key); setDone(null); }} />
        ))}
      </Card>

      {done && <Badge tone="ok">{done}</Badge>}
      <ErrorBox error={error} />

      {em && situation === 'no_money' && (
        <Card>
          <H2>{t('emFastest')}</H2>
          <ThemedText type="smallBold">{em.text.headline}</ThemedText>
          {em.text.options.map((o) => (
            <Row2 key={o.kind} text={o.text} />
          ))}
          <Button
            title={role === 'student' ? t('emAskFamily') : t('emPrepareUrgent')}
            onPress={() => act('/emergency/no-money', role === 'student' ? t('emAsked') : t('emPrepared'))}
            loading={busy}
          />
          <Muted>{t('emNothingSent')}</Muted>
        </Card>
      )}

      {em && situation === 'card_lost' && (
        <Card>
          <H2>{em.guides.card_lost.title}</H2>
          {em.card.status === 'active' ? (
            <Button title={t('emFreezeNow')} onPress={() => act('/emergency/card-lost', t('emFrozen'))} loading={busy} />
          ) : (
            <Badge tone="ok" icon="lock-closed">{t('emFrozen')}</Badge>
          )}
          <Muted>{t('cardSandboxNote')}</Muted>
          <Steps steps={em.guides.card_lost.steps} />
          {em.card.status !== 'active' && em.text.options.map((o) => <Row2 key={o.kind} text={o.text} />)}
        </Card>
      )}

      {em && (situation === 'scam_call' || situation === 'family_call') && (
        <Card tone="warn">
          <H2>{em.guides[situation].title}</H2>
          <Steps steps={em.guides[situation].steps} />
          {role === 'student' ? (
            <Button title={t('emTellSafe')} onPress={() => act('/emergency/safe', t('emToldSafe'), true)} loading={busy} />
          ) : (
            <Button title={t('emAskSafe')} onPress={() => act('/emergency/safety-checks', '')} loading={busy} />
          )}
        </Card>
      )}
    </Screen>
  );
}

function Steps({ steps }: { steps: string[] }) {
  return (
    <View style={{ gap: 6 }}>
      {steps.map((s, i) => (
        <View key={s} style={{ flexDirection: 'row', gap: 8 }}>
          <ThemedText type="smallBold" style={{ width: 18, color: Tone.block.fg }}>
            {i + 1}.
          </ThemedText>
          <ThemedText type="small" style={{ flex: 1 }}>
            {s}
          </ThemedText>
        </View>
      ))}
    </View>
  );
}

function Row2({ text }: { text: string }) {
  return (
    <View style={{ flexDirection: 'row', gap: 8 }}>
      <ThemedText type="small">•</ThemedText>
      <ThemedText type="small" style={{ flex: 1 }}>
        {text}
      </ThemedText>
    </View>
  );
}
