import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Mascot, type MascotAction, type MascotMood } from '@/components/mascot';
import { ThemedText } from '@/components/themed-text';
import { Card, Chip, Muted, Row, Screen } from '@/components/ui';
import { useSession } from '@/lib/session';

const MOODS: MascotMood[] = ['idle', 'happy', 'thinking', 'talking', 'curious', 'worried', 'alert', 'protect', 'celebrate', 'sleep'];
const ACTIONS: MascotAction['type'][] = ['wave', 'jump', 'nod', 'shake'];

/** Meet Sathi: every mood and gesture of the buddy, and what each one means in the app. */
export default function BuddyScreen() {
  const { t } = useSession();
  const [mood, setMood] = useState<MascotMood>('happy');
  const [action, setAction] = useState<MascotAction | undefined>(undefined);
  return (
    <Screen>
      <Card style={styles.stage}>
        <Mascot size={180} mood={mood} action={action} onPress={() => setAction({ type: 'wave', key: Date.now() })} />
        <ThemedText display style={styles.name}>
          {t(`buddyMood_${mood}`)}
        </ThemedText>
        <Muted style={styles.center}>{t(`buddyMeaning_${mood}`)}</Muted>
      </Card>
      <Muted>{t('buddyMoods')}</Muted>
      <Row>
        {MOODS.map((m) => (
          <Chip key={m} label={t(`buddyMood_${m}`)} selected={m === mood} onPress={() => setMood(m)} />
        ))}
      </Row>
      <Muted>{t('buddyGestures')}</Muted>
      <Row>
        {ACTIONS.map((a) => (
          <Chip key={a} label={t(`buddyAction_${a}`)} icon="hand-left-outline" onPress={() => setAction({ type: a, key: Date.now() })} />
        ))}
      </Row>
      <View style={styles.note}>
        <Muted>{t('buddyNote')}</Muted>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  stage: { alignItems: 'center', paddingVertical: 24 },
  name: { fontSize: 22, lineHeight: 28, fontWeight: '700' },
  center: { textAlign: 'center' },
  note: { paddingHorizontal: 4 },
});
