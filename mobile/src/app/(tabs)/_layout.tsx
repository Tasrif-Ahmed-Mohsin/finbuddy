import { Redirect } from 'expo-router';
import { Tabs } from 'expo-router/js-tabs';

import { Dock } from '@/components/dock';
import { Colors } from '@/constants/theme';
import { useSession } from '@/lib/session';

/**
 * Five places, one loop: Home (sense) · Plan · Bluefin (talk, in the middle) · Save (the student's own money) ·
 * Family (act, and the proof of everything that was done).
 */
export default function TabsLayout() {
  const { t, ready, onboarded, aiChoices } = useSession();
  if (ready && !onboarded) return <Redirect href="/welcome" />;  // first launch: four short cards first
  // Nobody on this phone has answered about the AI yet (e.g. an older install): ask that one card before the app.
  if (ready && aiChoices.parent === null && aiChoices.student === null) {
    return <Redirect href={{ pathname: '/welcome', params: { step: 'data' } }} />;
  }
  return (
    <Tabs tabBar={(props) => <Dock {...props} />} screenOptions={{ headerShown: false, sceneStyle: { backgroundColor: Colors.light.background } }}>
      <Tabs.Screen name="index" options={{ title: t('tabHome') }} />
      <Tabs.Screen name="plan" options={{ title: t('tabPlan') }} />
      <Tabs.Screen name="assistant" options={{ title: t('tabSathi') }} />
      <Tabs.Screen name="save" options={{ title: t('tabSave') }} />
      <Tabs.Screen name="family" options={{ title: t('tabFamily') }} />
    </Tabs>
  );
}
