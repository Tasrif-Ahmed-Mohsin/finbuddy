import { StyleSheet, Text, type TextProps, type TextStyle } from 'react-native';

import { Brand, Fonts, ThemeColor } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { fontFamilyFor, useFontState } from '@/lib/fonts';
import { useSession } from '@/lib/session';

export type ThemedTextProps = TextProps & {
  type?: 'default' | 'title' | 'small' | 'smallBold' | 'subtitle' | 'link' | 'linkPrimary' | 'code';
  themeColor?: ThemeColor;
  /** Use the display face (headings, big numbers). Text of 22px or more uses it automatically. */
  display?: boolean;
};

function weightOf(w: TextStyle['fontWeight']): number {
  if (w == null || w === 'normal') return 400;
  if (w === 'bold') return 700;
  const n = Number(w);
  return Number.isFinite(n) ? n : 400;
}

export function ThemedText({ style, type = 'default', themeColor, display, ...rest }: ThemedTextProps) {
  const theme = useTheme();
  const { lang } = useSession();
  const { bangla } = useFontState();
  const flat: TextStyle = StyleSheet.flatten([{ color: theme[themeColor ?? 'text'] }, styles[type], style]) ?? {};

  if (type === 'code') return <Text style={flat} {...rest} />;
  const isDisplay = display ?? (type === 'title' || type === 'subtitle' || (flat.fontSize ?? 16) >= 22);
  const family = fontFamilyFor(weightOf(flat.fontWeight), isDisplay, lang, bangla);
  const fix: TextStyle = family ? { fontFamily: family, fontWeight: 'normal' } : {};
  // Bangla glyphs are taller: give lines a little more room.
  if (lang === 'bn' && flat.lineHeight) fix.lineHeight = Math.round(flat.lineHeight * 1.12);
  return <Text style={[flat, fix]} {...rest} />;
}

const styles = StyleSheet.create({
  default: { fontSize: 16, lineHeight: 24, fontWeight: '400' },
  small: { fontSize: 14, lineHeight: 20, fontWeight: '400' },
  smallBold: { fontSize: 14, lineHeight: 20, fontWeight: '600' },
  title: { fontSize: 34, lineHeight: 40, fontWeight: '800' },
  subtitle: { fontSize: 24, lineHeight: 30, fontWeight: '700' },
  link: { fontSize: 14, lineHeight: 22, fontWeight: '600' },
  linkPrimary: { fontSize: 14, lineHeight: 22, fontWeight: '600', color: Brand.primary },
  code: { fontFamily: Fonts.mono, fontSize: 12 },
});
