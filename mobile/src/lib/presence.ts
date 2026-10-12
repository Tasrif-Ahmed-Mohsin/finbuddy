import * as LocalAuthentication from 'expo-local-authentication';
import { Alert, Platform } from 'react-native';

/**
 * Prove the user is present before a risky action (approve a payment, unfreeze a card, report it lost):
 * biometrics or device PIN on the phone. Web preview (development only) has no biometrics, so the tap
 * itself is the confirmation. Devices without enrolled biometrics get an explicit confirmation dialog.
 */
export async function confirmPresence(message: string): Promise<boolean> {
  if (Platform.OS === 'web') return true;
  const hasHardware = await LocalAuthentication.hasHardwareAsync();
  const enrolled = hasHardware && (await LocalAuthentication.isEnrolledAsync());
  if (!enrolled) {
    return new Promise((resolve) =>
      Alert.alert('Confirm', `${message}\n\nNo fingerprint/face set up on this device; confirming without it.`, [
        { text: 'Cancel', style: 'cancel', onPress: () => resolve(false) },
        { text: 'Confirm', onPress: () => resolve(true) },
      ]),
    );
  }
  const result = await LocalAuthentication.authenticateAsync({ promptMessage: message, cancelLabel: 'Cancel' });
  return result.success;
}
