import Ionicons from '@expo/vector-icons/Ionicons';
import { useCallback, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { BigNumber, Kicker, Panel, SpaceText } from '@/components/neo';
import { ThemedText } from '@/components/themed-text';
import { Button, Card, Muted, Row } from '@/components/ui';
import { Space, Tone } from '@/constants/theme';
import type { LedgerView } from '@/lib/api';
import { num, shortDate } from '@/lib/format';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

/** Prove: the sandbox bank's double-entry books. Balanced in each currency, every account reconciled, every payment
 * booked once (retries with the same Idempotency-Key are answered, not paid again). */
export function LedgerCard() {
  const { t, lang, call } = useSession();
  const [open, setOpen] = useState(false);
  const { data } = useLoad(useCallback(() => call<LedgerView>('/ledger?limit=12'), [call]));
  if (!data) return null;
  const b = data.books;
  return (
    <Panel tone={b.ok ? 'blue' : 'red'}>
      <Kicker dark>{t('ledgerKicker')}</Kicker>
      <Row style={{ flexWrap: 'nowrap', gap: 12 }}>
        <View style={[local.icon, !b.ok && { boxShadow: `0px 0px 14px ${Tone.block.neon}` }]}>
          <Ionicons name={b.ok ? 'git-compare' : 'warning'} size={24} color={b.ok ? Space.neon : Tone.block.neon} />
        </View>
        <View style={{ flex: 1, gap: 2 }}>
          <SpaceText neon={b.ok} style={local.title}>
            {b.ok ? t('ledgerOk') : t('ledgerBroken')}
          </SpaceText>
          <SpaceText muted small>
            {Object.entries(b.trial_balance)
              .map(([cur, v]) => `${cur} ${t('ledgerDiff')} ${num(Number(v), lang)}`)
              .join(' · ')}
          </SpaceText>
        </View>
      </Row>
      <Row style={{ gap: 18 }}>
        <Stat value={b.entries} label={t('ledgerEntries')} />
        <Stat value={data.payments_booked} label={t('ledgerPayments')} />
        <Stat value={data.idempotent_replays} label={t('ledgerReplays')} />
      </Row>
      <SpaceText muted small>
        {b.reconciled ? `✓ ${t('ledgerReconciled')}. ` : ''}
        {t('ledgerIntro')}
      </SpaceText>
      <Button title={open ? t('fuzzHideDetails') : t('ledgerShowEntries')} variant="secondary" icon="list" onPress={() => setOpen(!open)} />
      {open &&
        data.entries.map((e) => (
          <Card key={e.id} style={{ gap: 4 }}>
            <Row style={{ justifyContent: 'space-between' }}>
              <ThemedText type="smallBold">
                {e.id} · {e.event.replace(/_/g, ' ')}
              </ThemedText>
              <Muted>{shortDate(e.at, lang)}</Muted>
            </Row>
            {e.postings.map((p, i) => (
              <Row key={i} style={{ justifyContent: 'space-between', flexWrap: 'nowrap' }}>
                <ThemedText type="code" style={{ flex: 1 }} numberOfLines={1}>
                  {p.account}
                </ThemedText>
                <ThemedText type="code" style={{ color: Number(p.amount) < 0 ? '#C0392B' : '#1E8449' }}>
                  {Number(p.amount) > 0 ? '+' : ''}
                  {p.amount} {p.currency}
                </ThemedText>
              </Row>
            ))}
          </Card>
        ))}
    </Panel>
  );
}

function Stat({ value, label }: { value: number; label: string }) {
  const { lang } = useSession();
  return (
    <View style={{ gap: 0, minWidth: 80, flexShrink: 1 }}>
      <BigNumber value={value} size={28} color={Space.text} format={(n) => num(Math.round(n), lang)} />
      <SpaceText muted small>
        {label}
      </SpaceText>
    </View>
  );
}

const local = StyleSheet.create({
  icon: { width: 48, height: 48, borderRadius: 16, backgroundColor: Space.bg2, alignItems: 'center', justifyContent: 'center', boxShadow: '0px 0px 12px rgba(77, 163, 255, 0.35)' },
  title: { fontSize: 17, lineHeight: 22, fontWeight: '600' },
});
