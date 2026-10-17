import Ionicons from '@expo/vector-icons/Ionicons';
import { useEffect, useId, useRef, type ComponentProps } from 'react';
import { Pressable, StyleSheet, View, type ViewStyle } from 'react-native';
import Animated, {
  cancelAnimation,
  Easing,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withSpring,
  withTiming,
  type SharedValue,
} from 'react-native-reanimated';
import Svg, { Defs, Ellipse, LinearGradient, Path, RadialGradient, Rect, Stop } from 'react-native-svg';

import { Brand, Elevation, Palette } from '@/constants/theme';

/**
 * Sathi, the money buddy: a small graphite robot with a dark visor and two square eyes.
 * It breathes, blinks and looks around on its own, and changes mood with what is happening:
 * thinking while the agent works, talking when it answers, a shield when it refuses something unsafe,
 * a question mark when it needs one more detail, a little jump when money arrives safely.
 * Every part is a plain View transform, so the same animations run on Android, iOS and the web.
 * With "reduce motion" switched on, it keeps its expressions but stops moving.
 */
export type MascotMood =
  | 'idle'
  | 'happy'
  | 'thinking'
  | 'talking'
  | 'curious'
  | 'worried'
  | 'alert'
  | 'protect'
  | 'celebrate'
  | 'sleep';

export type MascotAction = { type: 'wave' | 'jump' | 'nod' | 'shake'; key: number };

type IconName = ComponentProps<typeof Ionicons>['name'];
type Eye = 'open' | 'happy' | 'closed' | 'small' | 'worried' | 'focused';

type Pose = {
  eye: Eye;
  gaze: [number, number];
  eyeScale: number;
  tilt: number; // head, degrees
  arms: [number, number]; // left, right (degrees; left raises with +, right with -)
  bob: { amp: number; ms: number };
  glow: number;
  badge?: { icon?: IconName; dots?: boolean; color?: string };
};

const POSES: Record<MascotMood, Pose> = {
  idle: { eye: 'open', gaze: [0, 0], eyeScale: 1, tilt: 0, arms: [6, -6], bob: { amp: 3, ms: 2000 }, glow: 0.15 },
  happy: { eye: 'happy', gaze: [0, -1], eyeScale: 1, tilt: 4, arms: [28, -28], bob: { amp: 4, ms: 1300 }, glow: 0.55 },
  thinking: { eye: 'small', gaze: [7, -6], eyeScale: 1, tilt: -6, arms: [4, -60], bob: { amp: 2, ms: 2600 }, glow: 0.7, badge: { dots: true } },
  talking: { eye: 'open', gaze: [0, 1], eyeScale: 1, tilt: 2, arms: [14, -14], bob: { amp: 3, ms: 1100 }, glow: 0.9 },
  curious: { eye: 'open', gaze: [-5, -4], eyeScale: 1.08, tilt: 9, arms: [8, -8], bob: { amp: 2, ms: 2200 }, glow: 0.45, badge: { icon: 'help' } },
  worried: { eye: 'worried', gaze: [0, 3], eyeScale: 0.9, tilt: -3, arms: [-4, 4], bob: { amp: 1.5, ms: 2400 }, glow: 0.1 },
  alert: { eye: 'open', gaze: [0, 0], eyeScale: 1.18, tilt: 0, arms: [40, -40], bob: { amp: 2, ms: 900 }, glow: 0.6, badge: { icon: 'alert', color: '#E08A00' } },
  protect: { eye: 'focused', gaze: [0, 1], eyeScale: 1, tilt: 0, arms: [70, -70], bob: { amp: 1, ms: 2600 }, glow: 0.8, badge: { icon: 'shield-checkmark' } },
  celebrate: { eye: 'happy', gaze: [0, -2], eyeScale: 1.05, tilt: 0, arms: [110, -110], bob: { amp: 5, ms: 900 }, glow: 1, badge: { icon: 'sparkles' } },
  sleep: { eye: 'closed', gaze: [0, 3], eyeScale: 1, tilt: -8, arms: [0, 0], bob: { amp: 2, ms: 3600 }, glow: 0, badge: { icon: 'moon' } },
};

