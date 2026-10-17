import { useState, type ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';

import { Mascot, type MascotAction, type MascotMood } from '@/components/mascot';
import { ThemedText } from '@/components/themed-text';
import { Elevation, Radius } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/**
 * Sathi talking: the mascot with a speech bubble beside it. Tapping the mascot makes it wave.
 * The bubble fades in again whenever the message changes, so a new message is noticed.
 */
export function BuddyBubble({
  mood = 'idle',
  text,
  title,
  size = 92,
  action,
  look,
  children,
  onPressMascot,
}: {
  mood?: MascotMood;
  text: string;
  title?: string;
  size?: number;
  action?: MascotAction;
  look?: 'down' | 'left' | 'right';
  children?: ReactNode;
  onPressMascot?: () => void;
}) {
  const theme = useTheme();
  const [wave, setWave] = useState<MascotAction | undefined>(undefined);
  const gesture = wave && (!action || wave.key > action.key) ? wave : action;
  return (
    <View style={styles.row}>
      <Mascot
        size={size}
        mood={mood}
        action={gesture}
        look={look}
        onPress={() => {
          setWave({ type: 'wave', key: Date.now() });
          onPressMascot?.();
        }}
        accessibilityLabel={`Sathi: ${text}`}
      />
      <Animated.View key={text} entering={FadeInDown.duration(260)} style={[styles.bubble, { backgroundColor: theme.backgroundElement }]}>
        <View style={[styles.tail, { backgroundColor: theme.backgroundElement }]} />
        {title ? (
          <ThemedText type="smallBold" style={{ color: theme.text }}>
            {title}
          </ThemedText>
        ) : null}
        <ThemedText type="small" style={{ color: theme.text }}>
          {text}
        </ThemedText>
        {children}
      </Animated.View>
    </View>
  );
}

/** A friendly loading state: Sathi thinking, with a short line under it. */
export function BuddyLoading({ text }: { text: string }) {
  return (
    <Animated.View entering={FadeIn.duration(200)} style={styles.loading}>
      <Mascot size={96} mood="thinking" />
      <ThemedText type="small" themeColor="textSecondary">
        {text}
      </ThemedText>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  bubble: { flex: 1, borderRadius: Radius.lg, padding: 14, gap: 6, boxShadow: Elevation[2] },
  tail: { position: 'absolute', left: -6, top: '50%', marginTop: -7, width: 14, height: 14, borderRadius: 3, transform: [{ rotate: '45deg' }] },
  loading: { alignItems: 'center', gap: 8, paddingVertical: 24 },
});
