import { useState } from 'react';

import { SathiAdd } from '@/components/sathi-add';
import { SathiChat } from '@/components/sathi-chat';
import { SathiDocument } from '@/components/sathi-document';
import { SathiUpdates } from '@/components/sathi-updates';
import { H1, Screen, Segmented } from '@/components/ui';
import { useSession } from '@/lib/session';

type Pane = 'updates' | 'chat' | 'add' | 'doc';

export default function AssistantScreen() {
  const { t } = useSession();
  const [pane, setPane] = useState<Pane>('updates');
  return (
    <Screen>
      <H1>{t('askSathi')}</H1>
      <Segmented<Pane>
        value={pane}
        onChange={setPane}
        options={[
          { value: 'updates', label: t('updates') },
          { value: 'chat', label: t('chat') },
          { value: 'add', label: 'SMS' },
          { value: 'doc', label: '📷' },
        ]}
      />
      {pane === 'updates' && <SathiUpdates />}
      {pane === 'chat' && <SathiChat />}
      {pane === 'add' && <SathiAdd />}
      {pane === 'doc' && <SathiDocument />}
    </Screen>
  );
}