const EYE_W = 22;
const EYE_H = 26;
const sine = Easing.inOut(Easing.sin);

/** Breathing / bobbing loop. */
function loop(sv: SharedValue<number>, amp: number, ms: number) {
  sv.set(withRepeat(withSequence(withTiming(-amp, { duration: ms / 2, easing: sine }), withTiming(0, { duration: ms / 2, easing: sine })), -1));
}

export function Mascot({
  size = 120,
  mood = 'idle',
  action,
  look,
  onPress,
  accessibilityLabel = 'Sathi',
  style,
  neon = true,
}: {
  size?: number;
  mood?: MascotMood;
  /** One-shot gesture: change `key` to play it again. */
  action?: MascotAction;
  /** Override where the eyes look (e.g. 'down' at the text box while someone types). */
  look?: 'down' | 'left' | 'right';
  onPress?: () => void;
  accessibilityLabel?: string;
  style?: ViewStyle;
  /** Sci-fi trims: glowing ear lights and a neon visor rim. */
  neon?: boolean;
}) {
  const k = size / 200;
  const px = (n: number) => n * k;
  const reduced = useReducedMotion();
  const uid = useId().replace(/[^a-zA-Z0-9]/g, '');
  const pose = POSES[mood];

  const bob = useSharedValue(0);
  const jumpY = useSharedValue(0);
  const shiver = useSharedValue(0);
  const headRot = useSharedValue(0);
  const headY = useSharedValue(0);
  const armL = useSharedValue(pose.arms[0]);
  const armR = useSharedValue(pose.arms[1]);
  const blink = useSharedValue(1);
  const talk = useSharedValue(1);
  const eyeX = useSharedValue(0);
  const eyeY = useSharedValue(0);
  const eyePop = useSharedValue(1);
  const glow = useSharedValue(pose.glow);
  const badge = useSharedValue(pose.badge ? 1 : 0);
  const phase = useSharedValue(0); // drives the thinking dots and the voice bars
  const poseRef = useRef(pose);
  useEffect(() => {
    poseRef.current = pose;
  }, [pose]);

  // ---- mood: settle into the pose and start its loops ------------------------------------------
  useEffect(() => {
    const p = POSES[mood];
    [bob, jumpY, shiver, talk, phase].forEach(cancelAnimation);
    const spring = { damping: 14, stiffness: 140 };
    headRot.set(withSpring(p.tilt, spring));
    armL.set(withSpring(p.arms[0], spring));
    armR.set(withSpring(p.arms[1], spring));
    eyePop.set(reduced ? 1 : withSequence(withTiming(0.75, { duration: 90 }), withSpring(1, { damping: 9, stiffness: 220 })));
    glow.set(withTiming(p.glow, { duration: 400 }));
    badge.set(p.badge ? withSpring(1, { damping: 10, stiffness: 180 }) : withTiming(0, { duration: 150 }));
    if (reduced) {
      bob.set(0);
      talk.set(1);
      shiver.set(0);
      return;
    }
    loop(bob, p.bob.amp, p.bob.ms);
    if (mood === 'talking') {
      talk.set(withRepeat(withSequence(withTiming(0.8, { duration: 150 }), withTiming(1, { duration: 170 })), -1));
    } else {
      talk.set(withTiming(1, { duration: 120 }));
    }
    if (mood === 'thinking' || mood === 'talking') {
      phase.set(0);
      phase.set(withRepeat(withTiming(1, { duration: mood === 'talking' ? 700 : 1200, easing: Easing.linear }), -1));
    }
    if (mood === 'worried') {
      shiver.set(withRepeat(withSequence(withTiming(1, { duration: 70 }), withTiming(-1, { duration: 70 })), -1, true));
    } else {
      shiver.set(withTiming(0, { duration: 100 }));
    }
    if (mood === 'celebrate') {
      jumpY.set(withRepeat(
        withSequence(withTiming(-18, { duration: 230, easing: Easing.out(Easing.quad) }), withTiming(0, { duration: 260, easing: Easing.in(Easing.quad) })),
        3,
      ));
    }
    if (mood === 'alert') {
      headRot.set(withSequence(withTiming(-6, { duration: 70 }), withTiming(6, { duration: 90 }), withTiming(-3, { duration: 80 }), withSpring(p.tilt)));
    }
  }, [mood, reduced, bob, jumpY, shiver, talk, phase, headRot, armL, armR, eyePop, glow, badge]);

  // ---- gaze: the pose's direction, or where the screen asks it to look ----------------------------
  useEffect(() => {
    const [gx, gy] = look === 'down' ? [0, 7] : look === 'left' ? [-8, 1] : look === 'right' ? [8, 1] : pose.gaze;
    eyeX.set(withSpring(gx, { damping: 15, stiffness: 160 }));
    eyeY.set(withSpring(gy, { damping: 15, stiffness: 160 }));
  }, [look, pose.gaze, eyeX, eyeY]);

  // ---- life: blink every few seconds, and glance around when nothing is going on ----------------
  useEffect(() => {
    if (reduced) return;
    let blinkTimer: ReturnType<typeof setTimeout>;
    let glanceTimer: ReturnType<typeof setTimeout>;
    const scheduleBlink = () => {
      blinkTimer = setTimeout(() => {
        const e = poseRef.current.eye;
        if (e === 'open' || e === 'small' || e === 'focused' || e === 'worried') {
          blink.set(withSequence(withTiming(0.08, { duration: 70 }), withTiming(1, { duration: 120 })));
        }
        scheduleBlink();
      }, 2400 + Math.random() * 2800);
    };
    const scheduleGlance = () => {
      glanceTimer = setTimeout(() => {
        if (poseRef.current === POSES.idle && !look) {
          const side = Math.random() < 0.5 ? -1 : 1;
          eyeX.set(withSequence(withTiming(4 * side, { duration: 260 }), withDelay(900, withTiming(-3 * side, { duration: 300 })), withDelay(700, withSpring(0))));
        }
        scheduleGlance();
      }, 5200 + Math.random() * 3500);
    };
    scheduleBlink();
    scheduleGlance();
    return () => {
      clearTimeout(blinkTimer);
      clearTimeout(glanceTimer);
    };
  }, [reduced, look, blink, eyeX]);

  // ---- one-shot gestures ---------------------------------------------------------------------------
  useEffect(() => {
    if (!action || reduced) return;
    const p = poseRef.current;
    if (action.type === 'wave') {
      armR.set(withSequence(
        withTiming(-125, { duration: 260, easing: Easing.out(Easing.back(1.4)) }),
        withRepeat(withSequence(withTiming(-95, { duration: 170 }), withTiming(-125, { duration: 170 })), 3),
        withSpring(p.arms[1]),
      ));
      headRot.set(withSequence(withTiming(p.tilt + 6, { duration: 220 }), withDelay(1000, withSpring(p.tilt))));
    } else if (action.type === 'jump') {
      jumpY.set(withSequence(withTiming(-18, { duration: 200, easing: Easing.out(Easing.quad) }), withSpring(0, { damping: 7, stiffness: 200 })));
    } else if (action.type === 'nod') {
      headY.set(withSequence(withTiming(5, { duration: 130 }), withTiming(0, { duration: 130 }), withTiming(5, { duration: 130 }), withTiming(0, { duration: 160 })));
    } else if (action.type === 'shake') {
      headRot.set(withSequence(
        withTiming(p.tilt - 8, { duration: 90 }),
        withTiming(p.tilt + 8, { duration: 110 }),
        withTiming(p.tilt - 5, { duration: 100 }),
        withTiming(p.tilt + 4, { duration: 90 }),
        withSpring(p.tilt),
      ));
    }
  }, [action, reduced, armR, headRot, jumpY, headY]);

  // ---- animated styles -------------------------------------------------------------------------------
  const botStyle = useAnimatedStyle(() => ({ transform: [{ translateY: (bob.value + jumpY.value) * k }, { translateX: shiver.value * 0.7 * k }] }));
  const shadowStyle = useAnimatedStyle(() => {
    const lift = -(bob.value + jumpY.value);
    return { opacity: Math.max(0.25, 1 - lift * 0.035), transform: [{ scaleX: Math.max(0.6, 1 - lift * 0.018) }] };
  });
  const headStyle = useAnimatedStyle(() => ({ transform: [{ translateY: headY.value * k }, { rotate: `${headRot.value}deg` }] }));
  const armLStyle = useAnimatedStyle(() => ({ transform: [{ rotate: `${armL.value}deg` }] }));
  const armRStyle = useAnimatedStyle(() => ({ transform: [{ rotate: `${armR.value}deg` }] }));
  const eyesStyle = useAnimatedStyle(() => ({ transform: [{ translateX: eyeX.value * k }, { translateY: eyeY.value * k }, { scale: eyePop.value }] }));
  const lidStyle = useAnimatedStyle(() => ({ transform: [{ scaleY: blink.value * talk.value }] }));
  const glowStyle = useAnimatedStyle(() => ({ opacity: glow.value }));
  const earStyle = useAnimatedStyle(() => ({ opacity: 0.45 + glow.value * 0.55 }));
  const badgeStyle = useAnimatedStyle(() => ({ opacity: badge.value, transform: [{ scale: 0.3 + badge.value * 0.7 }] }));

  const eye = pose.eye;
  const tiltL = eye === 'worried' ? -14 : eye === 'focused' ? 9 : 0;
  const eyeBox = (left: number, tilt: number) => (
    <Animated.View style={[{ position: 'absolute', left: px(left), top: px(28), width: px(EYE_W), height: px(EYE_H) }, lidStyle]}>
      <View style={{ flex: 1, transform: [{ rotate: `${tilt}deg` }, { scale: pose.eyeScale }] }}>
        <EyeShape kind={eye} w={px(EYE_W)} h={px(EYE_H)} />
      </View>
    </Animated.View>
  );

  const body = (
    <View style={{ width: size, height: size * 1.1 }}>
      {/* ground shadow */}
      <Animated.View style={[{ position: 'absolute', left: px(50), top: px(204), width: px(100), height: px(14) }, shadowStyle]}>
        <Svg width="100%" height="100%" viewBox="0 0 100 14">
          <Ellipse cx="50" cy="7" rx="50" ry="7" fill={Palette.ink} opacity={0.13} />
        </Svg>
      </Animated.View>

      <Animated.View style={[StyleSheet.absoluteFill, botStyle]}>
        {/* arms (behind the body) */}
        <Animated.View style={[{ position: 'absolute', left: px(46), top: px(144), width: px(26), height: px(40), transformOrigin: '80% 14%' }, armLStyle]}>
          <Limb id={`${uid}l`} />
        </Animated.View>
        <Animated.View style={[{ position: 'absolute', left: px(128), top: px(144), width: px(26), height: px(40), transformOrigin: '20% 14%' }, armRStyle]}>
          <Limb id={`${uid}r`} />
        </Animated.View>

        {/* body with two little feet */}
        <View style={{ position: 'absolute', left: px(64), top: px(122), width: px(72), height: px(82) }}>
          <Svg width="100%" height="100%" viewBox="0 0 72 82">
            <Defs>
              <LinearGradient id={`${uid}b`} x1="0" y1="0" x2="0" y2="1">
                <Stop offset="0" stopColor="#7B7E82" />
                <Stop offset="1" stopColor="#4B4E52" />
              </LinearGradient>
            </Defs>
            <Path d="M14,0 H58 Q72,0 72,14 V62 Q72,80 56,80 H44 Q38,80 36,73 Q34,80 28,80 H16 Q0,80 0,62 V14 Q0,0 14,0 Z" fill={`url(#${uid}b)`} />
            <Ellipse cx="26" cy="22" rx="14" ry="6" fill="#FFFFFF" opacity={0.1} />
          </Svg>
        </View>

        {/* head, visor and eyes */}
        <Animated.View style={[{ position: 'absolute', left: px(12), top: px(4), width: px(176), height: px(140), transformOrigin: '50% 94%' }, headStyle]}>
          <Svg width="100%" height="100%" viewBox="0 0 176 140">
            <Defs>
              <LinearGradient id={`${uid}h`} x1="0" y1="0" x2="0.35" y2="1">
                <Stop offset="0" stopColor="#9C9FA3" />
                <Stop offset="0.55" stopColor="#74777B" />
                <Stop offset="1" stopColor="#56595D" />
              </LinearGradient>
              <LinearGradient id={`${uid}e`} x1="0" y1="0" x2="0" y2="1">
                <Stop offset="0" stopColor="#6F7276" />
                <Stop offset="1" stopColor="#45484C" />
              </LinearGradient>
              <LinearGradient id={`${uid}v`} x1="0" y1="0" x2="0.3" y2="1">
                <Stop offset="0" stopColor="#2E2E33" />
                <Stop offset="0.5" stopColor={Palette.ink} />
                <Stop offset="1" stopColor="#0E0E10" />
              </LinearGradient>
            </Defs>
            <Rect x="0" y="48" width="18" height="42" rx="7" fill={`url(#${uid}e)`} />
            <Rect x="158" y="48" width="18" height="42" rx="7" fill={`url(#${uid}e)`} />
            <Rect x="10" y="2" width="156" height="132" rx="46" fill={`url(#${uid}h)`} />
            <Ellipse cx="72" cy="20" rx="50" ry="11" fill="#FFFFFF" opacity={0.16} />
            <Rect x="28" y="26" width="120" height="90" rx="34" fill="#3D4044" />
            {neon && <Rect x="28.5" y="26.5" width="119" height="89" rx="33.5" fill="none" stroke={Brand.neon} strokeWidth="1.6" opacity={0.85} />}
            <Rect x="33" y="31" width="110" height="80" rx="30" fill={`url(#${uid}v)`} />
            <Path d="M47,52 Q50,40 64,38" stroke="#FFFFFF" strokeWidth="4.5" strokeLinecap="round" fill="none" opacity={0.2} />
            <Ellipse cx="74" cy="38" rx="2.6" ry="2.4" fill="#FFFFFF" opacity={0.2} />
          </Svg>
          {/* neon ear lights, breathing with the mood */}
          {neon && (
            <>
              <Animated.View style={[styles.ear, { left: px(6), top: px(56), width: px(6), height: px(26), borderRadius: px(3) }, earStyle]} />
              <Animated.View style={[styles.ear, { left: px(164), top: px(56), width: px(6), height: px(26), borderRadius: px(3) }, earStyle]} />
            </>
          )}
          {/* everything inside the visor */}
          <View style={{ position: 'absolute', left: px(33), top: px(31), width: px(110), height: px(80), borderRadius: px(30), overflow: 'hidden' }}>
            <Animated.View style={[{ position: 'absolute', left: px(10), top: px(6), width: px(90), height: px(70) }, glowStyle]}>
              <Svg width="100%" height="100%" viewBox="0 0 90 70">
                <Defs>
                  <RadialGradient id={`${uid}g`} cx="50%" cy="50%" r="50%">
                    <Stop offset="0" stopColor={Brand.primary} stopOpacity={0.55} />
                    <Stop offset="1" stopColor={Brand.primary} stopOpacity={0} />
                  </RadialGradient>
                </Defs>
                <Ellipse cx="45" cy="35" rx="45" ry="35" fill={`url(#${uid}g)`} />
              </Svg>
            </Animated.View>
            <Animated.View style={[StyleSheet.absoluteFill, eyesStyle]}>
              {eyeBox(28, tiltL)}
              {eyeBox(60, -tiltL)}
            </Animated.View>
            {mood === 'talking' && <VoiceBars phase={phase} k={k} />}
          </View>
        </Animated.View>
      </Animated.View>

      {/* mood badge: shield, question, sparkles, thinking dots */}
      {pose.badge && (
        <Animated.View
          pointerEvents="none"
          style={[styles.badge, { left: px(146), top: px(-2), width: px(46), height: px(46), borderRadius: px(23) }, badgeStyle]}>
          {pose.badge.dots ? (
            <ThinkingDots phase={phase} k={k} />
          ) : pose.badge.icon ? (
            <Ionicons name={pose.badge.icon} size={Math.max(12, px(24))} color={pose.badge.color ?? Brand.primary} />
          ) : null}
        </Animated.View>
      )}
    </View>
  );

  if (!onPress) {
    return (
      <View style={style} accessible accessibilityRole="image" accessibilityLabel={accessibilityLabel}>
        {body}
      </View>
    );
  }
  return (
    <Pressable onPress={onPress} style={style} accessibilityRole="button" accessibilityLabel={accessibilityLabel} hitSlop={8}>
      {body}
    </Pressable>
  );
}

