import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { useCallback, useState, type ComponentProps } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { AnchorCard } from '@/components/anchor-card';
import { CopCard } from '@/components/cop-card';
import { FirewallCard } from '@/components/firewall-card';
import { LedgerCard } from '@/components/ledger-card';
import { BigNumber, Kicker, Panel, Seal, SectionHeader, SpaceText } from '@/components/neo';
import { SafetyFuzzingCard } from '@/components/safety-fuzzing-card';
import { SwiftUetrCard } from '@/components/swift-uetr-card';
import { TaintCard } from '@/components/taint-card';
import { ThemedText } from '@/components/themed-text';
import { Badge, Button, Card, ErrorBox, Muted, Row, styles as ui } from '@/components/ui';
import { Brand, Elevation, Space, Tone } from '@/constants/theme';
import type { AuditEntry, FirewallTelemetry, FuzzReport, Receipt, TaintStatus } from '@/lib/api';
import { bdt, cny, fill, num, shortDate } from '@/lib/format';
import type { Lang, StringKey } from '@/lib/i18n';
import { KIND_LABEL } from '@/lib/labels';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

type IconName = ComponentProps<typeof Ionicons>['name'];
type ShieldId = 'passkeys' | 'twoperson' | 'taint' | 'firewall' | 'cop' | 'fuzz';
const SHIELDS: { id: ShieldId; icon: IconName }[] = [
  { id: 'passkeys', icon: 'finger-print' },
  { id: 'twoperson', icon: 'people' },
  { id: 'taint', icon: 'git-branch' },
  { id: 'firewall', icon: 'eye-off' },
  { id: 'cop', icon: 'person-circle' },
  { id: 'fuzz', icon: 'bug' },
];

/**
 * Proof, the trust center, in three parts:
 * - Your money: every payment's receipt, the double-entry books, the payment passport.
 * - Safety: six shields, each enforced by the server (not the AI); one tap opens its evidence.
 * - Black box: the hash-chained log, in plain sentences.
 */
export function ProofPanel() {
  const { t, lang, call } = useSession();
  const [allLog, setAllLog] = useState(false);
  const [allReceipts, setAllReceipts] = useState(false);
  const [open, setOpen] = useState<ShieldId | null>(null);
  const { data, error } = useLoad(
    useCallback(async () => {
      const [receipts, audit, fuzz, taint, firewall, keys] = await Promise.all([
        call<Receipt[]>('/receipts'),
        call<{ verify: { valid: boolean; entries: number }; entries: AuditEntry[] }>('/audit?limit=60'),
        call<FuzzReport>('/security/fuzz-results').catch(() => null),
        call<TaintStatus>('/security/taint/status').catch(() => null),
        call<FirewallTelemetry>('/security/firewall/status').catch(() => null),
        call<{ credentials: unknown[] }>('/auth/passkey/credentials').catch(() => ({ credentials: [] })),
      ]);
      return { receipts, audit, fuzz, taint, firewall, keys: keys.credentials.length };
    }, [call]),
  );

  const status = (id: ShieldId): string => {
    if (!data) return '';
    switch (id) {
      case 'passkeys':
        return fill(t('shield_passkeys_sub'), { n: num(data.keys, lang) });
      case 'twoperson':
        return t('shield_twoperson_sub');
      case 'taint':
        return fill(t('shield_taint_sub'), { n: num(data.taint?.total_injections_blocked ?? 0, lang) });
      case 'firewall':
        return fill(t('shield_firewall_sub'), { n: num(data.firewall?.total_inspections ?? 0, lang) });
      case 'cop':
        return t('shield_cop_sub');
      case 'fuzz':
        return data.fuzz
          ? fill(t('shield_fuzz_sub'), { n: num(data.fuzz.total_attacks.toLocaleString('en-US'), lang), v: num(data.fuzz.violations_detected, lang) })
          : '—';
    }
  };

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
          <Row style={{ gap: 10 }}>
            <Button title={t('storyOpen')} icon="play" onPress={() => router.push('/story')} />
            <Button title={t('judgeTitle')} variant="secondary" icon="checkmark-done" onPress={() => router.push('/judge')} />
          </Row>

          {/* 1. Your money */}
          <SectionHeader kicker={t('trustMoneyKicker')} title={t('trustMoney')} />
          {data.receipts.length === 0 && <Muted>{t('noPayments')}</Muted>}
          {(allReceipts ? data.receipts : data.receipts.slice(0, 3)).map((r) => (
            <ReceiptCard key={r.draft.id} r={r} />
          ))}
          {data.receipts.length > 3 && (
            <Button
              title={allReceipts ? t('showLess') : fill(t('showAllReceipts'), { n: num(data.receipts.length, lang) })}
              variant="secondary"
              onPress={() => setAllReceipts(!allReceipts)}
            />
          )}
          <LedgerCard />
          <Card tone="info">
            <Row style={{ flexWrap: 'nowrap', gap: 12 }}>
              <View style={local.iconBox}>
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

          {/* 2. Safety: six shields */}
          <SectionHeader kicker={t('trustSafetyKicker')} title={t('trustSafety')} />
          <Muted>{t('trustSafetyIntro')}</Muted>
          <View style={local.grid}>
            {SHIELDS.map((s) => {
              const on = open === s.id;
              return (
                <Pressable
                  key={s.id}
                  accessibilityRole="button"
                  accessibilityState={{ expanded: on }}
                  onPress={() => setOpen(on ? null : s.id)}
                  style={({ pressed }) => [local.shield, on && local.shieldOn, pressed && { transform: [{ scale: 0.98 }] }]}>
                  <View style={[local.shieldIcon, on && { backgroundColor: Brand.primary }]}>
                    <Ionicons name={s.icon} size={20} color={on ? '#FFFFFF' : Space.neon} />
                  </View>
                  <ThemedText type="smallBold" numberOfLines={2}>
                    {t(`shield_${s.id}` as StringKey)}
                  </ThemedText>
                  <Muted style={{ fontSize: 12, lineHeight: 16 }}>{status(s.id)}</Muted>
                </Pressable>
              );
            })}
          </View>
          {open === 'passkeys' && <ExplainCard icon="finger-print" title={t('shield_passkeys')} text={t('shield_passkeys_detail')} />}
          {open === 'twoperson' && <ExplainCard icon="people" title={t('shield_twoperson')} text={t('shield_twoperson_detail')} />}
          {open === 'cop' && <ExplainCard icon="person-circle" title={t('shield_cop')} text={t('shield_cop_detail')} />}
          {open === 'taint' && <TaintCard />}
          {open === 'firewall' && <FirewallCard />}
          {open === 'fuzz' && <SafetyFuzzingCard />}

          {/* 3. Black box */}
          <SectionHeader kicker={t('proofChainKicker')} title={t('auditLog')} />
          <AnchorCard />
          <View>
            {(allLog ? data.audit.entries : data.audit.entries.slice(0, 10)).map((e, i, list) => (
              <ChainBlock key={e.seq} e={e} last={i === list.length - 1} />
            ))}
          </View>
          {data.audit.entries.length > 10 && (
            <Button title={allLog ? t('showLess') : t('showAll')} variant="secondary" onPress={() => setAllLog(!allLog)} />
          )}
        </>
      )}
    </>
  );
}

