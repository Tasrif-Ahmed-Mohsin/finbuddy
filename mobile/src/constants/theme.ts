/**
 * Bluefin design tokens: neumorphism with a sci-fi twist.
 * A soft light shell (raised capsules, pressed-in wells) holds dark "deep-space" panels with neon-blue numbers,
 * the way a mission-control dashboard would. Built on the palette #F5F5F7 · #1D1D1F · #AAAAAA · #007AFF.
 * Light shell only, on the phone and the web alike.
 */

import '@/global.css';

import { Platform } from 'react-native';

/** The four palette colours. Everything else is derived from them. */
export const Palette = {
  snow: '#F5F5F7',
  ink: '#1D1D1F',
  gray: '#AAAAAA',
  blue: '#007AFF',
} as const;

/** The light neumorphic shell. Surfaces share the background colour; shadows give them depth. */
export const Colors = {
  light: {
    text: Palette.ink,
    /** Secondary text, readable on the shell (AA). */
    textSecondary: '#5F6470',
    /** Placeholders and quiet labels. Icons that only decorate may use the palette gray. */
    textTertiary: '#8A909C',
    background: '#EEF0F4',
    backgroundElement: '#EEF0F4',
    /** Pressed-in wells: tracks, inputs. */
    backgroundSelected: '#E3E6EC',
    border: 'rgba(255, 255, 255, 0.7)',
    accent: Palette.blue,
    accentSoft: '#DCEBFF',
  },
} as const;

export type ThemeColor = keyof typeof Colors.light;

/** Dark "deep-space" panels for the one number that matters on each screen. */
export const Space = {
  bg: '#0E1324',
  bg2: '#161C30',
  rim: 'rgba(77, 163, 255, 0.28)',
  grid: 'rgba(77, 163, 255, 0.08)',
  text: '#E8EEFF',
  muted: '#8E9AC0',
  neon: '#4DA3FF',
  neonStrong: '#2E8BFF',
} as const;

export const Brand = {
  primary: Palette.blue,
  primaryPressed: '#0062CC',
  primaryText: '#FFFFFF',
  primarySoft: '#DCEBFF',
  ink: Palette.ink,
  neon: Space.neon,
} as const;

/** Status on the light shell: soft tints with dark text (AA). */
export const Tone = {
  ok: { fg: '#17703A', bg: '#DDF3E6', line: '#BFE6CC', neon: '#3DDC97' },
  warn: { fg: '#8A5300', bg: '#FBEFCF', line: '#F5DDA0', neon: '#FFC24D' },
  block: { fg: '#C42B1C', bg: '#FBE1DE', line: '#F4C3BE', neon: '#FF5C5C' },
  info: { fg: '#0062CC', bg: '#DCEBFF', line: '#BCD7FF', neon: '#4DA3FF' },
  neutral: { fg: '#5F6470', bg: '#E3E6EC', line: '#D6DAE2', neon: '#9AA6C2' },
} as const;
export type ToneName = keyof typeof Tone;

const LIGHT = 'rgba(255, 255, 255, 0.92)';
const DARK = 'rgba(163, 170, 184, 0.45)';

/** Neumorphic depth, as box-shadow strings (identical on iOS, Android and the web). */
export const Elevation = {
  /** small raised (chips, round buttons) */
  1: `-3px -3px 8px ${LIGHT}, 3px 3px 8px ${DARK}`,
  /** raised (cards, tiles) */
  2: `-6px -6px 14px ${LIGHT}, 6px 6px 16px ${DARK}`,
  /** floating (the dock, big tiles) */
  3: `-8px -8px 20px ${LIGHT}, 10px 10px 24px rgba(163, 170, 184, 0.55)`,
  /** pressed-in well (inputs, tracks) */
  inset: `inset 4px 4px 8px ${DARK}, inset -4px -4px 8px ${LIGHT}`,
  /** a button while pressed */
  pressed: `inset 3px 3px 6px rgba(163, 170, 184, 0.55), inset -3px -3px 6px ${LIGHT}`,
  /** neon-blue glow for the main action */
  glow: '0px 0px 0px 1px rgba(77, 163, 255, 0.35), 0px 8px 22px rgba(0, 122, 255, 0.35)',
  /** a deep-space panel lifting off the shell */
  space: '0px 12px 28px rgba(14, 19, 36, 0.32), 0px 2px 6px rgba(14, 19, 36, 0.2)',
} as const;

export const Radius = {
  sm: 12,
  md: 18,
  lg: 24,
  pill: 999,
} as const;

/** Font families (loaded in app/_layout.tsx). Bangla uses Hind Siliguri; Chinese uses the system font. */
export const FontFamily = {
  body: { 400: 'Inter_400Regular', 500: 'Inter_500Medium', 600: 'Inter_600SemiBold', 700: 'Inter_700Bold' },
  display: { 300: 'Exo2_300Light', 600: 'Exo2_600SemiBold', 700: 'Exo2_700Bold' },
  bangla: { 400: 'HindSiliguri_400Regular', 500: 'HindSiliguri_500Medium', 600: 'HindSiliguri_600SemiBold', 700: 'HindSiliguri_700Bold' },
} as const;

export const Fonts = Platform.select({
  ios: { mono: 'ui-monospace' },
  default: { mono: 'monospace' },
  web: { mono: 'var(--font-mono)' },
});

export const Spacing = {
  half: 2,
  one: 4,
  two: 8,
  three: 16,
  four: 24,
  five: 32,
  six: 64,
} as const;

export const BottomTabInset = Platform.select({ ios: 50, android: 80 }) ?? 0;
/** Reading screens stay narrow; the Home dashboard can use more width on a desktop. */
export const MaxContentWidth = 760;
export const MaxWideWidth = 1100;
/** Room at the bottom of every screen for the floating dock. */
export const DockSpace = 120;
