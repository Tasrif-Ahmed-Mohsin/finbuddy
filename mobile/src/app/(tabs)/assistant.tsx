import { useState } from 'react';

import { SathiAdd } from '@/components/sathi-add';
import { SathiChat } from '@/components/sathi-chat';
import { SathiDocument } from '@/components/sathi-document';
import { SathiUpdates } from '@/components/sathi-updates';
import { Kicker } from '@/components/neo';
import { H1, Screen, Segmented } from '@/components/ui';
import { useSession } from '@/lib/session';

type Pane = 'chat' | 'add' | 'doc' | 'updates';

export default function AssistantScreen() {
  const { t } = useSession();
  const [pane, setPane] = useState<Pane>('chat');
  return (
    <Screen>
      <Kicker>{t('sathiKicker')}</Kicker>
      <H1>{t('askSathi')}</H1>
      <Segmented<Pane>
        value={pane}
        onChange={setPane}
        options={[
          { value: 'chat', label: t('chat') },
          { value: 'add', label: 'SMS' },
          { value: 'doc', label: t('photoTab') },
          { value: 'updates', label: t('updates') },
        ]}
      />
      {pane === 'updates' && <SathiUpdates />}
      {pane === 'chat' && <SathiChat />}
      {pane === 'add' && <SathiAdd />}
      {pane === 'doc' && <SathiDocument />}
    </Screen>
  );
}
