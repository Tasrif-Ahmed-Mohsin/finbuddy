import Constants from 'expo-constants';
import { Platform } from 'react-native';

/**
 * Where the Sathi backend lives.
 * 1. EXPO_PUBLIC_API_URL if set (e.g. a deployed server).
 * 2. In development on a phone: the same computer that serves the Expo bundle, port 8000.
 * 3. Fallback: localhost (web / emulator on the same machine).
 */
export function defaultApiBase(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL;
  if (fromEnv) return fromEnv.replace(/\/$/, '');
  const hostUri = Constants.expoConfig?.hostUri; // e.g. "192.168.1.5:8081"
  const host = hostUri?.split(':')[0];
  if (host) return `http://${host}:8000`;
  if (Platform.OS === 'android') return 'http://10.0.2.2:8000'; // Android emulator → host machine
  return 'http://localhost:8000';
}
