import Ionicons from '@expo/vector-icons/Ionicons';
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Platform, ScrollView, StyleSheet, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';

import { Mascot } from '@/components/mascot';
import { Kicker, Panel, SpaceText } from '@/components/neo';
import { ThemedText } from '@/components/themed-text';
import { Button, Card, ErrorBox, Muted, Row, Segmented } from '@/components/ui';
import { Brand, Space } from '@/constants/theme';
import type { Role } from '@/lib/api';
import type { Lang } from '@/lib/i18n';
import { setupPasskey } from '@/lib/passkey';
import { useSession } from '@/lib/session';

// Fade in on the phone; on the web the content shows at once (a hidden tab never runs the animation).
const enter = (ms: number) => (Platform.OS === 'web' ? undefined : FadeInDown.duration(ms));
const PAGES = ['meet', 'who', 'data', 'key'] as const;
type Page = (typeof PAGES)[number];

/**
 * First launch, four short cards: meet Bluefin (the loop in one line), who you are (parent or student) and your
 * language, your data and the AI (PIPL consent: an explicit choice, nothing pre-selected, and Skip still asks; "no" =
 * the rules answer and nothing goes to DeepSeek in China), and your fingerprint key (the passkey that signs every
 * approval). Then the story, or straight to the app. `?step=data` opens the AI question alone.
 */
