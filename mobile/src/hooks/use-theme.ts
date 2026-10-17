import { Colors } from '@/constants/theme';

/** Sathi has one light theme (see constants/theme.ts), on every platform. */
export function useTheme() {
  return Colors.light;
}
