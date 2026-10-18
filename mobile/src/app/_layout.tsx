import { useFonts } from 'expo-font';
import { DefaultTheme, ThemeProvider, type Theme } from 'expo-router';
import { Stack } from 'expo-router/stack';
import { StatusBar } from 'expo-status-bar';
import { Platform } from 'react-native';

import { Brand, Colors, FontFamily, Palette } from '@/constants/theme';
import { BASE_FONTS, FontProvider } from '@/lib/fonts';
import { SessionProvider } from '@/lib/session';

const NavTheme: Theme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: Brand.primary,
    background: Colors.light.background,
    card: Colors.light.background,
    text: Palette.ink,
    border: Colors.light.border,
    notification: Brand.primary,
  },
};

const modal = (title: string) => ({
  headerShown: true,
  title,
  presentation: 'modal' as const,
  headerShadowVisible: false,
  headerStyle: { backgroundColor: Colors.light.background },
  headerTintColor: Brand.primary,
  headerTitleStyle: { fontFamily: FontFamily.display[700], color: Palette.ink, fontSize: 17 },
});

export default function RootLayout() {
  const [loaded, error] = useFonts(BASE_FONTS);
  // On a phone the fonts are local and load in a blink; the web shows the system font until they arrive.
  if (!loaded && !error && Platform.OS !== 'web') return null;
  return (
    <SessionProvider>
      <FontProvider>
        <ThemeProvider value={NavTheme}>
          <StatusBar style="dark" />
          <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: Colors.light.background } }}>
            <Stack.Screen name="(tabs)" />
            <Stack.Screen name="draft/[id]" options={modal('Payment')} />
            <Stack.Screen name="renewal/[item]" options={modal('Renewal')} />
            <Stack.Screen name="passport" options={modal('Passport')} />
            <Stack.Screen name="settings" options={modal('Settings')} />
            <Stack.Screen name="buddy" options={modal('Bluefin')} />
            <Stack.Screen name="judge" options={modal('Judge mode')} />
            <Stack.Screen name="banks" options={modal('Banks')} />
            <Stack.Screen name="privacy" options={modal('Privacy')} />
            <Stack.Screen name="story" options={modal('Story')} />
            <Stack.Screen name="welcome" />
            <Stack.Screen name="emergency" options={modal('Emergency · জরুরি · 紧急')} />
          </Stack>
        </ThemeProvider>
      </FontProvider>
    </SessionProvider>
  );
}
