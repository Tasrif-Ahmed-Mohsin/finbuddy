import Ionicons from '@expo/vector-icons/Ionicons';
import { createContext, useContext, useEffect, useId, useState, type ComponentProps, type ReactNode } from 'react';
import { Pressable, StyleSheet, View, type LayoutChangeEvent, type ViewStyle } from 'react-native';
import Animated, {
  cancelAnimation,
  Easing,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withRepeat,
  withSequence,
  withSpring,
  withTiming,
} from 'react-native-reanimated';
import Svg, { Circle, Defs, LinearGradient, Path, RadialGradient, Rect, Stop } from 'react-native-svg';

import { ThemedText } from '@/components/themed-text';
import { Brand, Elevation, Radius, Space, Tone, type ToneName } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/**
 * The sci-fi widget kit: deep-space panels with neon numbers set into the soft neumorphic shell.
 * Every animation is a transform or an opacity change, so it runs the same on phones and on the web,
 * and every animation stops when the phone asks for reduced motion.
 */

type IconName = ComponentProps<typeof Ionicons>['name'];

// ---- deep-space panel ---------------------------------------------------------------------------------

/** A grid of faint neon lines, drawn once and cropped by the panel's rounded corners. */
const GRID = (() => {
  let d = '';
  for (let x = 0; x <= 1200; x += 26) d += `M${x},0 V800 `;
  for (let y = 0; y <= 800; y += 26) d += `M0,${y} H1200 `;
  return d;
})();

export function Panel({ children, style, tone = 'blue' }: { children: ReactNode; style?: ViewStyle; tone?: 'blue' | 'red' }) {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, '');
  const glow = tone === 'red' ? Tone.block.neon : Space.neon;
  return (
    <View style={[styles.panel, { borderColor: tone === 'red' ? 'rgba(255, 92, 92, 0.35)' : Space.rim }, style]}>
      <View style={StyleSheet.absoluteFill} pointerEvents="none">
        <Svg width="100%" height="100%" preserveAspectRatio="xMinYMin slice" viewBox="0 0 1200 800">
          <Defs>
            <RadialGradient id={`${uid}g`} cx="85%" cy="0%" r="70%">
              <Stop offset="0" stopColor={glow} stopOpacity={0.28} />
              <Stop offset="1" stopColor={glow} stopOpacity={0} />
            </RadialGradient>
          </Defs>
          <Path d={GRID} stroke={tone === 'red' ? 'rgba(255, 92, 92, 0.07)' : Space.grid} strokeWidth={1} />
          <Rect x="0" y="0" width="1200" height="800" fill={`url(#${uid}g)`} />
        </Svg>
      </View>
      {children}
    </View>
  );
}

/** Small uppercase label (like "HOUR", "MIN" on a watch face). */
export function Kicker({ children, dark, color, style }: { children: ReactNode; dark?: boolean; color?: string; style?: object }) {
  const theme = useTheme();
  return (
    <ThemedText display style={[styles.kicker, { color: color ?? (dark ? Space.muted : theme.textSecondary) }, style]}>
      {children}
    </ThemedText>
  );
}

/** Text on a dark panel. */
export function SpaceText({ children, muted, neon, style, small }: { children: ReactNode; muted?: boolean; neon?: boolean; small?: boolean; style?: object }) {
  return (
    <ThemedText type={small ? 'small' : 'default'} style={[{ color: neon ? Space.neon : muted ? Space.muted : Space.text }, style]}>
      {children}
    </ThemedText>
  );
}

/** Screen section title: a small uppercase kicker over an Exo 2 heading, with an optional thing on the right. */
export function SectionHeader({ kicker, title, right }: { kicker?: string; title: string; right?: ReactNode }) {
  return (
    <View style={styles.sectionHeader}>
      <View style={{ flex: 1, gap: 2 }}>
        {kicker ? <Kicker>{kicker}</Kicker> : null}
        <ThemedText display style={styles.sectionTitle}>
          {title}
        </ThemedText>
      </View>
      {right}
    </View>
  );
}

