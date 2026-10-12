import { DarkTheme, DefaultTheme, ThemeProvider } from 'expo-router';
import { Stack } from 'expo-router/stack';
import { useColorScheme } from 'react-native';

import { SessionProvider } from '@/lib/session';

export default function RootLayout() {
  const scheme = useColorScheme();
  return (
    <SessionProvider>
      <ThemeProvider value={scheme === 'dark' ? DarkTheme : DefaultTheme}>
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="draft/[id]" options={{ headerShown: true, title: 'Payment', presentation: 'modal' }} />
        </Stack>
      </ThemeProvider>
    </SessionProvider>
  );
}
