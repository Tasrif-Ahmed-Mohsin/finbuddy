import Ionicons from '@expo/vector-icons/Ionicons';
import { Tabs } from 'expo-router/js-tabs';
import type { ComponentProps } from 'react';
import type { ColorValue } from 'react-native';

import { Brand } from '@/constants/theme';
import { useSession } from '@/lib/session';

type IconName = ComponentProps<typeof Ionicons>['name'];

function icon(name: IconName) {
  function TabIcon({ color, size }: { color: ColorValue; size: number }) {
    return <Ionicons name={name} color={color} size={size} />;
  }
  return TabIcon;
}

export default function TabsLayout() {
  const { t } = useSession();
  return (
    <Tabs screenOptions={{ headerShown: false, tabBarActiveTintColor: Brand.primary }}>
      <Tabs.Screen name="index" options={{ title: t('tabHome'), tabBarIcon: icon('home-outline') }} />
      <Tabs.Screen name="plan" options={{ title: t('tabPlan'), tabBarIcon: icon('calculator-outline') }} />
      <Tabs.Screen name="assistant" options={{ title: t('tabSathi'), tabBarIcon: icon('chatbubbles-outline') }} />
      <Tabs.Screen name="activity" options={{ title: t('tabActivity'), tabBarIcon: icon('shield-checkmark-outline') }} />
      <Tabs.Screen name="settings" options={{ title: t('tabSettings'), tabBarIcon: icon('settings-outline') }} />
    </Tabs>
  );
}