// ---- buttons -----------------------------------------------------------------------------------------

/** A raised neumorphic circle that presses in. `danger` glows red, `neon` glows blue. */
export function RoundButton({
  icon,
  onPress,
  label,
  tone = 'neutral',
  size = 44,
}: {
  icon: IconName;
  onPress: () => void;
  label: string;
  tone?: 'neutral' | 'danger' | 'neon';
  size?: number;
}) {
  const theme = useTheme();
  const color = tone === 'danger' ? Tone.block.neon : tone === 'neon' ? Space.neon : theme.text;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      hitSlop={6}
      style={({ pressed }) => [
        { width: size, height: size, borderRadius: size / 2, alignItems: 'center', justifyContent: 'center' },
        tone === 'neutral'
          ? { backgroundColor: theme.background, boxShadow: pressed ? Elevation.pressed : Elevation[1] }
          : {
              backgroundColor: Space.bg,
              boxShadow: pressed ? Elevation.pressed : `0px 0px 0px 1px ${tone === 'danger' ? 'rgba(255,92,92,0.45)' : Space.rim}, 0px 6px 16px ${tone === 'danger' ? 'rgba(255,92,92,0.35)' : 'rgba(0,122,255,0.35)'}`,
            },
      ]}>
      <Ionicons name={icon} size={size * 0.46} color={color} />
    </Pressable>
  );
}

/** A soft neon halo that breathes behind the screen's main action. */
export function GlowPulse({ children, radius = Radius.pill, color = Brand.primary }: { children: ReactNode; radius?: number; color?: string }) {
  const reduced = useReducedMotion();
  const t = useSharedValue(0);
  useEffect(() => {
    if (reduced) return;
    t.set(withRepeat(withSequence(withTiming(1, { duration: 1400, easing: Easing.inOut(Easing.sin) }), withTiming(0, { duration: 1400, easing: Easing.inOut(Easing.sin) })), -1));
    return () => cancelAnimation(t);
  }, [reduced, t]);
  const halo = useAnimatedStyle(() => ({ opacity: 0.12 + t.value * 0.28, transform: [{ scaleX: 1 + t.value * 0.03 }, { scaleY: 1 + t.value * 0.12 }] }));
  return (
    <View>
      <Animated.View pointerEvents="none" style={[StyleSheet.absoluteFill, { borderRadius: radius, backgroundColor: color }, halo]} />
      {children}
    </View>
  );
}

// ---- numbers ------------------------------------------------------------------------------------------

