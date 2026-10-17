import { HindSiliguri_400Regular } from '@expo-google-fonts/hind-siliguri/400Regular';
import { HindSiliguri_500Medium } from '@expo-google-fonts/hind-siliguri/500Medium';
import { HindSiliguri_600SemiBold } from '@expo-google-fonts/hind-siliguri/600SemiBold';
import { HindSiliguri_700Bold } from '@expo-google-fonts/hind-siliguri/700Bold';
import { Inter_400Regular } from '@expo-google-fonts/inter/400Regular';
import { Inter_500Medium } from '@expo-google-fonts/inter/500Medium';
import { Inter_600SemiBold } from '@expo-google-fonts/inter/600SemiBold';
import { Inter_700Bold } from '@expo-google-fonts/inter/700Bold';
import { Exo2_300Light } from '@expo-google-fonts/exo-2/300Light';
import { Exo2_600SemiBold } from '@expo-google-fonts/exo-2/600SemiBold';
import { Exo2_700Bold } from '@expo-google-fonts/exo-2/700Bold';
import * as Font from 'expo-font';
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { Platform } from 'react-native';

import { FontFamily } from '@/constants/theme';
import type { Lang } from '@/lib/i18n';
import { useSession } from '@/lib/session';

/**
 * Fonts: Exo 2 for headings and big numbers (light for the big thin numerals), Inter for reading,
 * Hind Siliguri for Bangla (loaded only when someone switches to Bangla), and the system font for Chinese.
 */
export const BASE_FONTS = {
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
  Exo2_300Light,
  Exo2_600SemiBold,
  Exo2_700Bold,
};

const BANGLA_FONTS = { HindSiliguri_400Regular, HindSiliguri_500Medium, HindSiliguri_600SemiBold, HindSiliguri_700Bold };

// On the web a font may still be downloading: fall back to the system font instead of a serif.
const WEB_FALLBACK = 'system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans Bengali", "PingFang SC", "Microsoft YaHei", sans-serif';

const FontState = createContext({ bangla: false });

export function FontProvider({ children }: { children: ReactNode }) {
  const { lang } = useSession();
  const [bangla, setBangla] = useState(() => Font.isLoaded(FontFamily.bangla[400]));
  useEffect(() => {
    if (lang !== 'bn' || bangla) return;
    let alive = true;
    Font.loadAsync(BANGLA_FONTS)
      .then(() => alive && setBangla(true))
      .catch(() => {}); // the system Bangla font is used instead
    return () => {
      alive = false;
    };
  }, [lang, bangla]);
  return <FontState.Provider value={{ bangla }}>{children}</FontState.Provider>;
}

export function useFontState() {
  return useContext(FontState);
}

function pick<T extends Record<number, string>>(set: T, weight: number): string {
  const sizes = Object.keys(set).map(Number).sort((a, b) => a - b);
  const best = sizes.filter((w) => w <= weight).pop() ?? sizes[0];
  return set[best];
}

/** The font family for this weight and language, or undefined to use the system font (Chinese). */
export function fontFamilyFor(weight: number, display: boolean, lang: Lang, banglaReady: boolean): string | undefined {
  if (lang === 'zh') return undefined;
  let family: string;
  if (lang === 'bn') {
    if (!banglaReady) return undefined;
    family = pick(FontFamily.bangla, weight);
  } else {
    family = display ? pick(FontFamily.display, weight) : pick(FontFamily.body, weight);
  }
  return Platform.OS === 'web' ? `${family}, ${WEB_FALLBACK}` : family;
}
