import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { useCallback, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { BigNumber, Kicker, Panel, Seal, SectionHeader, SpaceText } from '@/components/neo';
import { SafetyFuzzingCard } from '@/components/safety-fuzzing-card';
import { SwiftUetrCard } from '@/components/swift-uetr-card';
import { TaintCard } from '@/components/taint-card';
import { FirewallCard } from '@/components/firewall-card';
import { CopCard } from '@/components/cop-card';
import { LedgerCard } from '@/components/ledger-card';
import { ThemedText } from '@/components/themed-text';
import { Badge, Button, Card, ErrorBox, Muted, Row, styles as ui } from '@/components/ui';
import { Space } from '@/constants/theme';
import type { AuditEntry, Receipt } from '@/lib/api';
import { bdt, cny, num, shortDate } from '@/lib/format';
import { KIND_LABEL } from '@/lib/labels';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

/** Prove: the black box. A seal for the hash-chained log, a receipt for every payment, the payment passport. */
export function ProofPanel() {
  const { t, lang, call } = useSession();
  const [allLog, setAllLog] = useState(false);
  const { data, error } = useLoad(
    useCallback(async () => {
      const [receipts, audit] = await Promise.all([
        call<Receipt[]>('/receipts'),
        call<{ verify: { valid: boolean; entries: number }; entries: AuditEntry[] }>('/audit?limit=60'),
      ]);
      return { receipts, audit };
    }, [call]),
  );

  return (
    <>
      <ErrorBox error={error} />
      {data && (
        <>
          <Panel>
            <Kicker dark>{t('proofKicker')}</Kicker>
            <Row style={{ flexWrap: 'nowrap', gap: 16 }}>
              <Seal ok={data.audit.verify.valid} size={76} />
              <View style={{ flex: 1, gap: 2 }}>
                <SpaceText neon={data.audit.verify.valid} style={local.sealTitle}>
                  {data.audit.verify.valid ? t('chainValid') : t('chainBroken')}
                </SpaceText>
                <Row style={{ gap: 6, alignItems: 'baseline' }}>
                  <BigNumber value={data.audit.verify.entries} size={34} color={Space.text} format={(n) => num(Math.round(n), lang)} />
                  <SpaceText muted small>
                    {t('proofEntries')}
                  </SpaceText>
                </Row>
              </View>
            </Row>
            <SpaceText muted small>
              {t('proofIntro')}
            </SpaceText>
          </Panel>

          <Button title={t('judgeTitle')} variant="secondary" icon="play-circle-outline" onPress={() => router.push('/judge')} />

          <LedgerCard />

          <SafetyFuzzingCard />

          <TaintCard />

          <FirewallCard />

          <SectionHeader kicker={t('proofReceiptsKicker')} title={t('receiptsTitle')} />
          {data.receipts.length === 0 && <Muted>{t('noPayments')}</Muted>}
          {data.receipts.map((r) => (
            <ReceiptCard key={r.draft.id} r={r} />
          ))}

          <Card tone="info">
            <Row style={{ flexWrap: 'nowrap', gap: 12 }}>
              <View style={local.passIcon}>
                <Ionicons name="id-card" size={22} color={Space.neon} />
              </View>
              <View style={{ flex: 1, gap: 2 }}>
                <ThemedText display style={local.cardTitle}>
                  {t('buildCredit')}
                </ThemedText>
                <Muted>{t('passportIntro')}</Muted>
              </View>
            </Row>
            <Button title={t('passport')} variant="secondary" icon="qr-code-outline" onPress={() => router.push('/passport')} />
          </Card>

          <SectionHeader kicker={t('proofChainKicker')} title={t('auditLog')} />
          <View>
            {(allLog ? data.audit.entries : data.audit.entries.slice(0, 12)).map((e, i, list) => (
              <ChainBlock key={e.seq} e={e} last={i === list.length - 1} />
            ))}
          </View>
          {data.audit.entries.length > 12 && (
            <Button title={allLog ? t('showLess') : t('showAll')} variant="secondary" onPress={() => setAllLog(!allLog)} />
          )}
        </>
      )}
    </>
  );
}

/** One log entry as a block on the chain: a neon rail on the left links it to the one before. */
function ChainBlock({ e, last }: { e: AuditEntry; last: boolean }) {
  const { lang } = useSession();
  const bad = e.event.includes('denied') || e.event.includes('blocked');
  return (
    <View style={local.chainRow}>
      <View style={local.rail}>
        <View style={[local.node, bad && { backgroundColor: '#FF5C5C', boxShadow: '0px 0px 8px #FF5C5C' }]} />
        {!last && <View style={local.link} />}
      </View>
      <Card style={local.block}>
        <Row style={ui.between}>
          <ThemedText type="smallBold" style={{ flex: 1 }}>
            #{num(e.seq, lang)} {e.event.replace(/_/g, ' ')}
          </ThemedText>
          <Badge tone={bad ? 'block' : e.permission_level === 'MANDATE' ? 'ok' : 'neutral'}>{e.permission_level}</Badge>
        </Row>
        <Muted>
          {e.actor} · {shortDate(e.sim_time ?? e.ts, lang)} · {e.hash.slice(0, 10)}…
        </Muted>
        <ThemedText type="code" numberOfLines={2}>
          {JSON.stringify(e.data)}
        </ThemedText>
      </Card>
    </View>
  );
}

/** A receipt as a ticket stub: what was paid, to whom, and who or what allowed it. */
function ReceiptCard({ r }: { r: Receipt }) {
  const { t, lang } = useSession();
  const a = r.authority;
  const byMandate = a?.type === 'mandate';
  const hasUetr = Boolean(r.uetr || r.iso20022?.uetr);

  return (
    <Card tone={byMandate ? 'ok' : 'info'}>
      <Pressable onPress={() => router.push({ pathname: '/draft/[id]', params: { id: r.draft.id } })}>
        <Row style={{ ...ui.between, flexWrap: 'nowrap' }}>
          <Row style={{ flexWrap: 'nowrap', flex: 1 }}>
            <Ionicons name={byMandate ? 'sync' : 'finger-print'} size={18} color="#007AFF" />
            <ThemedText type="smallBold" style={{ flex: 1 }}>
              {KIND_LABEL[r.draft.kind]} → {r.draft.payee_name}
            </ThemedText>
          </Row>
          <ThemedText display style={local.amount}>
            {cny(r.draft.amount_cny, lang)}
          </ThemedText>
        </Row>
        <View style={local.perforation} />
        <Muted>
          {bdt(r.draft.total_bdt, lang)} · {r.sent ? shortDate(r.sent.sim_time, lang) : ''}
          {r.landed ? ` · ${t('landedOn')} ${shortDate(r.landed.sim_time, lang)}` : r.sent?.arrives_at ? ` · ${t('arrivesOn')} ${shortDate(r.sent.arrives_at, lang)}` : ''}
        </Muted>
        {a?.type === 'mandate' && (
          <Muted>
            {t('underMandate')} ({a.signed_by.map((s) => t(s)).join(' + ')}) · #{a.proposal_hash?.slice(0, 10)}
          </Muted>
        )}
        {a?.type === 'approvals' && (
          <Muted>
            {t('approvedByPeople')}: {a.approved_by.map((s) => t(s)).join(' + ')}
          </Muted>
        )}
        <Row style={{ marginTop: 4 }}>
          <Badge tone="ok">{a?.level ?? '–'}</Badge>
          {r.draft.checks.filter((c) => c.passed).length > 0 && (
            <Badge tone="neutral" icon="checkmark">
              {num(r.draft.checks.filter((c) => c.passed).length, lang)}/{num(r.draft.checks.length, lang)} {t('checks')}
            </Badge>
          )}
          {r.sent && (
            <Badge tone="neutral">
              {t('logEntry')} #{num(r.sent.seq, lang)}
            </Badge>
          )}
          {r.draft.cop_verification && (
            <CopCard cop={r.draft.cop_verification} compact />
          )}
        </Row>
      </Pressable>

      {hasUetr && (
        <View style={{ marginTop: 8 }}>
          <SwiftUetrCard
            draftId={r.draft.id}
            uetr={r.uetr || r.iso20022?.uetr}
            originBic={r.iso20022?.origin_bic}
            originBankName={r.iso20022?.origin_bank_name}
            destBic={r.iso20022?.dest_bic}
            destBankName={r.iso20022?.dest_bank_name}
            regulatoryReporting={r.iso20022?.regulatory_reporting}
          />
        </View>
      )}
    </Card>
  );
}

const local = StyleSheet.create({
  sealTitle: { fontSize: 17, lineHeight: 22, fontWeight: '600' },
  passIcon: { width: 44, height: 44, borderRadius: 14, backgroundColor: Space.bg, alignItems: 'center', justifyContent: 'center', boxShadow: '0px 0px 12px rgba(77, 163, 255, 0.35)' },
  cardTitle: { fontSize: 17, lineHeight: 22, fontWeight: '700' },
  chainRow: { flexDirection: 'row', gap: 10 },
  rail: { width: 16, alignItems: 'center' },
  node: { width: 12, height: 12, borderRadius: 6, marginTop: 22, backgroundColor: Space.neon, boxShadow: `0px 0px 8px ${Space.neon}` },
  link: { flex: 1, width: 2, marginVertical: 2, backgroundColor: 'rgba(77, 163, 255, 0.45)' },
  block: { flex: 1, marginBottom: 12 },
  amount: { fontSize: 20, lineHeight: 24, fontWeight: '600' },
  perforation: { height: 0, borderTopWidth: 1.5, borderStyle: 'dashed', borderColor: '#C9CED8', marginVertical: 2 },
});