export default function WelcomeScreen() {
  const { t, role, setRole, lang, setLang, call, setOnboarded, setAiChoice } = useSession();
  const { step } = useLocalSearchParams<{ step?: string }>();
  const [page, setPage] = useState<Page>(step === 'data' ? 'data' : 'meet');
  const [ai, setAi] = useState<boolean | null>(null);
  const [keyLabel, setKeyLabel] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const i = PAGES.indexOf(page);

  async function next() {
    setError(null);
    if (page === 'data') {
      if (ai === null) return;
      try {
        // In this demo one phone is both people, so the answer is recorded for both; each can change it later.
        await setAiChoice(['parent', 'student'], ai);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        return;
      }
    }
    if (i < PAGES.length - 1) setPage(PAGES[i + 1]);
  }

  async function makeKey() {
    setBusy(true);
    setError(null);
    try {
      const label = await setupPasskey(role, t('welcome_key_title'), call);
      if (label) setKeyLabel(label);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  function finish(to: '/story' | '/') {
    setOnboarded(true);
    router.replace(to);
  }

  return (
    <ScrollView contentContainerStyle={local.scroll}>
      <Row style={{ gap: 6, flexWrap: 'nowrap' }}>
        {PAGES.map((p, k) => (
          <View key={p} style={[local.dot, { backgroundColor: k <= i ? Brand.primary : '#D5D9E2', flex: k === i ? 3 : 1 }]} />
        ))}
      </Row>

      <Animated.View key={page} entering={enter(260)} style={{ gap: 14 }}>
        {page === 'meet' && (
          <Panel>
            <View style={{ alignItems: 'center', gap: 10 }}>
              <Mascot size={150} mood="happy" />
              <Kicker dark>{t('welcome_meet_kicker')}</Kicker>
              <SpaceText style={local.big}>{t('welcome_meet_title')}</SpaceText>
              <SpaceText muted style={{ textAlign: 'center' }}>
                {t('welcome_meet_body')}
              </SpaceText>
            </View>
            <Row style={{ gap: 6, justifyContent: 'center' }}>
              {(['sense', 'plan', 'act', 'prove'] as const).map((s) => (
                <View key={s} style={local.stage}>
                  <SpaceText neon small style={{ fontWeight: '700', letterSpacing: 1 }}>
                    {t(`stage_${s}`)}
                  </SpaceText>
                </View>
              ))}
            </Row>
          </Panel>
        )}

        {page === 'who' && (
          <Card>
            <ThemedText display style={local.title}>
              {t('welcome_who_title')}
            </ThemedText>
            <Muted>{t('welcome_who_body')}</Muted>
            <Segmented<Role>
              value={role}
              onChange={setRole}
              options={[
                { value: 'parent', label: t('parent') },
                { value: 'student', label: t('student') },
              ]}
            />
            <Segmented<Lang>
              value={lang}
              onChange={setLang}
              options={[
                { value: 'bn', label: 'বাংলা' },
                { value: 'en', label: 'English' },
                { value: 'zh', label: '中文' },
              ]}
            />
          </Card>
        )}

        {page === 'data' && (
          <Card>
            <Row style={{ flexWrap: 'nowrap', gap: 10 }}>
              <Ionicons name="lock-closed" size={24} color={Brand.primary} />
              <ThemedText display style={[local.title, { flex: 1 }]}>
                {t('welcome_data_title')}
              </ThemedText>
            </Row>
            <Muted>{t('welcome_data_body')}</Muted>
            <Row style={{ gap: 10 }}>
              <Button title={t('welcome_ai_yes')} icon="sparkles" variant={ai === true ? 'primary' : 'secondary'} onPress={() => setAi(true)} />
              <Button title={t('welcome_ai_no')} icon="list" variant={ai === false ? 'primary' : 'secondary'} onPress={() => setAi(false)} />
            </Row>
            <Muted>{ai === null ? t('welcome_ai_pick') : ai ? t('privacyAiOn') : t('privacyAiOff')}</Muted>
            <Muted>{t('welcome_ai_both')}</Muted>
          </Card>
        )}

        {page === 'key' && (
          <Card>
            <Row style={{ flexWrap: 'nowrap', gap: 10 }}>
              <Ionicons name="finger-print" size={26} color={Brand.primary} />
              <ThemedText display style={[local.title, { flex: 1 }]}>
                {t('welcome_key_title')}
              </ThemedText>
            </Row>
            <Muted>{t('welcome_key_body')}</Muted>
            {keyLabel ? (
              <Row style={{ gap: 8 }}>
                <Ionicons name="checkmark-circle" size={20} color="#1E8449" />
                <ThemedText type="smallBold">{keyLabel}</ThemedText>
              </Row>
            ) : (
              <Button title={t('welcome_key_do')} icon="finger-print" onPress={makeKey} loading={busy} />
            )}
          </Card>
        )}
      </Animated.View>

      <ErrorBox error={error} />
      {page !== 'key' ? (
        <Row style={{ gap: 10 }}>
          {i > 0 && <Button title={t('story_back')} variant="secondary" icon="arrow-back" onPress={() => setPage(PAGES[i - 1])} />}
          <Button title={t('story_next')} icon="arrow-forward" onPress={next} disabled={page === 'data' && ai === null} />
        </Row>
      ) : (
        <>
          <Button title={t('storyOpen')} icon="play" onPress={() => finish('/story')} />
          <Button title={t('welcome_skip_story')} variant="secondary" onPress={() => finish('/')} />
        </>
      )}
      {/* Skipping the introduction still asks the one question that needs an answer: the AI. */}
      {page === 'meet' && <Button title={t('welcome_skip')} variant="secondary" onPress={() => setPage('data')} />}
    </ScrollView>
  );
}

const local = StyleSheet.create({
  scroll: { padding: 16, paddingTop: 56, gap: 14, paddingBottom: 48, maxWidth: 640, width: '100%', alignSelf: 'center' },
  dot: { height: 6, borderRadius: 3 },
  big: { fontSize: 24, lineHeight: 30, fontWeight: '700', textAlign: 'center' },
  title: { fontSize: 20, lineHeight: 26, fontWeight: '700' },
  stage: { borderWidth: 1, borderColor: 'rgba(77, 163, 255, 0.5)', borderRadius: 999, paddingHorizontal: 10, paddingVertical: 3, backgroundColor: Space.bg2 },
});
