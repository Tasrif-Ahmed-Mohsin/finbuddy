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
      {/* One loop: Today (sense) · Plan · Save (the student's own money) · Family (act) · Sathi (talk, add messages) · Proof */}
      <Tabs.Screen name="index" options={{ title: t('tabToday'), tabBarIcon: icon('today-outline') }} />
      <Tabs.Screen name="plan" options={{ title: t('tabPlan'), tabBarIcon: icon('calendar-outline') }} />
      <Tabs.Screen name="save" options={{ title: t('tabSave'), tabBarIcon: icon('wallet-outline') }} />
      <Tabs.Screen name="family" options={{ title: t('tabFamily'), tabBarIcon: icon('people-outline') }} />
      <Tabs.Screen name="assistant" options={{ title: t('tabSathi'), tabBarIcon: icon('chatbubbles-outline') }} />
      <Tabs.Screen name="proof" options={{ title: t('tabProof'), tabBarIcon: icon('shield-checkmark-outline') }} />
    </Tabs>
  );
}
