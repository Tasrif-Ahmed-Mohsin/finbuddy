/** Small saved preferences (role, language, first launch done): secure storage on the phone, localStorage on the web. */
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const web = Platform.OS === 'web';

export async function getPref(key: string): Promise<string | null> {
  try {
    return web ? (globalThis.localStorage?.getItem(`sathi.${key}`) ?? null) : await SecureStore.getItemAsync(`sathi.${key}`);
  } catch {
    return null;
  }
}

export async function setPref(key: string, value: string): Promise<void> {
  try {
    if (web) globalThis.localStorage?.setItem(`sathi.${key}`, value);
    else await SecureStore.setItemAsync(`sathi.${key}`, value);
  } catch {
    // a preference that cannot be saved is asked again next time; nothing else depends on it
  }
}
