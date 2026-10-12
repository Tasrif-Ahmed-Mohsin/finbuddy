import { useState } from 'react';

import { ThemedText } from '@/components/themed-text';
import { Badge, Button, Card, ErrorBox, H2, Muted, Row, styles } from '@/components/ui';
import type { Card as CardT } from '@/lib/api';
import { post } from '@/lib/api';
import { num, shortDate } from '@/lib/format';
import { confirmPresence } from '@/lib/presence';
import { useSession } from '@/lib/session';

const TONE = { active: 'ok', frozen: 'warn', lost: 'block' } as const;

/**
 * Card controls like a banking app. Asymmetric friction by design:
 * freezing (safer) is one tap; unfreezing or reporting lost needs fingerprint/PIN.
 */
export function CardControls({ card, onChange }: { card: CardT; onChange: () => void }) {
  const { t, lang, call } = useSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(op: 'freeze' | 'unfreeze' | 'report-lost') {
    if (op !== 'freeze') {
      const ok = await confirmPresence(op === 'unfreeze' ? t('unfreezeCard') : t('reportLost'));
      if (!ok) return;
    }
    setBusy(true);
    setError(null);
    try {
      await call(`/cards/${card.last4}/${op}`, post(op === 'freeze' ? { reason: 'frozen by user in the app' } : {}));
      onChange();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const label = card.status === 'active' ? t('cardActive') : card.status === 'frozen' ? t('cardFrozen') : t('cardLost');
  return (
    <Card tone={TONE[card.status]}>
      <Row style={styles.between}>
        <H2>
          {t('card')} ••••{num(card.last4, lang)}
        </H2>
        <Badge tone={TONE[card.status]}>{label}</Badge>
      </Row>
      <Muted>{card.label}</Muted>
      {card.changed_at && (
        <Muted>
          {shortDate(card.changed_at, lang)}
          {card.reason ? ` · ${card.reason}` : ''}
        </Muted>
      )}
      {card.status === 'active' && <Button title={`🔒 ${t('freezeCard')}`} variant="danger" onPress={() => run('freeze')} loading={busy} />}
      {card.status === 'frozen' && <Button title={t('unfreezeCard')} onPress={() => run('unfreeze')} loading={busy} />}
      {card.status !== 'lost' && <Button title={t('reportLost')} variant="secondary" onPress={() => run('report-lost')} loading={busy} />}
      {card.status === 'lost' && card.replacement_last4 && (
        <ThemedText type="small">
          {t('replacementOrdered')} ••••{num(card.replacement_last4, lang)}
        </ThemedText>
      )}
      <ErrorBox error={error} />
    </Card>
  );
}
