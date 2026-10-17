import Ionicons from '@expo/vector-icons/Ionicons';
import { useEffect, useRef, useState } from 'react';
import { Platform, Pressable, StyleSheet } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withRepeat, withTiming } from 'react-native-reanimated';

import { Brand, Elevation, Tone } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import type { Lang } from '@/lib/i18n';
import { useSession } from '@/lib/session';

// The speech module is native: present in the app build and on the web (Web Speech API), absent in Expo Go.
type SpeechModule = typeof import('expo-speech-recognition').ExpoSpeechRecognitionModule;
let Speech: SpeechModule | null = null;
try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  Speech = require('expo-speech-recognition').ExpoSpeechRecognitionModule as SpeechModule;
} catch {
  Speech = null;
}

const LOCALE: Record<Lang, string> = { bn: 'bn-BD', en: 'en-US', zh: 'zh-CN' };
const GOOGLE = 'com.google.android.googlequicksearchbox';

function available(): boolean {
  try {
    return !!Speech && Speech.isRecognitionAvailable();
  } catch {
    return false;
  }
}

/**
 * Speak instead of typing: Bangla (bn-BD), English or Chinese, in the chat's language. Words appear in the box as
 * they are heard; the person reads them and taps send (nothing is sent by voice alone). Free: Android's speech
 * service (Google) on the phone, the browser's speech recognition on the web.
 */
export function VoiceButton({ onText, onError }: { onText: (text: string) => void; onError: (message: string) => void }) {
  const { t, lang } = useSession();
  const theme = useTheme();
  const [listening, setListening] = useState(false);
  const pulse = useSharedValue(1);
  const textRef = useRef(onText);
  useEffect(() => {
    textRef.current = onText;
  }, [onText]);

  useEffect(() => {
    if (!Speech) return;
    const subs = [
      Speech.addListener('start', () => setListening(true)),
      Speech.addListener('end', () => setListening(false)),
      Speech.addListener('result', (e) => {
        const said = e.results[0]?.transcript;
        if (said) textRef.current(said);
      }),
      Speech.addListener('error', (e) => {
        setListening(false);
        if (e.error !== 'aborted' && e.error !== 'no-speech') onError(e.error === 'not-allowed' ? t('voiceDenied') : `${t('voiceUnavailable')} (${e.error})`);
      }),
    ];
    return () => subs.forEach((s) => s.remove());
  }, [onError, t]);

  useEffect(() => {
    pulse.set(listening ? withRepeat(withTiming(1.18, { duration: 650 }), -1, true) : withTiming(1));
  }, [listening, pulse]);
  const ring = useAnimatedStyle(() => ({ transform: [{ scale: pulse.get() }] }));

  async function toggle() {
    if (!Speech || !available()) {
      onError(t('voiceUnavailable'));
      return;
    }
    if (listening) {
      Speech.stop();
      return;
    }
    const perm = await Speech.requestPermissionsAsync();
    if (!perm.granted) {
      onError(t('voiceDenied'));
      return;
    }
    let service: string | undefined;
    if (Platform.OS === 'android') {
      try {
        service = Speech.getSpeechRecognitionServices().includes(GOOGLE) ? GOOGLE : undefined;
      } catch {
        service = undefined;
      }
    }
    Speech.start({ lang: LOCALE[lang], interimResults: true, continuous: false, maxAlternatives: 1, androidRecognitionServicePackage: service });
  }

  return (
    <Animated.View style={ring}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={listening ? t('voiceListening') : t('voiceStart')}
        onPress={toggle}
        style={({ pressed }) => [
          local.button,
          { backgroundColor: listening ? Tone.block.neon : theme.backgroundElement, boxShadow: listening ? Elevation.glow : Elevation[1] },
          pressed && { transform: [{ scale: 0.94 }] },
        ]}>
        <Ionicons name={listening ? 'stop' : 'mic'} size={22} color={listening ? '#FFFFFF' : Brand.primary} />
      </Pressable>
    </Animated.View>
  );
}

const local = StyleSheet.create({
  button: { width: 48, height: 48, borderRadius: 24, alignItems: 'center', justifyContent: 'center' },
});