/** A big thin numeral that counts up when it appears (like the "07 / 37" clock face). */
export function BigNumber({
  value,
  format = (n) => String(Math.round(n)),
  size = 72,
  color,
  weight = '300',
}: {
  value: number;
  format?: (n: number) => string;
  size?: number;
  color?: string;
  weight?: '300' | '600' | '700';
}) {
  const theme = useTheme();
  const reduced = useReducedMotion();
  const [shown, setShown] = useState(0);
  useEffect(() => {
    if (reduced) return;
    let frame = 0;
    const start = Date.now();
    const from = 0;
    const tick = () => {
      const t = Math.min((Date.now() - start) / 700, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(from + (value - from) * eased);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    // A background tab may pause animation frames: never leave a half-counted (wrong) number on screen.
    const settle = setTimeout(() => setShown(value), 900);
    return () => {
      cancelAnimationFrame(frame);
      clearTimeout(settle);
    };
  }, [value, reduced]);
  return (
    <ThemedText display style={{ fontSize: size, lineHeight: Math.round(size * 1.05), fontWeight: weight, color: color ?? theme.text, fontVariant: ['tabular-nums'] }}>
      {format(reduced ? value : shown)}
    </ThemedText>
  );
}

/** A small raised tile: kicker, value, and one quiet line. */
export function StatTile({ label, value, sub, tone, style }: { label: string; value: string; sub?: string; tone?: ToneName; style?: ViewStyle }) {
  const theme = useTheme();
  return (
    <View style={[styles.tile, { backgroundColor: theme.background }, style]}>
      <Kicker>{label}</Kicker>
      <ThemedText display style={[styles.tileValue, tone && { color: Tone[tone].fg }]}>
        {value}
      </ThemedText>
      {sub ? (
        <ThemedText type="small" themeColor="textSecondary">
          {sub}
        </ThemedText>
      ) : null}
    </View>
  );
}

// ---- gauges -------------------------------------------------------------------------------------------

/** A capsule tank that fills with dark liquid and a moving wave, with the value in neon (the "Timing 68%" widget). */
export function LiquidCapsule({ pct, value, label, width = 92, height = 196 }: { pct: number; value: string; label: string; width?: number; height?: number }) {
  const theme = useTheme();
  const reduced = useReducedMotion();
  const inner = { w: width - 14, h: height - 14 };
  const level = useSharedValue(0);
  const wave = useSharedValue(0);
  useEffect(() => {
    level.set(withSpring(Math.max(0.06, Math.min(pct, 1)), { damping: 16, stiffness: 70 }));
  }, [pct, level]);
  useEffect(() => {
    if (reduced) return;
    wave.set(withRepeat(withTiming(1, { duration: 2600, easing: Easing.linear }), -1));
    return () => cancelAnimation(wave);
  }, [reduced, wave]);
  const fill = useAnimatedStyle(() => ({ height: level.value * inner.h }));
  const waveStyle = useAnimatedStyle(() => ({ transform: [{ translateX: -wave.value * inner.w }] }));
  const crest = 14;
  // Two wave periods side by side, so sliding one period to the left loops seamlessly.
  const w = inner.w;
  const d = `M0,${crest / 2} Q${w / 4},0 ${w / 2},${crest / 2} T${w},${crest / 2} T${w * 1.5},${crest / 2} T${w * 2},${crest / 2} V${crest + 4} H0 Z`;
  return (
    <View style={[styles.capsule, { width, height, borderRadius: width / 2, backgroundColor: theme.background }]} accessible accessibilityLabel={`${label} ${value}`}>
      <View style={[styles.capsuleWell, { width: inner.w, height: inner.h, borderRadius: inner.w / 2, backgroundColor: theme.backgroundSelected }]}>
        <Animated.View style={[styles.liquid, fill]}>
          <Animated.View style={[{ position: 'absolute', top: -crest + 1, left: 0, width: w * 2, height: crest + 4 }, waveStyle]}>
            <Svg width={w * 2} height={crest + 4}>
              <Path d={d} fill={Space.bg} />
            </Svg>
          </Animated.View>
        </Animated.View>
        <View style={styles.capsuleText} pointerEvents="none">
          <ThemedText display style={styles.capsuleValue}>
            {value}
          </ThemedText>
          <ThemedText style={styles.capsuleLabel}>{label}</ThemedText>
        </View>
      </View>
    </View>
  );
}

/** A dark dial with clock ticks lit up to the value and a slow scanner sweep (the neon clock widget). */
export function RingGauge({ pct, value, label, sub, size = 156 }: { pct: number; value: string; label: string; sub?: string; size?: number }) {
  const reduced = useReducedMotion();
  const sweep = useSharedValue(0);
  useEffect(() => {
    if (reduced) return;
    sweep.set(withRepeat(withTiming(1, { duration: 6000, easing: Easing.linear }), -1));
    return () => cancelAnimation(sweep);
  }, [reduced, sweep]);
  const sweepStyle = useAnimatedStyle(() => ({ transform: [{ rotate: `${sweep.value * 360}deg` }] }));
  const uid = useId().replace(/[^a-zA-Z0-9]/g, '');
  const c = 100;
  const lit = Math.round(Math.max(0, Math.min(pct, 1)) * 60);
  const ticks: { d: string; on: boolean; major: boolean }[] = [];
  for (let i = 0; i < 60; i++) {
    const a = (i / 60) * Math.PI * 2 - Math.PI / 2;
    const major = i % 5 === 0;
    const r1 = major ? 70 : 74;
    const r2 = 82;
    ticks.push({
      d: `M${c + Math.cos(a) * r1},${c + Math.sin(a) * r1} L${c + Math.cos(a) * r2},${c + Math.sin(a) * r2}`,
      on: i < lit,
      major,
    });
  }
  const r = 90;
  const circ = 2 * Math.PI * r;
  return (
    <View style={[styles.dial, { width: size, height: size, borderRadius: size * 0.22 }]} accessible accessibilityLabel={`${label} ${value}`}>
      <Svg width={size} height={size} viewBox="0 0 200 200">
        <Defs>
          <LinearGradient id={`${uid}a`} x1="0" y1="0" x2="1" y2="1">
            <Stop offset="0" stopColor="#5AB0FF" />
            <Stop offset="1" stopColor={Space.neonStrong} />
          </LinearGradient>
        </Defs>
        <Circle cx={c} cy={c} r={r} stroke="rgba(77, 163, 255, 0.12)" strokeWidth={4} fill="none" />
        <Circle
          cx={c}
          cy={c}
          r={r}
          stroke={`url(#${uid}a)`}
          strokeWidth={4}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={`${circ * Math.max(0.001, Math.min(pct, 1))} ${circ}`}
          transform={`rotate(-90 ${c} ${c})`}
        />
        {ticks.map((t, i) => (
          <Path key={i} d={t.d} stroke={t.on ? Space.neon : 'rgba(142, 154, 192, 0.35)'} strokeWidth={t.major ? 3 : 1.6} strokeLinecap="round" />
        ))}
      </Svg>
      {!reduced && (
        <Animated.View pointerEvents="none" style={[StyleSheet.absoluteFill, { alignItems: 'center' }, sweepStyle]}>
          <View style={{ width: 2, height: size * 0.11, marginTop: size * 0.08, backgroundColor: 'rgba(77, 163, 255, 0.85)', borderRadius: 1, boxShadow: `0px 0px 6px ${Space.neon}` }} />
        </Animated.View>
      )}
      <View style={styles.dialText} pointerEvents="none">
        <ThemedText display style={[styles.dialValue, { fontSize: size * 0.2, lineHeight: size * 0.24 }]}>
          {value}
        </ThemedText>
        <ThemedText style={styles.dialLabel}>{label}</ThemedText>
        {sub ? <ThemedText style={styles.dialSub}>{sub}</ThemedText> : null}
      </View>
    </View>
  );
}

/** Battery widget: a dark icon chip, a label, the number and five cells (the "electricity 90" widget). */
export function Battery({ pct, label, value, icon = 'flash' }: { pct: number; label: string; value: string; icon?: IconName }) {
  const theme = useTheme();
  const cells = Math.round(Math.max(0, Math.min(pct, 1)) * 5);
  return (
    <View style={styles.battery} accessible accessibilityLabel={`${label} ${value}`}>
      <View style={styles.batteryIcon}>
        <Ionicons name={icon} size={18} color={Space.neon} />
      </View>
      <View style={{ flex: 1, gap: 2 }}>
        <ThemedText type="small" themeColor="textSecondary">
          {label}
        </ThemedText>
        <ThemedText display style={styles.batteryValue}>
          {value}
        </ThemedText>
      </View>
      <View style={[styles.batteryShell, { borderColor: theme.text }]}>
        {[0, 1, 2, 3, 4].map((i) => (
          <View key={i} style={[styles.batteryCell, { backgroundColor: i < cells ? theme.text : 'transparent' }]} />
        ))}
        <View style={[styles.batteryCap, { backgroundColor: theme.text }]} />
      </View>
    </View>
  );
}

// ---- calendar strip and money route ----------------------------------------------------------------------

export type DayInfo = { date: string; today: boolean; bd: { open: boolean; reason: string | null }; cn: { open: boolean; reason: string | null } };

/** A week of day pills (like the calendar widget). Today glows; two dots under each day: BD bank, CN bank. */
export function DayStrip({ days, weekday }: { days: DayInfo[]; weekday: (iso: string) => string }) {
  const theme = useTheme();
  return (
    <View style={styles.strip}>
      {days.map((d) => (
        <View key={d.date} style={styles.stripDay} accessible accessibilityLabel={`${weekday(d.date)} ${Number(d.date.slice(8))}: BD ${d.bd.open ? 'open' : d.bd.reason ?? 'closed'}, CN ${d.cn.open ? 'open' : d.cn.reason ?? 'closed'}`}>
          <ThemedText display style={[styles.stripWeekday, d.today && { color: Brand.primary }]}>
            {weekday(d.date)}
          </ThemedText>
          {d.today ? <TodayPill n={Number(d.date.slice(8))} /> : (
            <View style={[styles.dayPill, { backgroundColor: theme.background, boxShadow: Elevation[1] }]}>
              <ThemedText display style={styles.dayNum}>
                {Number(d.date.slice(8))}
              </ThemedText>
            </View>
          )}
          <View style={styles.dots}>
            <View style={[styles.dot, { backgroundColor: d.bd.open ? Tone.ok.neon : Tone.block.neon }]} />
            <View style={[styles.dot, { backgroundColor: d.cn.open ? Tone.ok.neon : Tone.block.neon }]} />
          </View>
        </View>
      ))}
    </View>
  );
}

function TodayPill({ n }: { n: number }) {
  const reduced = useReducedMotion();
  const t = useSharedValue(0);
  useEffect(() => {
    if (reduced) return;
    t.set(withRepeat(withSequence(withTiming(1, { duration: 1200 }), withTiming(0, { duration: 1200 })), -1));
    return () => cancelAnimation(t);
  }, [reduced, t]);
  const halo = useAnimatedStyle(() => ({ opacity: 0.25 + t.value * 0.45 }));
  return (
    <View>
      <Animated.View pointerEvents="none" style={[styles.todayHalo, halo]} />
      <View style={[styles.dayPill, styles.todayPill]}>
        <ThemedText display style={[styles.dayNum, { color: Space.neon }]}>
          {n}
        </ThemedText>
      </View>
    </View>
  );
}

/** Bangladesh → China as a neon capsule: a rocket glides across while money is on the way, or waits docked. */
export function RouteBeam({ moving, height = 64 }: { moving: boolean; height?: number }) {
  const reduced = useReducedMotion();
  const [w, setW] = useState(0);
  const x = useSharedValue(0);
  const bob = useSharedValue(0);
  useEffect(() => {
    if (reduced || !w) return;
    if (moving) {
      x.set(0);
      x.set(withRepeat(withTiming(1, { duration: 3600, easing: Easing.inOut(Easing.quad) }), -1));
    } else {
      cancelAnimation(x);
      x.set(withTiming(0, { duration: 300 }));
    }
    bob.set(withRepeat(withSequence(withTiming(1, { duration: 900 }), withTiming(0, { duration: 900 })), -1));
    return () => {
      cancelAnimation(x);
      cancelAnimation(bob);
    };
  }, [moving, reduced, w, x, bob]);
  const track = Math.max(0, w - height * 2 - 30);
  const rocket = useAnimatedStyle(() => ({ transform: [{ translateX: x.value * track }, { translateY: (bob.value - 0.5) * 3 }, { rotate: '45deg' }] }));
  const onLayout = (e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width);
  return (
    <View onLayout={onLayout} style={[styles.route, { height, borderRadius: height / 2 }]}>
      <Ionicons name="earth" size={height * 0.5} color={Space.neon} style={styles.routeEnd} />
      <View style={styles.routeMid}>
        <Svg width="100%" height={height} preserveAspectRatio="none" viewBox="0 0 100 10" style={StyleSheet.absoluteFill}>
          <Path d="M0,5 H100" stroke="rgba(77, 163, 255, 0.45)" strokeWidth={0.6} strokeDasharray="2 2" />
        </Svg>
        <Animated.View style={[styles.rocket, rocket]}>
          <Ionicons name="rocket" size={height * 0.38} color="#BFE0FF" />
        </Animated.View>
        <SparkleField />
      </View>
      <Ionicons name="planet" size={height * 0.5} color={Space.neon} style={styles.routeEnd} />
    </View>
  );
}

function SparkleField() {
  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill}>
      <Ionicons name="sparkles" size={10} color="rgba(191, 224, 255, 0.7)" style={{ position: 'absolute', left: '22%', top: 8 }} />
      <Ionicons name="star" size={6} color="rgba(191, 224, 255, 0.6)" style={{ position: 'absolute', left: '58%', bottom: 10 }} />
      <Ionicons name="star" size={5} color="rgba(191, 224, 255, 0.5)" style={{ position: 'absolute', left: '80%', top: 12 }} />
    </View>
  );
}

