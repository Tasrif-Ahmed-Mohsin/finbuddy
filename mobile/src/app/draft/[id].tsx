import Ionicons from '@expo/vector-icons/Ionicons';
import { useLocalSearchParams } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { BuddyBubble, BuddyLoading } from '@/components/buddy';
import { ListenButton } from '@/components/listen-button';
import type { MascotMood } from '@/components/mascot';
import { BigNumber, GlowPulse, Kicker, Panel, SpaceText } from '@/components/neo';
import { ThemedText } from '@/components/themed-text';
import { CopCard } from '@/components/cop-card';
import { SwiftUetrCard } from '@/components/swift-uetr-card';
import { Badge, Banner, Button, Card, ErrorBox, H2, Muted, Row, Screen, styles } from '@/components/ui';
import { Colors, Space } from '@/constants/theme';
import type { Draft } from '@/lib/api';
import { bdt, cny, fill, num } from '@/lib/format';
import { KIND_LABEL, STATUS_TONE } from '@/lib/labels';
import { idempotencyKey, signWithPasskey } from '@/lib/passkey';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

const CHECK_ICON = { pass: '✓', warn: '!', block: '✕' } as const;

export default function DraftScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { t, lang, role, call } = useSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const { data: d, error: loadError, reload } = useLoad(useCallback(() => call<Draft>(`/drafts/${id}`), [call, id]));
  // One Idempotency-Key per tap on Send: if the answer is lost and the person taps again, the server returns the
  // first result instead of sending twice. A new key only after a definite answer.
  const sendKey = useRef<string | null>(null);

  async function approve() {
    if (!d) return;
    setBusy(true);
    setError(null);
    try {
      // The phone (or the browser's passkey) signs this exact draft's hash; the server checks the signature first.
      const assertion = await signWithPasskey(role, d.draft_hash, `${t('passkeyApprove')}: ${bdt(d.total_bdt, lang)} → ${d.payee_name}`, call);
      if (!assertion) return;
      await call(`/drafts/${d.id}/passkey-approve`, { method: 'POST', body: JSON.stringify(assertion) });
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    if (!d) return;
    setBusy(true);
    setError(null);
    try {
      await call(`/drafts/${d.id}/cancel`, { method: 'POST' });
      setDone(t('cancelledPayment'));
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function execute() {
    if (!d) return;
    setBusy(true);
    setError(null);
    try {
      sendKey.current = sendKey.current ?? idempotencyKey();
      await call(`/drafts/${d.id}/execute`, { method: 'POST', headers: { 'Idempotency-Key': sendKey.current } });
      sendKey.current = null;
      setDone(t('executed'));
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!d) {
    return (
      <Screen>
        {loadError ? <ErrorBox error={loadError} /> : <BuddyLoading text={t('chatThinking')} />}
      </Screen>
    );
  }

  const blockedReasons = d.checks.filter((c) => !c.passed && c.severity === 'block');
  const canApprove = d.required_approvers.includes(role) && !d.approved_by.includes(role) && (d.status === 'draft' || d.status === 'approved');
  const waitingFor = d.required_approvers.filter((r) => !d.approved_by.includes(r)).map((r) => t(r)).join(', ');
  const buddy: { mood: MascotMood; text: string } =
    d.status === 'executed'
      ? { mood: 'celebrate', text: t('draftSaySent') }
      : d.status === 'blocked'
        ? { mood: 'protect', text: t('draftSayBlocked') }
        : d.status === 'cancelled' || d.status === 'expired'
          ? { mood: 'sleep', text: t('draftSayClosed') }
          : d.status === 'approved' && !canApprove
            ? { mood: 'happy', text: t('draftSayApproved') }
            : canApprove
              ? { mood: 'idle', text: t('draftSayCheck') }
              : { mood: 'curious', text: fill(t('draftSayWaitingFmt'), { who: waitingFor }) };
  return (
    <Screen>
      {/* The payment as a boarding pass: from Bangladesh to China, the amount, what the family pays. */}
      <Panel style={local.pass}>
        <Row style={styles.between}>
          <Kicker dark>{t('passKicker')}</Kicker>
          <Badge tone={STATUS_TONE[d.status]}>{d.status}</Badge>
        </Row>
        <View style={local.route}>
          <View style={local.end}>
            <Kicker dark>{t('passFrom')}</Kicker>
            <ThemedText display style={local.code}>
              BD
            </ThemedText>
            <SpaceText muted small>
              {t(d.payer)}
            </SpaceText>
          </View>
          <View style={local.flight}>
            <View style={local.dash} />
            <Ionicons name="airplane" size={22} color={Space.neon} style={local.plane} />
          </View>
          <View style={[local.end, { alignItems: 'flex-end' }]}>
            <Kicker dark>{t('passTo')}</Kicker>
            <ThemedText display style={local.code}>
              CN
            </ThemedText>
            <SpaceText muted small style={{ textAlign: 'right' }}>
              {d.payee_name}
            </SpaceText>
          </View>
        </View>
        <View style={local.perf}>
          <View style={[local.notch, { left: -30 }]} />
          <View style={local.perfLine} />
          <View style={[local.notch, { right: -30 }]} />
        </View>
        <Row style={{ ...styles.between, alignItems: 'flex-end' }}>
          <View>
            <Kicker dark>{KIND_LABEL[d.kind]}</Kicker>
            <BigNumber value={Number(d.amount_cny)} size={44} color={Space.text} format={(n) => cny(Math.round(n), lang)} />
          </View>
          <View style={{ alignItems: 'flex-end' }}>
            <Kicker dark>{t('passTotal')}</Kicker>
            <ThemedText display style={local.total}>
              {bdt(d.total_bdt, lang)}
            </ThemedText>
          </View>
        </Row>
        {d.rate_bdt_per_cny && (
          <SpaceText muted small>
            {t('rate')}: ৳{num(d.rate_bdt_per_cny, lang)} / ¥1
          </SpaceText>
        )}
        {d.withdrawals.length > 0 && (
          <SpaceText muted small>
            ATM: {d.withdrawals.map((w) => cny(w, lang)).join(' + ')}
          </SpaceText>
        )}
        {d.memo ? (
          <SpaceText muted small>
            “{d.memo}”
          </SpaceText>
        ) : null}
      </Panel>
      <BuddyBubble mood={buddy.mood} text={buddy.text} size={84} />
      {d.status === 'blocked' && (
        <Banner tone="block">
          {t('blocked')}: {blockedReasons.map((c) => c.message).join(' · ')}
        </Banner>
      )}
      {done && <Banner tone="ok">{done}</Banner>}
      <ErrorBox error={error} />

      {d.summary && (
        <Card tone="info">
          <H2>{t('whatYouApprove')}</H2>
          <ThemedText>{d.summary[lang]}</ThemedText>
          <ListenButton text={d.summary[lang]} lang={lang} />
          <Muted>{t('readAloudHint')}</Muted>
        </Card>
      )}

      {d.cop_verification && <CopCard cop={d.cop_verification} />}

      <Card>
        <H2 icon="shield-checkmark">{t('checks')}</H2>
        {d.checks.map((c) => {
          const kind = c.passed ? (c.severity === 'warn' ? 'warn' : 'pass') : c.severity === 'block' ? 'block' : 'warn';
          const tone = kind === 'pass' ? 'ok' : kind;
          return (
            <Row key={c.id} style={{ alignItems: 'flex-start' }}>
              <Badge tone={tone}>{CHECK_ICON[kind]}</Badge>
              <ThemedText type="small" style={{ flex: 1 }}>
                {c.message}
              </ThemedText>
            </Row>
          );
        })}
      </Card>

      {d.passkey_approvals && d.passkey_approvals.length > 0 && (
        <Card tone="ok">
          <H2 icon="shield-checkmark">{t('passkeySignedBadge')}</H2>
          <ThemedText type="small" style={{ marginVertical: 4 }}>
            {t('passkeyVerifiedMsg')}
          </ThemedText>
          {d.passkey_approvals.map((pa) => (
            <Row key={pa.credential_id} style={{ ...styles.between, marginTop: 6 }}>
              <ThemedText type="smallBold">
                {t(pa.actor)}: {pa.label}
              </ThemedText>
              <Badge tone="ok" icon="finger-print">{pa.thumbprint}</Badge>
            </Row>
          ))}
        </Card>
      )}

      {d.uetr && (
        <SwiftUetrCard
          draftId={d.id}
          uetr={d.uetr}
        />
      )}

      <Card>
        <Row>
          <Muted>{t('needs')}:</Muted>
          {d.required_approvers.map((r) => (
            <Badge key={r} tone={d.approved_by.includes(r) ? 'ok' : 'neutral'}>
              {d.approved_by.includes(r) ? '✓ ' : ''}
              {t(r)}
            </Badge>
          ))}
        </Row>
        {canApprove && (
          <GlowPulse>
            <Button title={t('passkeyApprove')} icon="finger-print" onPress={approve} loading={busy} />
          </GlowPulse>
        )}
        {!canApprove && d.status === 'draft' && (
          <Banner tone="info">
            {t('waitingFor')}: {d.required_approvers.filter((r) => !d.approved_by.includes(r)).map((r) => t(r)).join(', ')}
          </Banner>
        )}
        {d.status === 'approved' && <Button title={t('execute')} icon="paper-plane" onPress={execute} loading={busy} />}
        {(d.status === 'draft' || d.status === 'approved') && (
          <Button title={t('cancelPayment')} variant="secondary" onPress={cancel} disabled={busy} />
        )}
      </Card>
    </Screen>
  );
}

const local = StyleSheet.create({
  pass: { gap: 14 },
  route: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  end: { gap: 2, minWidth: 80, maxWidth: '38%' },
  code: { fontSize: 40, lineHeight: 46, fontWeight: '600', color: Space.text, letterSpacing: 2 },
  flight: { flex: 1, height: 30, justifyContent: 'center', alignItems: 'center' },
  dash: { position: 'absolute', left: 0, right: 0, height: 0, borderTopWidth: 1.5, borderStyle: 'dashed', borderColor: 'rgba(77, 163, 255, 0.55)' },
  plane: { backgroundColor: Space.bg, paddingHorizontal: 6, textShadowColor: Space.neon, textShadowRadius: 8 },
  perf: { height: 20, justifyContent: 'center', marginHorizontal: 0 },
  perfLine: { height: 0, borderTopWidth: 1.5, borderStyle: 'dashed', borderColor: 'rgba(142, 154, 192, 0.45)' },
  notch: { position: 'absolute', top: -2, width: 24, height: 24, borderRadius: 12, backgroundColor: Colors.light.background },
  total: { fontSize: 22, lineHeight: 28, fontWeight: '600', color: Space.neon },
});
