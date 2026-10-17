import Ionicons from '@expo/vector-icons/Ionicons';
import { useState, type ComponentProps, type ReactNode } from 'react';
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
import { Brand, DockSpace, Elevation, MaxContentWidth, MaxWideWidth, Radius, Space, Spacing, Tone, type ToneName } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { fontFamilyFor, useFontState } from '@/lib/fonts';
import { useSession } from '@/lib/session';

type IconName = ComponentProps<typeof Ionicons>['name'];

/** A scrolling screen on the neumorphic shell, with room for the floating dock. `wide` lets dashboards use a desktop's width. */
export function Screen({ children, refreshing, onRefresh, wide }: { children: ReactNode; refreshing?: boolean; onRefresh?: () => void; wide?: boolean }) {
  const theme = useTheme();
  return (
    <View style={[styles.flex, { backgroundColor: theme.background }]}>
      <SafeAreaView style={styles.flex} edges={['top']}>
        <ScrollView
          contentContainerStyle={[styles.scroll, { maxWidth: wide ? MaxWideWidth : MaxContentWidth }]}
          keyboardShouldPersistTaps="handled"
          refreshControl={onRefresh ? <RefreshControl refreshing={!!refreshing} onRefresh={onRefresh} tintColor={Brand.primary} colors={[Brand.primary]} /> : undefined}>
          {children}
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

/** A raised neumorphic surface. `tone` adds a status light in the corner and a quiet coloured rim. */
export function Card({ children, style, tone }: { children: ReactNode; style?: ViewStyle; tone?: ToneName }) {
  const theme = useTheme();
  return (
    <View style={[styles.card, { backgroundColor: theme.backgroundElement }, tone && { borderColor: Tone[tone].line, borderWidth: 1.5 }, style]}>
      {tone ? <View style={[styles.led, { backgroundColor: Tone[tone].neon, boxShadow: `0px 0px 8px ${Tone[tone].neon}` }]} /> : null}
      {children}
    </View>
  );
}

export function Row({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  return <View style={[styles.row, style]}>{children}</View>;
}

export function H1({ children }: { children: ReactNode }) {
  return (
    <ThemedText display style={styles.h1}>
      {children}
    </ThemedText>
  );
}

export function H2({ children, icon }: { children: ReactNode; icon?: IconName }) {
  const text = (
    <ThemedText display style={[styles.h2, icon && styles.flexShrink]}>
      {children}
    </ThemedText>
  );
  if (!icon) return text;
  return (
    <View style={styles.titleRow}>
      <View style={styles.h2Icon}>
        <Ionicons name={icon} size={15} color={Space.neon} />
      </View>
      {text}
    </View>
  );
}

/** A bold line with an icon in front (card titles). */
export function Label({ icon, color, children }: { icon: IconName; color?: string; children: ReactNode }) {
  return (
    <View style={[styles.titleRow, styles.flexShrink]}>
      <Ionicons name={icon} size={17} color={color ?? Brand.primary} />
      <ThemedText type="smallBold" style={styles.flexShrink}>
        {children}
      </ThemedText>
    </View>
  );
}

export function Muted({ children, style }: { children: ReactNode; style?: object }) {
  return (
    <ThemedText type="small" themeColor="textSecondary" style={style}>
      {children}
    </ThemedText>
  );
}

export function Badge({ tone, children, icon }: { tone: ToneName; children: ReactNode; icon?: IconName }) {
  return (
    <View style={[styles.badge, { backgroundColor: Tone[tone].bg }, icon && styles.badgeRow]}>
      {icon ? <Ionicons name={icon} size={13} color={Tone[tone].fg} /> : null}
      <ThemedText style={[styles.badgeText, { color: Tone[tone].fg }]}>{children}</ThemedText>
    </View>
  );
}

/** Primary: a glowing neon pill (one per screen). Secondary: a raised neumorphic pill that presses in. */
export function Button({
  title,
  onPress,
  variant = 'primary',
  disabled,
  loading,
  icon,
}: {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  loading?: boolean;
  icon?: IconName;
}) {
  const theme = useTheme();
  const off = disabled || loading;
  const filled = variant !== 'secondary';
  const bg = off && !loading ? theme.backgroundSelected : variant === 'primary' ? Brand.primary : variant === 'danger' ? Tone.block.fg : theme.backgroundElement;
  const fg = off && !loading ? theme.textTertiary : filled ? Brand.primaryText : theme.text;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!off, busy: !!loading }}
      onPress={onPress}
      disabled={off}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: pressed && variant === 'primary' ? Brand.primaryPressed : bg },
        off && !loading
          ? { boxShadow: Elevation.inset }
          : pressed
            ? { boxShadow: filled ? Elevation.pressed : Elevation.pressed, transform: [{ scale: 0.985 }] }
            : { boxShadow: variant === 'primary' ? Elevation.glow : variant === 'danger' ? '0px 8px 20px rgba(196, 43, 28, 0.3)' : Elevation[1] },
      ]}>
      {loading ? (
        <ActivityIndicator color={fg} />
      ) : (
        <View style={styles.buttonInner}>
          {icon ? <Ionicons name={icon} size={18} color={variant === 'secondary' ? Brand.primary : fg} /> : null}
          <ThemedText style={[styles.buttonText, { color: fg }]}>{title}</ThemedText>
        </View>
      )}
    </Pressable>
  );
}