// ---- seal ---------------------------------------------------------------------------------------------

/** A neon seal with a slowly turning dashed ring: the log checks out (or, in red, it does not). */
export function Seal({ ok, size = 64 }: { ok: boolean; size?: number }) {
  const reduced = useReducedMotion();
  const spin = useSharedValue(0);
  useEffect(() => {
    if (reduced) return;
    spin.set(withRepeat(withTiming(1, { duration: 9000, easing: Easing.linear }), -1));
    return () => cancelAnimation(spin);
  }, [reduced, spin]);
  const ring = useAnimatedStyle(() => ({ transform: [{ rotate: `${spin.value * 360}deg` }] }));
  const color = ok ? Space.neon : Tone.block.neon;
  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Animated.View style={[StyleSheet.absoluteFill, ring]}>
        <Svg width={size} height={size} viewBox="0 0 64 64">
          <Circle cx="32" cy="32" r="29" stroke={color} strokeWidth={1.6} strokeDasharray="4 5" fill="none" opacity={0.8} />
        </Svg>
      </Animated.View>
      <View style={{ width: size * 0.72, height: size * 0.72, borderRadius: size, backgroundColor: Space.bg, alignItems: 'center', justifyContent: 'center', boxShadow: `0px 0px 14px ${ok ? 'rgba(77,163,255,0.45)' : 'rgba(255,92,92,0.45)'}` }}>
        <Ionicons name={ok ? 'shield-checkmark' : 'warning'} size={size * 0.36} color={color} />
      </View>
    </View>
  );
}

