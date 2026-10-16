import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { useCallback } from 'react';
import { Pressable } from 'react-native';

import { DataBanner } from '@/components/data-banner';
import { NeedCard, NoteCard } from '@/components/note-card';
import { RunwayCard } from '@/components/runway-card';
import { ShieldMini } from '@/components/save';
import { InsightCard } from '@/components/sathi-updates';
import { ThemedText } from '@/components/themed-text';
import { Card, ErrorBox, H1, H2, Muted, Row, Screen, Segmented, styles } from '@/components/ui';
import { Tone } from '@/constants/theme';
import type { Feed, Insight, Role, Timeline } from '@/lib/api';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';
import { useTheme } from '@/hooks/use-theme';

/** Today: the loop at a glance. Sense (money in China, alerts) → what Sathi did (act) → what needs you. */
export default function TodayScreen() {
  const { t, lang, role, setRole, call } = useSession();
  const theme = useTheme();
  const { data, error, loading, reload } = useLoad(
    useCallback(async () => {
      const [feed, ins, timeline] = await Promise.all([
        call<Feed>(`/feed?lang=${lang}`),
        call<{ insights: Insight[] }>(`/insights?lang=${lang}`),
        call<Timeline>('/timeline'),
      ]);
      return { feed, insights: ins.insights, timeline };
    }, [call, lang]),
  );

  const needs = data?.feed.needs_you ?? [];
  const notes = data?.feed.notes ?? [];
  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <Row style={styles.between}>
        <H1>{t('appName')}</H1>
        <Row style={{ gap: 14 }}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={t('emergencyLink')}
            onPress={() => router.push('/emergency')}
            hitSlop={8}
            style={{ paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16, backgroundColor: Tone.block.bg }}>
            <ThemedText type="smallBold" style={{ color: Tone.block.fg }}>
              🆘 {t('emergencyLink')}
            </ThemedText>
          </Pressable>
          <Pressable accessibilityRole="button" accessibilityLabel={t('settingsLink')} onPress={() => router.push('/settings')} hitSlop={12}>
            <Ionicons name="settings-outline" size={24} color={theme.text} />
          </Pressable>
        </Row>
      </Row>
      <Muted>{t('loopTagline')}</Muted>
      <Card>
        <Muted>{t('youAre')}</Muted>
        <Segmented<Role>
          value={role}
          onChange={setRole}
          options={[
            { value: 'parent', label: t('parent') },
            { value: 'student', label: t('student') },
          ]}
        />
      </Card>
      <ErrorBox error={error} />

      {data && (
        <>
          <RunwayCard runway={data.feed.runway} />
          {data.feed.shield && <ShieldMini shield={data.feed.shield} />}
          {needs.length > 0 && (
            <>
              <H2>{t('needsYou')}</H2>
              {needs.map((n) => (
                <NeedCard
                  key={n.type === 'sign_mandate' ? n.proposal_id : n.type === 'confirm_safe' ? n.check_id : n.type === 'approve_release' ? n.release_id : n.draft_id}
                  need={n}
                />
              ))}
            </>
          )}
          <H2>{t('whatSathiDid')}</H2>
          {notes.length === 0 && <Muted>{t('nothingYet')}</Muted>}
          {notes.slice(0, 8).map((n) => (
            <NoteCard key={n.id} note={n} />
          ))}
          {data.insights.length > 0 && (
            <>
              <H2>{t('alertsFromMessages')}</H2>
              {data.insights.slice(0, 3).map((i) => (
                <InsightCard key={i.id} insight={i} onChanged={reload} />
              ))}
            </>
          )}
          <DataBanner dq={data.timeline.data_quality} />
        </>
      )}
    </Screen>
  );
}
