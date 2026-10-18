import Ionicons from '@expo/vector-icons/Ionicons';
import type { BottomTabBarProps } from 'expo-router/js-tabs';
import type { ComponentProps } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { Mascot } from '@/components/mascot';
import { ThemedText } from '@/components/themed-text';
import { Brand, Colors, Elevation, Space } from '@/constants/theme';

type IconName = ComponentProps<typeof Ionicons>['name'];

const ICONS: Record<string, [IconName, IconName]> = {
  index: ['home-outline', 'home'],
  plan: ['calendar-outline', 'calendar'],
  save: ['shield-half-outline', 'shield-half'],
  family: ['people-outline', 'people'],
};

/**
 * The floating dock: a raised neumorphic capsule with four tabs and, in the middle, Bluefin in a glowing round
 * button that rises above the bar. The chosen tab's icon sits in a small deep-space pill with a neon icon.
 */
export function Dock({ state, descriptors, navigation, insets }: BottomTabBarProps) {
  return (
    <View pointerEvents="box-none" style={[styles.wrap, { bottom: Math.max(insets.bottom, 8) + 8 }]}>
      <View style={styles.bar}>
        {state.routes.map((route, index) => {
          const focused = state.index === index;
          const label = descriptors[route.key].options.title ?? route.name;
          const onPress = () => {
            const event = navigation.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
            if (!focused && !event.defaultPrevented) navigation.navigate(route.name, route.params);
          };
          if (route.name === 'assistant') {
            return (
              <View key={route.key} style={styles.centerSlot}>
                <Pressable
                  accessibilityRole="tab"
                  accessibilityState={{ selected: focused }}
                  accessibilityLabel={label}
                  onPress={onPress}
                  style={({ pressed }) => [styles.center, focused && styles.centerOn, pressed && { transform: [{ scale: 0.96 }] }]}>
                  <View style={styles.centerClip}>
                    <Mascot size={58} mood={focused ? 'happy' : 'idle'} style={{ marginTop: 6 }} />
                  </View>
                </Pressable>
                <ThemedText style={[styles.label, { color: focused ? Brand.primary : Colors.light.textSecondary }]}>{label}</ThemedText>
              </View>
            );
          }
          const [off, on] = ICONS[route.name] ?? ['ellipse-outline', 'ellipse'];
          return (
            <Pressable
              key={route.key}
              accessibilityRole="tab"
              accessibilityState={{ selected: focused }}
              accessibilityLabel={label}
              onPress={onPress}
              style={styles.item}>
              <View style={[styles.iconPill, focused && styles.iconPillOn]}>
                <Ionicons name={focused ? on : off} size={20} color={focused ? Space.neon : Colors.light.textSecondary} />
              </View>
              <ThemedText style={[styles.label, { color: focused ? Brand.primary : Colors.light.textSecondary }]}>{label}</ThemedText>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { position: 'absolute', left: 14, right: 14, alignItems: 'center' },
  bar: {
    width: '100%',
    maxWidth: 520,
    height: 70,
    borderRadius: 35,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingHorizontal: 8,
    backgroundColor: Colors.light.background,
    boxShadow: Elevation[3],
  },
  item: { flex: 1, alignItems: 'center', gap: 3 },
  iconPill: { width: 44, height: 30, borderRadius: 15, alignItems: 'center', justifyContent: 'center' },
  iconPillOn: { backgroundColor: Space.bg, boxShadow: '0px 0px 0px 1px rgba(77, 163, 255, 0.35), 0px 4px 12px rgba(0, 122, 255, 0.35)' },
  label: { fontSize: 11, lineHeight: 15, fontWeight: '600' },
  centerSlot: { flex: 1, alignItems: 'center', justifyContent: 'flex-end', height: '100%', paddingBottom: 8 },
  center: {
    position: 'absolute',
    top: -30,
    width: 66,
    height: 66,
    borderRadius: 33,
    backgroundColor: Space.bg,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: Space.neonStrong,
    boxShadow: '0px 0px 16px rgba(46, 139, 255, 0.6), 0px 10px 22px rgba(14, 19, 36, 0.35)',
  },
  centerOn: { borderColor: Space.neon, boxShadow: '0px 0px 24px rgba(77, 163, 255, 0.9), 0px 10px 22px rgba(14, 19, 36, 0.35)' },
  centerClip: { width: 60, height: 60, borderRadius: 30, overflow: 'hidden', alignItems: 'center' },
});