// ---- bento grid -----------------------------------------------------------------------------------------

const BentoWidth = createContext<{ col: number; gap: number }>({ col: 0, gap: 14 });

/** A dashboard grid: 2 columns on a phone, 4 on a wide screen. Children are <Tile span={1|2|...}>. */
export function Bento({ children, gap = 14, columns }: { children: ReactNode; gap?: number; columns?: number }) {
  const [w, setW] = useState(0);
  const cols = columns ?? (w >= 900 ? 4 : 2);
  const col = w ? (w - gap * (cols - 1)) / cols : 0;
  return (
    <View onLayout={(e) => setW(e.nativeEvent.layout.width)} style={{ flexDirection: 'row', flexWrap: 'wrap', gap }}>
      <BentoWidth.Provider value={{ col, gap }}>{w ? children : null}</BentoWidth.Provider>
    </View>
  );
}

export function Tile({ span = 1, children, style, onPress, label }: { span?: number; children: ReactNode; style?: ViewStyle; onPress?: () => void; label?: string }) {
  const theme = useTheme();
  const { col, gap } = useContext(BentoWidth);
  const width = col * span + gap * (span - 1);
  const base = [styles.tile, { width, backgroundColor: theme.background }, style];
  if (!onPress) return <View style={base}>{children}</View>;
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={label} onPress={onPress} style={({ pressed }) => [...base, pressed && { boxShadow: Elevation.pressed }]}>
      {children}
    </Pressable>
  );
}

