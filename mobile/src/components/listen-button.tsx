import * as Speech from 'expo-speech';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui';
import type { Lang } from '@/lib/i18n';
import { useSession } from '@/lib/session';

const VOICE: Record<Lang, string> = { en: 'en-US', bn: 'bn-BD', zh: 'zh-CN' };

/**
 * Reads a text aloud in the user's language (explain-before-sign). The text always comes from the server's
 * templates, built from the exact fields being approved or signed, never from the AI.
 */
export function ListenButton({ text, lang }: { text: string; lang: Lang }) {
  const { t } = useSession();
  const [speaking, setSpeaking] = useState(false);
  useEffect(() => () => void Speech.stop(), []);

  function toggle() {
    if (speaking) {
      Speech.stop();
      setSpeaking(false);
      return;
    }
    setSpeaking(true);
    Speech.speak(text, { language: VOICE[lang], onDone: () => setSpeaking(false), onStopped: () => setSpeaking(false) });
  }
  return <Button title={speaking ? `■ ${t('stopListening')}` : `🔊 ${t('listen')}`} variant="secondary" onPress={toggle} />;
}