function ExplainCard({ icon, title, text }: { icon: IconName; title: string; text: string }) {
  return (
    <Card tone="info">
      <Row style={{ flexWrap: 'nowrap', gap: 10, alignItems: 'flex-start' }}>
        <Ionicons name={icon} size={22} color={Brand.primary} />
        <View style={{ flex: 1, gap: 4 }}>
          <ThemedText type="smallBold">{title}</ThemedText>
          <Muted>{text}</Muted>
        </View>
      </Row>
    </Card>
  );
}

/** One log entry, said plainly: the key facts (amount, payment, payee, reason); the hash links it to the one before. */
function logLine(e: AuditEntry, lang: Lang): string {
  const d = (e.data ?? {}) as Record<string, unknown>;
  const parts: string[] = [];
  if (typeof d.amount_cny === 'string' || typeof d.amount_cny === 'number') parts.push(cny(String(d.amount_cny), lang));
  if (typeof d.debited_bdt === 'string') parts.push(bdt(d.debited_bdt, lang));
  if (typeof d.draft_id === 'string') parts.push(d.draft_id);
  if (typeof d.payee === 'string') parts.push(d.payee.replace(/_/g, ' '));
  if (typeof d.connector === 'string') parts.push(d.connector);
  if (typeof d.uetr === 'string') parts.push(`UETR ${d.uetr.slice(0, 8)}…`);
  if (typeof d.reason === 'string') parts.push(d.reason.slice(0, 70));
  return parts.join(' · ');
}

const KNOWN_LEVELS = ['READ', 'DRAFT', 'EXECUTE', 'MANDATE', 'SYSTEM', 'SANDBOX'];
const KNOWN_ACTORS = ['parent', 'student', 'agent', 'system'];

