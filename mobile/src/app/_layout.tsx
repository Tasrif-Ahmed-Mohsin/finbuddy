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
          <Stack.Screen name="renewal/[item]" options={{ headerShown: true, title: 'Renewal', presentation: 'modal' }} />
          <Stack.Screen name="passport" options={{ headerShown: true, title: 'Passport', presentation: 'modal' }} />
          <Stack.Screen name="settings" options={{ headerShown: true, title: 'Settings', presentation: 'modal' }} />
          <Stack.Screen name="emergency" options={{ headerShown: true, title: 'Emergency · জরুরি · 紧急', presentation: 'modal' }} />
        </Stack>
      </ThemeProvider>
    </SessionProvider>
  );
}