/** Lets a child know the width one bento column has (for sizing gauges). */
export function useBentoColumn() {
  return useContext(BentoWidth).col;
}

// ---- styles ----------------------------------------------------------------------------------------------

const styles = StyleSheet.create({
  panel: { backgroundColor: Space.bg, borderRadius: Radius.lg, borderWidth: 1, padding: 18, gap: 10, overflow: 'hidden', boxShadow: Elevation.space },
  kicker: { fontSize: 11, lineHeight: 14, fontWeight: '600', letterSpacing: 1.6, textTransform: 'uppercase' },
  sectionHeader: { flexDirection: 'row', alignItems: 'flex-end', gap: 10, marginTop: 6 },
  sectionTitle: { fontSize: 22, lineHeight: 28, fontWeight: '700' },
  tile: { borderRadius: Radius.lg, padding: 16, gap: 6, boxShadow: Elevation[2] },
  tileValue: { fontSize: 26, lineHeight: 32, fontWeight: '600' },
  capsule: { alignItems: 'center', justifyContent: 'center', boxShadow: Elevation[2] },
  capsuleWell: { overflow: 'hidden', justifyContent: 'flex-end', boxShadow: Elevation.inset },
  liquid: { width: '100%', backgroundColor: Space.bg },
  capsuleText: { position: 'absolute', left: 0, right: 0, bottom: 12, alignItems: 'center' },
  capsuleValue: { fontSize: 20, lineHeight: 24, fontWeight: '600', color: Space.neon },
  capsuleLabel: { fontSize: 11, lineHeight: 14, color: Space.muted, textAlign: 'center', paddingHorizontal: 6 },
  dial: { backgroundColor: Space.bg, alignItems: 'center', justifyContent: 'center', overflow: 'hidden', borderWidth: 1, borderColor: Space.rim, boxShadow: Elevation.space },
  dialText: { position: 'absolute', alignItems: 'center' },
  dialValue: { fontWeight: '300', color: Space.text },
  dialLabel: { fontSize: 11, lineHeight: 14, color: Space.neon, letterSpacing: 1.2, textTransform: 'uppercase' },
  dialSub: { fontSize: 10, lineHeight: 13, color: Space.muted },
  battery: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  batteryIcon: { width: 38, height: 38, borderRadius: 12, backgroundColor: Space.bg, alignItems: 'center', justifyContent: 'center', boxShadow: '0px 0px 10px rgba(77, 163, 255, 0.35)' },
  batteryValue: { fontSize: 20, lineHeight: 24, fontWeight: '600' },
  batteryShell: { flexDirection: 'row', alignItems: 'center', gap: 3, borderWidth: 2, borderRadius: 7, padding: 3, height: 30 },
  batteryCell: { width: 7, height: 18, borderRadius: 2 },
  batteryCap: { position: 'absolute', right: -6, width: 3, height: 10, borderRadius: 2 },
  strip: { flexDirection: 'row', justifyContent: 'space-between' },
  stripDay: { alignItems: 'center', gap: 8, flex: 1 },
  stripWeekday: { fontSize: 11, lineHeight: 14, fontWeight: '600', letterSpacing: 1, color: '#5F6470', textTransform: 'uppercase' },
  dayPill: { minWidth: 38, height: 38, borderRadius: 19, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 4 },
  todayPill: { backgroundColor: Space.bg, boxShadow: `0px 0px 0px 1px ${Space.rim}` },
  todayHalo: { position: 'absolute', left: -4, right: -4, top: -4, bottom: -4, borderRadius: 24, backgroundColor: 'rgba(0, 122, 255, 0.35)' },
  dayNum: { fontSize: 16, lineHeight: 20, fontWeight: '600' },
  dots: { flexDirection: 'row', gap: 4 },
  dot: { width: 6, height: 6, borderRadius: 3 },
  route: { flexDirection: 'row', alignItems: 'center', backgroundColor: Space.bg, borderWidth: 2, borderColor: Space.neonStrong, paddingHorizontal: 14, boxShadow: '0px 0px 14px rgba(46, 139, 255, 0.55), inset 0px 0px 10px rgba(46, 139, 255, 0.35)', overflow: 'hidden' },
  routeEnd: { textShadowColor: Space.neon, textShadowRadius: 8 },
  routeMid: { flex: 1, height: '100%', justifyContent: 'center', marginHorizontal: 6 },
  rocket: { position: 'absolute', left: 0 },
});