function Limb({ id }: { id: string }) {
  return (
    <Svg width="100%" height="100%" viewBox="0 0 26 40">
      <Defs>
        <LinearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor="#7B7E82" />
          <Stop offset="1" stopColor="#505357" />
        </LinearGradient>
      </Defs>
      <Rect x="4" y="2" width="18" height="34" rx="9" fill={`url(#${id})`} />
    </Svg>
  );
}

function EyeShape({ kind, w, h }: { kind: Eye; w: number; h: number }) {
  const c = Palette.snow;
  return (
    <Svg width={w} height={h} viewBox={`0 0 ${EYE_W} ${EYE_H}`}>
      {kind === 'happy' ? (
        <Path d="M3,18 Q11,4 19,18" stroke={c} strokeWidth="5.5" strokeLinecap="round" fill="none" />
      ) : kind === 'closed' ? (
        <Rect x="1" y="13" width="20" height="4.5" rx="2.2" fill={c} />
      ) : kind === 'small' ? (
        <Rect x="4" y="5" width="14" height="17" rx="5" fill={c} />
      ) : kind === 'focused' ? (
        <Rect x="0" y="8" width="22" height="18" rx="6" fill={c} />
      ) : (
        <Rect x="0" y="0" width="22" height="26" rx="7" fill={c} />
      )}
    </Svg>
  );
}