/** Pill tabs in a pressed-in track; the chosen one is a dark deep-space pill with neon text. */
export function Segmented<T extends string>({ value, options, onChange }: { value: T; options: { value: T; label: string }[]; onChange: (v: T) => void }) {
  const theme = useTheme();
  return (
    <View style={[styles.segmented, { backgroundColor: theme.backgroundSelected }]} accessibilityRole="tablist">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <Pressable
            key={o.value}
            accessibilityRole="tab"
            accessibilityState={{ selected: active }}
            onPress={() => onChange(o.value)}
            style={[styles.segment, active && styles.segmentActive]}>
            <ThemedText type="smallBold" style={{ color: active ? Space.neon : theme.textSecondary }}>
              {o.label}
            </ThemedText>
          </Pressable>
        );
      })}
    </View>
  );
}

/** A small raised pill for quick choices and filters; the chosen one goes deep-space with neon text. */
export function Chip({ label, onPress, icon, selected }: { label: string; onPress?: () => void; icon?: IconName; selected?: boolean }) {
  const theme = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ selected: !!selected }}
      onPress={onPress}
      disabled={!onPress}
      style={({ pressed }) => [
        styles.chip,
        selected ? styles.chipSelected : { backgroundColor: theme.backgroundElement, boxShadow: Elevation[1] },
        pressed && { boxShadow: Elevation.pressed },
      ]}>
      {icon ? <Ionicons name={icon} size={15} color={selected ? Space.neon : Brand.primary} /> : null}
      <ThemedText type="small" style={{ color: selected ? Space.text : theme.text, fontWeight: '500' }}>
        {label}
      </ThemedText>
    </Pressable>
  );
}

/** A pressed-in input well; it lights up with a neon ring while you type. */
export function Field({ label, style, ...props }: TextInputProps & { label: string }) {
  const theme = useTheme();
  const { lang } = useSession();
  const { bangla } = useFontState();
  const fontFamily = fontFamilyFor(400, false, lang, bangla);
  const [focused, setFocused] = useState(false);
  return (
    <View style={styles.field}>
      {label ? <Muted>{label}</Muted> : null}
      <TextInput
        placeholderTextColor={theme.textTertiary}
        selectionColor={Brand.primary}
        {...props}
        onFocus={(e) => {
          setFocused(true);
          props.onFocus?.(e);
        }}
        onBlur={(e) => {
          setFocused(false);
          props.onBlur?.(e);
        }}
        style={[
          styles.input,
          { color: theme.text, backgroundColor: theme.backgroundSelected, fontFamily },
          { boxShadow: focused ? `${Elevation.inset}, 0px 0px 0px 2px rgba(0, 122, 255, 0.55)` : Elevation.inset },
          style,
        ]}
      />
    </View>
  );
}

