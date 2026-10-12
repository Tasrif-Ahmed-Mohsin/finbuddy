import type { ReactNode } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
  type TextInputProps,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Brand, MaxContentWidth, Spacing, Tone, type ToneName } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

export function Screen({ children, refreshing, onRefresh }: { children: ReactNode; refreshing?: boolean; onRefresh?: () => void }) {
  return (
    <ThemedView style={styles.flex}>
      <SafeAreaView style={styles.flex} edges={['top']}>
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
          refreshControl={onRefresh ? <RefreshControl refreshing={!!refreshing} onRefresh={onRefresh} /> : undefined}>
          {children}
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

export function Card({ children, style, tone }: { children: ReactNode; style?: ViewStyle; tone?: ToneName }) {
  return (
    <ThemedView type="backgroundElement" style={[styles.card, tone && { borderLeftWidth: 4, borderLeftColor: Tone[tone].fg }, style]}>
      {children}
    </ThemedView>
  );
}

export function Row({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  return <View style={[styles.row, style]}>{children}</View>;
}

export function H1({ children }: { children: ReactNode }) {
  return <ThemedText style={styles.h1}>{children}</ThemedText>;
}

export function H2({ children }: { children: ReactNode }) {
  return <ThemedText style={styles.h2}>{children}</ThemedText>;
}

export function Muted({ children, style }: { children: ReactNode; style?: object }) {
  return (
    <ThemedText type="small" themeColor="textSecondary" style={style}>
      {children}
    </ThemedText>
  );
}

export function Badge({ tone, children }: { tone: ToneName; children: ReactNode }) {
  return (
    <View style={[styles.badge, { backgroundColor: Tone[tone].bg }]}>
      <ThemedText style={[styles.badgeText, { color: Tone[tone].fg }]}>{children}</ThemedText>
    </View>
  );
}

export function Button({
  title,
  onPress,
  variant = 'primary',
  disabled,
  loading,
}: {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  loading?: boolean;
}) {
  const theme = useTheme();
  const bg = variant === 'primary' ? Brand.primary : variant === 'danger' ? Tone.block.fg : theme.backgroundSelected;
  const fg = variant === 'secondary' ? theme.text : Brand.primaryText;
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [styles.button, { backgroundColor: bg, opacity: disabled ? 0.45 : pressed ? 0.8 : 1 }]}>
      {loading ? <ActivityIndicator color={fg} /> : <ThemedText style={[styles.buttonText, { color: fg }]}>{title}</ThemedText>}
    </Pressable>
  );
}

export function Segmented<T extends string>({ value, options, onChange }: { value: T; options: { value: T; label: string }[]; onChange: (v: T) => void }) {
  return (
    <ThemedView type="backgroundSelected" style={styles.segmented}>
      {options.map((o) => {
        const active = o.value === value;
        return (
          <Pressable key={o.value} onPress={() => onChange(o.value)} style={[styles.segment, active && { backgroundColor: Brand.primary }]}>
            <ThemedText type="smallBold" style={active ? { color: Brand.primaryText } : undefined}>
              {o.label}
            </ThemedText>
          </Pressable>
        );
      })}
    </ThemedView>
  );
}

export function Field({ label, style, ...props }: TextInputProps & { label: string }) {
  const theme = useTheme();
  return (
    <View style={styles.field}>
      {label ? <Muted>{label}</Muted> : null}
      <TextInput
        placeholderTextColor={theme.textSecondary}
        {...props}
        style={[styles.input, { color: theme.text, backgroundColor: theme.background, borderColor: theme.backgroundSelected }, style]}
      />
    </View>
  );
}

/** Horizontal usage bar for limits (5 lakh BDT / 30 transactions). Turns amber at 80%, red at 100%. */
export function Meter({ label, used, cap, display }: { label: string; used: number; cap: number; display: string }) {
  const theme = useTheme();
  const ratio = cap > 0 ? Math.min(used / cap, 1) : 0;
  const tone = ratio >= 1 ? Tone.block : ratio >= 0.8 ? Tone.warn : Tone.ok;
  return (
    <View style={styles.meter}>
      <Row style={styles.between}>
        <ThemedText type="small">{label}</ThemedText>
        <ThemedText type="smallBold">{display}</ThemedText>
      </Row>
      <View style={[styles.track, { backgroundColor: theme.backgroundSelected }]}>
        <View style={[styles.fill, { width: `${ratio * 100}%`, backgroundColor: tone.fg }]} />
      </View>
    </View>
  );
}

export function Banner({ tone, children }: { tone: ToneName; children: ReactNode }) {
  return (
    <View style={[styles.banner, { backgroundColor: Tone[tone].bg }]}>
      <ThemedText type="small" style={{ color: Tone[tone].fg }}>
        {children}
      </ThemedText>
    </View>
  );
}

export function ErrorBox({ error }: { error: string | null }) {
  if (!error) return null;
  return <Banner tone="block">{error}</Banner>;
}

export const styles = StyleSheet.create({
  flex: { flex: 1 },
  scroll: { padding: Spacing.three, gap: Spacing.three, paddingBottom: Spacing.six, width: '100%', maxWidth: MaxContentWidth, alignSelf: 'center' },
  card: { borderRadius: 16, padding: Spacing.three, gap: Spacing.two },
  row: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two, flexWrap: 'wrap' },
  between: { justifyContent: 'space-between' },
  h1: { fontSize: 28, lineHeight: 34, fontWeight: '700' },
  h2: { fontSize: 18, lineHeight: 24, fontWeight: '700' },
  badge: { borderRadius: 999, paddingHorizontal: 10, paddingVertical: 2, alignSelf: 'flex-start' },
  badgeText: { fontSize: 12, lineHeight: 18, fontWeight: '700' },
  button: { borderRadius: 12, paddingVertical: 12, paddingHorizontal: 16, alignItems: 'center', justifyContent: 'center', minHeight: 48 },
  buttonText: { fontSize: 16, fontWeight: '700' },
  segmented: { flexDirection: 'row', borderRadius: 12, padding: 4, gap: 4 },
  segment: { flex: 1, borderRadius: 9, paddingVertical: 8, alignItems: 'center' },
  field: { gap: 4 },
  input: { borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, fontSize: 16, minHeight: 46 },
  meter: { gap: 6 },
  track: { height: 8, borderRadius: 4, overflow: 'hidden' },
  fill: { height: 8, borderRadius: 4 },
  banner: { borderRadius: 12, paddingHorizontal: 12, paddingVertical: 10 },
});
