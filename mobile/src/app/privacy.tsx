import Ionicons from '@expo/vector-icons/Ionicons';
import * as Clipboard from 'expo-clipboard';
import { router } from 'expo-router';
import { useCallback, useState } from 'react';
import { Alert, Platform, Pressable, StyleSheet, Switch, View } from 'react-native';

import { Kicker, Panel, SpaceText } from '@/components/neo';
import { ThemedText } from '@/components/themed-text';
import { Badge, Banner, Button, Card, ErrorBox, H1, H2, Muted, Row, Screen } from '@/components/ui';
import { Brand, Space } from '@/constants/theme';
import { post, type PrivacyView } from '@/lib/api';
import { num } from '@/lib/format';
import type { StringKey } from '@/lib/i18n';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

const ICON = { deepseek: 'sparkles', whatsapp: 'logo-whatsapp', banks: 'business' } as const;

function confirmDelete(message: string): Promise<boolean> {
  if (Platform.OS === 'web') return Promise.resolve(globalThis.confirm?.(message) ?? true);
  return new Promise((resolve) =>
    Alert.alert('Sathi', message, [
      { text: 'Cancel', style: 'cancel', onPress: () => resolve(false) },
      { text: 'OK', style: 'destructive', onPress: () => resolve(true) },
    ]),
  );
}

/**
 * Your data (PIPL Art. 17, 39, 44-47): what Sathi keeps and why, where it goes (DeepSeek is in China), a copy of it,
 * deleting it, and the AI switch (off = the rules answer and nothing is sent to the AI).
 */
export default function PrivacyScreen() {
  const { t, lang, call } = useSession();
  const { data, error, reload } = useLoad(useCallback(() => call<PrivacyView>('/privacy'), [call]));
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function act(fn: () => Promise<void>) {
    setBusy(true);
    setErr(null);
    try {
      await fn();
      reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const setAi = (allowed: boolean) => act(async () => void (await call('/privacy/ai', post({ allowed }))));
  const exportData = () =>
    act(async () => {
      const copy = await call<object>('/privacy/export');
      await Clipboard.setStringAsync(JSON.stringify(copy, null, 2));
      setNote(t('privacyExported'));
    });
  const remove = (id: string) =>
    act(async () => {
      if (!(await confirmDelete(t('privacyDeleteConfirm')))) return;
      await call('/privacy/delete', post({ categories: [id] }));
      setNote(t('privacyDeleted'));
    });

  return (
    <Screen>
      <Kicker>{t('privacyKicker')}</Kicker>
      <H1>{t('privacyTitle')}</H1>
      <Muted>{t('privacyIntro')}</Muted>
      <ErrorBox error={error ?? err} />
      {note && <Banner tone="ok">{note}</Banner>}

      {data && (
        <>
          <Panel>
            <Row style={{ flexWrap: 'nowrap', gap: 12 }}>
              <Ionicons name="sparkles" size={24} color={Space.neon} />
              <SpaceText style={local.title}>{t('privacyAi')}</SpaceText>
              <Switch
                value={data.switches.ai}
                onValueChange={setAi}
                disabled={busy}
                trackColor={{ true: Brand.primary, false: '#5A6378' }}
                accessibilityLabel={t('privacyAi')}
              />
            </Row>
            <SpaceText muted small>
              {!data.switches.ai_available ? t('privacyAiMissing') : data.switches.ai ? t('privacyAiOn') : t('privacyAiOff')}
            </SpaceText>
          </Panel>

          <H2 icon="folder-open">{t('privacyHeld')}</H2>
          {data.held.map((h) => (
            <Card key={h.id}>
              <Row style={{ flexWrap: 'nowrap', gap: 10 }}>
                <View style={{ flex: 1, gap: 2 }}>
                  <ThemedText type="smallBold">{t(`held_${h.id}` as StringKey)}</ThemedText>
                  {lang === 'en' && <Muted>{h.why}</Muted>}
                </View>
                <Badge tone="neutral">{num(h.count, lang)}</Badge>
              </Row>
              {h.deletable ? (
                h.count > 0 && <Button title={t('privacyDelete')} icon="trash" variant="secondary" onPress={() => remove(h.id)} disabled={busy} />
              ) : (
                <Muted>🔒 {t('privacyCannotDelete')}</Muted>
              )}
            </Card>
          ))}
          <Muted>{t('privacyKept')}</Muted>

          <H2 icon="globe">{t('privacyGoes')}</H2>
          {data.recipients.map((r) => (
            <Card key={r.id}>
              <Row style={{ flexWrap: 'nowrap', gap: 10 }}>
                <Ionicons name={ICON[r.id as keyof typeof ICON] ?? 'globe'} size={20} color={Brand.primary} />
                <View style={{ flex: 1, gap: 2 }}>
                  <ThemedText type="smallBold">{r.name}</ThemedText>
                  <Muted>{t(`rec_${r.id}` as StringKey)}</Muted>
                </View>
                <Badge tone="info">{r.law}</Badge>
              </Row>
              {r.id === 'banks' && (
                <Pressable onPress={() => router.push('/banks')} accessibilityRole="link">
                  <ThemedText type="link">{t('settingsBanks')} →</ThemedText>
                </Pressable>
              )}
            </Card>
          ))}

          <H2 icon="eye-off">{t('privacyNotStored')}</H2>
          <Card>
            {(['ns_1', 'ns_2', 'ns_3', 'ns_4', 'ns_5'] as const).map((k) => (
              <Muted key={k}>✕ {t(k)}</Muted>
            ))}
          </Card>

          <Button title={t('privacyExport')} icon="download" onPress={exportData} loading={busy} />
          <Banner tone="info">{t('privacyRights')}</Banner>
        </>
      )}
    </Screen>
  );
}

const local = StyleSheet.create({
  title: { flex: 1, fontSize: 16, lineHeight: 22, fontWeight: '600' },
});