/** Usage bar for limits: a pressed-in track with a neon fill (amber at 80%, red at 100%). */
export function Meter({ label, used, cap, display }: { label: string; used: number; cap: number; display: string }) {
  const theme = useTheme();
  const ratio = cap > 0 ? Math.min(used / cap, 1) : 0;
  const fill = ratio >= 1 ? Tone.block.neon : ratio >= 0.8 ? Tone.warn.neon : Brand.primary;
  return (
    <View style={styles.meter}>
      <Row style={styles.between}>
        <ThemedText type="small">{label}</ThemedText>
        <ThemedText type="smallBold">{display}</ThemedText>
      </Row>
      <View style={[styles.track, { backgroundColor: theme.backgroundSelected }]}>
        <View style={[styles.fill, { width: `${ratio * 100}%`, backgroundColor: fill, boxShadow: `0px 0px 10px ${fill}` }]} />
      </View>
    </View>
  );
}

const BANNER_ICON: Record<ToneName, IconName> = {
  ok: 'checkmark-circle',
  warn: 'warning',
  block: 'alert-circle',
  info: 'information-circle',
  neutral: 'information-circle-outline',
};

/** Alert bar with an icon (success / warning / error / info). */
export function Banner({ tone, children }: { tone: ToneName; children: ReactNode }) {
  return (
    <View style={[styles.banner, { backgroundColor: Tone[tone].bg, borderColor: Tone[tone].line }]} accessibilityRole={tone === 'block' ? 'alert' : undefined}>
      <Ionicons name={BANNER_ICON[tone]} size={18} color={Tone[tone].fg} style={styles.bannerIcon} />
      <ThemedText type="small" style={[styles.bannerText, { color: Tone[tone].fg }]}>
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
  scroll: { padding: 20, gap: 18, paddingBottom: DockSpace, width: '100%', alignSelf: 'center' },
  card: { borderRadius: Radius.lg, padding: 18, gap: 10, boxShadow: Elevation[2] },
  led: { position: 'absolute', top: 14, right: 14, width: 8, height: 8, borderRadius: 4 },
  row: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two, flexWrap: 'wrap' },
  between: { justifyContent: 'space-between' },
  h1: { fontSize: 32, lineHeight: 38, fontWeight: '700' },
  h2: { fontSize: 19, lineHeight: 26, fontWeight: '700' },
  badge: { borderRadius: Radius.pill, paddingHorizontal: 10, paddingVertical: 3, alignSelf: 'flex-start' },
  badgeText: { fontSize: 12, lineHeight: 17, fontWeight: '600' },
  badgeRow: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  h2Icon: { width: 28, height: 28, borderRadius: 14, backgroundColor: Space.bg, alignItems: 'center', justifyContent: 'center', boxShadow: `0px 0px 10px rgba(77, 163, 255, 0.35)` },
  flexShrink: { flexShrink: 1 },
  button: { borderRadius: Radius.pill, paddingVertical: 14, paddingHorizontal: 22, alignItems: 'center', justifyContent: 'center', minHeight: 52 },
  buttonInner: { flexDirection: 'row', alignItems: 'center', gap: 8, justifyContent: 'center' },
  buttonText: { fontSize: 16, lineHeight: 22, fontWeight: '600', textAlign: 'center' },
  segmented: { flexDirection: 'row', borderRadius: Radius.pill, padding: 5, gap: 4, boxShadow: Elevation.inset },
  segment: { flex: 1, borderRadius: Radius.pill, paddingVertical: 10, paddingHorizontal: 6, alignItems: 'center' },
  segmentActive: { backgroundColor: Space.bg, boxShadow: '0px 0px 0px 1px rgba(77, 163, 255, 0.35), 0px 6px 14px rgba(14, 19, 36, 0.35)' },
  chip: { flexDirection: 'row', alignItems: 'center', gap: 6, borderRadius: Radius.pill, paddingHorizontal: 14, paddingVertical: 9 },
  chipSelected: { backgroundColor: Space.bg, boxShadow: '0px 0px 0px 1px rgba(77, 163, 255, 0.4), 0px 4px 12px rgba(14, 19, 36, 0.3)' },
  field: { gap: 6 },
  input: { borderRadius: Radius.md, paddingHorizontal: 16, paddingVertical: 13, fontSize: 16, minHeight: 52 },
  meter: { gap: 8 },
  track: { height: 12, borderRadius: Radius.pill, padding: 2, boxShadow: Elevation.inset, overflow: 'hidden' },
  fill: { height: 8, borderRadius: Radius.pill },
  banner: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, borderRadius: Radius.md, borderWidth: 1, paddingHorizontal: 14, paddingVertical: 12 },
  bannerIcon: { marginTop: 1 },
  bannerText: { flex: 1 },
});