function ChainBlock({ e, last }: { e: AuditEntry; last: boolean }) {
  const { t, lang } = useSession();
  const bad = e.event.includes('denied') || e.event.includes('blocked') || e.event.includes('failed');
  const line = logLine(e, lang);
  const level = KNOWN_LEVELS.includes(e.permission_level) ? t(`level_${e.permission_level}` as StringKey) : e.permission_level;
  const who = KNOWN_ACTORS.includes(e.actor) ? t(`actor_${e.actor}` as StringKey) : e.actor;
  return (
    <View style={local.chainRow}>
      <View style={local.rail}>
        <View style={[local.node, bad && { backgroundColor: Tone.block.neon, boxShadow: `0px 0px 8px ${Tone.block.neon}` }]} />
        {!last && <View style={local.link} />}
      </View>
      <Card style={local.block}>
        <Row style={ui.between}>
          <ThemedText type="smallBold" style={{ flex: 1 }}>
            #{num(e.seq, lang)} {e.event.replace(/_/g, ' ')}
          </ThemedText>
          <Badge tone={bad ? 'block' : e.permission_level === 'MANDATE' ? 'ok' : 'neutral'}>{level}</Badge>
        </Row>
        {line ? <ThemedText type="small">{line}</ThemedText> : null}
        <Muted>
          {who} · {shortDate(e.sim_time ?? e.ts, lang)} · {e.hash.slice(0, 10)}…
        </Muted>
      </Card>
    </View>
  );
}

/** A receipt as a ticket stub: what was paid, to whom, who or what allowed it, and the bank's tracking number. */
function ReceiptCard({ r }: { r: Receipt }) {
  const { t, lang } = useSession();
  const [bank, setBank] = useState(false);
  const a = r.authority;
  const byMandate = a?.type === 'mandate';
  const uetr = r.uetr || r.iso20022?.uetr;
  const who =
    a?.type === 'mandate'
      ? `${t('underMandate')} (${a.signed_by.map((s) => t(s)).join(' + ')})`
      : a?.type === 'approvals'
        ? `${t('approvedByPeople')}: ${a.approved_by.map((s) => t(s)).join(' + ')}${a.passkey_signed ? ` · ${t('passkeySignedBadge')}` : ''}`
        : '';
  return (
    <Card tone={byMandate ? 'ok' : 'info'}>
      <Pressable onPress={() => router.push({ pathname: '/draft/[id]', params: { id: r.draft.id } })}>
        <Row style={{ ...ui.between, flexWrap: 'nowrap' }}>
          <Row style={{ flexWrap: 'nowrap', flex: 1 }}>
            <Ionicons name={byMandate ? 'sync' : 'finger-print'} size={18} color={Brand.primary} />
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
        {who ? <Muted>{who}</Muted> : null}
        <Row style={{ marginTop: 4 }}>
          {r.draft.checks.length > 0 && (
            <Badge tone="neutral" icon="checkmark">
              {num(r.draft.checks.filter((c) => c.passed).length, lang)}/{num(r.draft.checks.length, lang)} {t('checks')}
            </Badge>
          )}
          {r.sent && (
            <Badge tone="neutral">
              {t('logEntry')} #{num(r.sent.seq, lang)}
            </Badge>
          )}
          {r.draft.cop_verification && <CopCard cop={r.draft.cop_verification} compact />}
        </Row>
      </Pressable>
      {uetr && (
        <Pressable accessibilityRole="button" accessibilityState={{ expanded: bank }} onPress={() => setBank(!bank)} style={local.bankRow}>
          <Ionicons name="navigate-circle" size={18} color={Brand.primary} />
          <ThemedText type="small" style={{ flex: 1 }} numberOfLines={1}>
            {t('swiftGpiTracking')}: {uetr.slice(0, 13)}…
          </ThemedText>
          <Ionicons name={bank ? 'chevron-up' : 'chevron-down'} size={16} color={Brand.primary} />
        </Pressable>
      )}
      {uetr && bank && (
        <View style={{ marginTop: 8 }}>
          <SwiftUetrCard
            draftId={r.draft.id}
            uetr={uetr}
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
  iconBox: { width: 44, height: 44, borderRadius: 14, backgroundColor: Space.bg, alignItems: 'center', justifyContent: 'center', boxShadow: '0px 0px 12px rgba(77, 163, 255, 0.35)' },
  cardTitle: { fontSize: 17, lineHeight: 22, fontWeight: '700' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  shield: { flexBasis: '30%', flexGrow: 1, minWidth: 140, gap: 6, padding: 12, borderRadius: 20, backgroundColor: '#EEF0F4', boxShadow: Elevation[1] },
  shieldOn: { boxShadow: Elevation.inset },
  shieldIcon: { width: 36, height: 36, borderRadius: 12, backgroundColor: Space.bg, alignItems: 'center', justifyContent: 'center' },
  chainRow: { flexDirection: 'row', gap: 10 },
  rail: { width: 16, alignItems: 'center' },
  node: { width: 12, height: 12, borderRadius: 6, marginTop: 22, backgroundColor: Space.neon, boxShadow: `0px 0px 8px ${Space.neon}` },
  link: { flex: 1, width: 2, marginVertical: 2, backgroundColor: 'rgba(77, 163, 255, 0.45)' },
  block: { flex: 1, marginBottom: 12 },
  amount: { fontSize: 20, lineHeight: 24, fontWeight: '600' },
  bankRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 8, paddingVertical: 4 },
  perforation: { height: 0, borderTopWidth: 1.5, borderStyle: 'dashed', borderColor: '#C9CED8', marginVertical: 2 },
});
