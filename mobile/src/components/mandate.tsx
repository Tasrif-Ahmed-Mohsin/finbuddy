import { useState } from 'react';

import { ListenButton } from '@/components/listen-button';
import { ThemedText } from '@/components/themed-text';
import { Badge, Banner, Button, Card, ErrorBox, Field, H2, Meter, Muted, Row } from '@/components/ui';
import { post, type MandateView, type Proposal } from '@/lib/api';
import { bdt, cny, num, shortDate } from '@/lib/format';
import { signWithPasskey } from '@/lib/passkey';
import { VoiceButton } from '@/components/voice-button';
import { useSession } from '@/lib/session';

/** Act, step 1: the parent says in their own words what Bluefin may do. Bluefin turns it into a strict proposal. */
export function MandateComposer({ onProposal }: { onProposal: (p: Proposal) => void }) {
  const { t, lang, call } = useSession();
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function write() {
    setBusy(true);
    setError(null);
    try {
      onProposal(await call<Proposal>('/mandates/proposals', post({ text, lang })));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Card>
      <H2>{t('setUpMandate')}</H2>
      <Muted>{t('mandateIntro')}</Muted>
      <Field label={t('yourInstruction')} value={text} onChangeText={setText} placeholder={t('mandateExample')} multiline />
      <Row>
        <Button title={t('useExample')} variant="secondary" onPress={() => setText(t('mandateExample'))} />
        {/* Older parents can say it instead of typing it, in Bangla */}
        <VoiceButton onText={setText} onError={setError} />
      </Row>
      <Button title={t('writeMandate')} onPress={write} loading={busy} disabled={text.trim().length < 3} />
      <ErrorBox error={error} />
    </Card>
  );
}

/** Act, step 2: read (or hear) exactly what will be signed, then sign with fingerprint. Large caps need both signatures. */
export function ProposalCard({ proposal: p, onSigned }: { proposal: Proposal; onSigned: (p: Proposal) => void }) {
  const { t, lang, role, call } = useSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const summary = p.summary[lang];
  const canSign = p.status === 'proposed' && p.missing_signers.includes(role);

  async function sign() {
    setBusy(true);
    setError(null);
    try {
      // The passkey signs this proposal's hash, and the server checks that hash is the proposal it holds now:
      // what you read is what you sign.
      const assertion = await signWithPasskey(role, p.hash, t('signMandate'), call);
      if (!assertion) return;
      onSigned(await call<Proposal>(`/mandates/proposals/${p.id}/sign`, post({ proposal_hash: p.hash, assertion })));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card tone={p.errors.length ? 'block' : p.status === 'active' ? 'ok' : 'warn'}>
      <H2>{p.errors.length ? t('fixFirst') : t('readBack')}</H2>
      {p.text ? <Muted>“{p.text}”</Muted> : null}
      {p.errors.map((e) => (
        <Banner key={e} tone="block">
          {e}
        </Banner>
      ))}
      {!p.errors.length && (
        <>
          <ThemedText>{summary}</ThemedText>
          <ListenButton text={summary} lang={lang} />
          {p.notes.map((n) => (
            <Banner key={n} tone="warn">
              {n}
            </Banner>
          ))}
          <Row>
            {p.required_signers.map((s) => (
              <Badge key={s} tone={p.signatures[s] ? 'ok' : 'neutral'}>
                {p.signatures[s] ? `✓ ${t('signedBy')} ` : `${t('waitingSignature')} `}
                {t(s)}
              </Badge>
            ))}
          </Row>
          {canSign && <Button title={`✍️ ${t('signWithFingerprint')}`} onPress={sign} loading={busy} />}
          {p.autopilot?.map((a, i) =>
            a.type === 'autopilot_sent' && a.amount_cny ? (
              <Banner key={i} tone="ok">
                {t('autopilotActed')} {cny(a.amount_cny, lang)} {t('sentAmount')}
              </Banner>
            ) : null,
          )}
        </>
      )}
      <ErrorBox error={error} />
    </Card>
  );
}

/** The mandate in force: how much of this month's limit is used, who signed, and a one-tap cancel (safer is easy). */
export function ActiveMandateCard({ m, onChanged }: { m: MandateView; onChanged: () => void }) {
  const { t, lang, call } = useSession();
  const [error, setError] = useState<string | null>(null);
  const summary = m.summary?.[lang] ?? '';

  async function cancel() {
    setError(null);
    try {
      await call(`/mandates/${m.id}`, { method: 'DELETE' });
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }
  return (
    <Card tone="ok">
      <H2 icon="sync">{t('mandateActive')}</H2>
      {summary ? <ThemedText type="small">{summary}</ThemedText> : null}
      {summary ? <ListenButton text={summary} lang={lang} /> : null}
      <Meter
        label={t('usedThisMonth')}
        used={Number(m.spent_in_period_bdt)}
        cap={Number(m.max_bdt_per_period)}
        display={`${bdt(m.spent_in_period_bdt, lang)} / ${bdt(m.max_bdt_per_period, lang)}`}
      />
      <Muted>
        {t('autopilotPayments')}: {num(m.payments, lang)} · {t('validUntilLabel')} {shortDate(m.expires_at, lang)}
      </Muted>
      <Row>
        {m.signed_by.map((s) => (
          <Badge key={s} tone="ok">
            ✓ {t(s)}
          </Badge>
        ))}
      </Row>
      <Button title={t('cancelMandate')} variant="danger" onPress={cancel} />
      <ErrorBox error={error} />
    </Card>
  );
}
