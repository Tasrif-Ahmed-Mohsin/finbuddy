import Ionicons from '@expo/vector-icons/Ionicons';
import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';

import { Mascot } from '@/components/mascot';
import { BigNumber, GlowPulse, Kicker, Panel, SectionHeader, SpaceText } from '@/components/neo';
import { ThemedText } from '@/components/themed-text';
import { Button, Card, ErrorBox, H1, Muted, Row } from '@/components/ui';
import { Space, Tone } from '@/constants/theme';
import { post, type JudgeRun, type JudgeTask } from '@/lib/api';
import { fill, num } from '@/lib/format';
import type { StringKey } from '@/lib/i18n';
import { useSession } from '@/lib/session';

const CRITERIA: { key: JudgeTask['criterion']; label: StringKey; icon: 'checkmark-done' | 'shield-checkmark' | 'chatbubbles' }[] = [
  { key: 'task', label: 'critTask', icon: 'checkmark-done' },
  { key: 'security', label: 'critSecurity', icon: 'shield-checkmark' },
  { key: 'interaction', label: 'critInteraction', icon: 'chatbubbles' },
];

/**
 * Judge mode: every scripted task of the brief, run end to end through the real API, each in a fresh sandbox,
 * with the steps, the checks, the value and the hash-chained log entry that proves it.
 */
export default function JudgeScreen() {
  const { t, lang, call } = useSession();
  const [run, setRun] = useState<JudgeRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setBusy(true);
    setError(null);
    setRun(null);
    try {
      setRun(await call<JudgeRun>('/judge/run', post({})));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const allGood = run && run.passed === run.total;
  return (
    <View style={{ flex: 1 }}>
      <Animated.ScrollView contentContainerStyle={local.scroll}>
        <Kicker>{t('judgeKicker')}</Kicker>
        <H1>{t('judgeTitle')}</H1>
        <Muted>{t('judgeIntro')}</Muted>

        <Panel>
          <Row style={{ flexWrap: 'nowrap', gap: 14 }}>
            <Mascot size={96} mood={busy ? 'thinking' : run ? (allGood ? 'celebrate' : 'worried') : 'idle'} />
            <View style={{ flex: 1, gap: 4 }}>
              {run ? (
                <>
                  <Row style={{ alignItems: 'baseline', gap: 6, flexWrap: 'nowrap' }}>
                    <BigNumber value={run.passed} size={56} color={allGood ? Tone.ok.neon : Tone.block.neon} format={(n) => num(Math.round(n), lang)} />
                    <SpaceText muted>/ {num(run.total, lang)}</SpaceText>
                  </Row>
                  <SpaceText neon small>
                    {fill(t('judgePassedFmt'), { p: num(run.passed, lang), t: num(run.total, lang) })}
                  </SpaceText>
                </>
              ) : (
                <SpaceText>{busy ? t('judgeRunning') : t('judgeIntro')}</SpaceText>
              )}
            </View>
          </Row>
          {run && (
            <Row style={{ gap: 8 }}>
              {CRITERIA.map((c) => (
                <View key={c.key} style={local.crit}>
                  <Ionicons name={c.icon} size={14} color={Space.neon} />
                  <SpaceText small>
                    {t(c.label)} {num(run.summary[c.key].passed, lang)}/{num(run.summary[c.key].total, lang)}
                  </SpaceText>
                </View>
              ))}
            </Row>
          )}
        </Panel>

        <GlowPulse>
          <Button title={t('judgeRun')} icon="play" onPress={start} loading={busy} />
        </GlowPulse>
        <ErrorBox error={error} />

        {run &&
          CRITERIA.map((c) => (
            <View key={c.key} style={{ gap: 12 }}>
              <SectionHeader kicker={`${num(run.summary[c.key].passed, lang)}/${num(run.summary[c.key].total, lang)}`} title={t(c.label)} />
              {run.tasks
                .filter((x) => x.criterion === c.key)
                .map((task, i) => (
                  <Animated.View key={task.id} entering={FadeInDown.delay(i * 70).duration(260)}>
                    <TaskCard task={task} />
                  </Animated.View>
                ))}
            </View>
          ))}
      </Animated.ScrollView>
    </View>
  );
}

function TaskCard({ task }: { task: JudgeTask }) {
  const { t } = useSession();
  const [open, setOpen] = useState(false);
  return (
    <Pressable accessibilityRole="button" accessibilityState={{ expanded: open }} onPress={() => setOpen(!open)}>
      <Card tone={task.passed ? 'ok' : 'block'}>
        <Row style={{ flexWrap: 'nowrap', gap: 10 }}>
          <Ionicons name={task.passed ? 'checkmark-circle' : 'close-circle'} size={22} color={task.passed ? Tone.ok.fg : Tone.block.fg} />
          <View style={{ flex: 1 }}>
            <ThemedText type="smallBold">
              {task.id} · {task.title}
            </ThemedText>
            <Muted>{task.goal}</Muted>
          </View>
          <Ionicons name={open ? 'chevron-up' : 'chevron-down'} size={18} color="#8A909C" />
        </Row>
        {task.value ? (
          <ThemedText type="small">
            <ThemedText type="smallBold">{t('judgeValue')}: </ThemedText>
            {task.value}
          </ThemedText>
        ) : null}
        {open && (
          <View style={{ gap: 10 }}>
            {task.steps.map((s, i) => (
              <View key={i} style={local.step}>
                <View style={local.who}>
                  <ThemedText style={local.whoText}>{s.who}</ThemedText>
                </View>
                <View style={{ flex: 1, gap: 2 }}>
                  <ThemedText type="small">{s.did}</ThemedText>
                  <Muted>→ {s.got}</Muted>
                </View>
              </View>
            ))}
            <View style={{ gap: 4 }}>
              {task.checks.map((c) => (
                <Row key={c.what} style={{ flexWrap: 'nowrap', alignItems: 'flex-start' }}>
                  <Ionicons name={c.ok ? 'checkmark' : 'close'} size={16} color={c.ok ? Tone.ok.fg : Tone.block.fg} style={{ marginTop: 2 }} />
                  <ThemedText type="small" style={{ flex: 1 }}>
                    {c.what}
                  </ThemedText>
                </Row>
              ))}
              {task.error ? <ThemedText style={{ color: Tone.block.fg }}>{task.error}</ThemedText> : null}
            </View>
            {task.evidence?.seq ? (
              <View style={local.evidence}>
                <Ionicons name="link" size={14} color={Space.neon} />
                <ThemedText type="code" style={{ color: Space.text, flex: 1 }}>
                  {t('judgeEvidence')}: #{task.evidence.seq} {task.evidence.event} · {task.evidence.hash}… · {task.ms} ms
                </ThemedText>
              </View>
            ) : null}
          </View>
        )}
      </Card>
    </Pressable>
  );
}

const local = StyleSheet.create({
  scroll: { padding: 20, gap: 18, paddingBottom: 60, width: '100%', maxWidth: 760, alignSelf: 'center' },
  crit: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999, borderWidth: 1, borderColor: Space.rim },
  step: { flexDirection: 'row', gap: 10, alignItems: 'flex-start' },
  who: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8, backgroundColor: Space.bg, minWidth: 64, alignItems: 'center' },
  whoText: { fontSize: 11, lineHeight: 15, color: Space.neon, fontWeight: '600' },
  evidence: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 10, borderRadius: 12, backgroundColor: Space.bg },
});