function ThinkingDots({ phase, k }: { phase: SharedValue<number>; k: number }) {
  return (
    <View style={styles.dots}>
      {[0, 1, 2].map((i) => (
        <Dot key={i} i={i} phase={phase} k={k} />
      ))}
    </View>
  );
}

function Dot({ i, phase, k }: { i: number; phase: SharedValue<number>; k: number }) {
  const st = useAnimatedStyle(() => {
    const t = (phase.value - i * 0.22 + 1) % 1;
    const lift = Math.sin(Math.PI * Math.min(t * 2, 1));
    return { opacity: 0.35 + 0.65 * lift, transform: [{ translateY: -lift * 3 * k }] };
  });
  const d = Math.max(4, 7 * k);
  return <Animated.View style={[{ width: d, height: d, borderRadius: d / 2, backgroundColor: Brand.primary }, st]} />;
}

function VoiceBars({ phase, k }: { phase: SharedValue<number>; k: number }) {
  return (
    <View style={[styles.voice, { bottom: px2(k, 9), gap: px2(k, 4) }]}>
      {[0, 1, 2].map((i) => (
        <Bar key={i} i={i} phase={phase} k={k} />
      ))}
    </View>
  );
}

function Bar({ i, phase, k }: { i: number; phase: SharedValue<number>; k: number }) {
  const st = useAnimatedStyle(() => ({ transform: [{ scaleY: 0.3 + 0.7 * Math.abs(Math.sin(Math.PI * 2 * (phase.value + i / 3))) }] }));
  return <Animated.View style={[{ width: px2(k, 4), height: px2(k, 10), borderRadius: px2(k, 2), backgroundColor: '#3D9BFF' }, st]} />;
}

const px2 = (k: number, n: number) => n * k;

const styles = StyleSheet.create({
  ear: { position: 'absolute', backgroundColor: Brand.neon, boxShadow: `0px 0px 8px ${Brand.neon}` },
  badge: { position: 'absolute', backgroundColor: '#FFFFFF', alignItems: 'center', justifyContent: 'center', boxShadow: Elevation[2] },
  dots: { flexDirection: 'row', gap: 3, alignItems: 'center' },
  voice: { position: 'absolute', left: 0, right: 0, flexDirection: 'row', justifyContent: 'center', alignItems: 'center' },
});
