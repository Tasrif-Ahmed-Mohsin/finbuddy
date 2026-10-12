import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';

import { ThemedText } from '@/components/themed-text';
import { Badge, Banner, Button, Card, ErrorBox, H1, H2, Meter, Muted, Row, Screen, Segmented, Field, styles } from '@/components/ui';
import { post, type Draft, type LivingPlan, type Timeline, type TuitionPlan } from '@/lib/api';
import { bdt, cny, num, shortDate } from '@/lib/format';
import { useSession } from '@/lib/session';

type Mode = 'tuition' | 'living';

export default function PlanScreen() {
  const params = useLocalSearchParams<{ mode?: string }>();
  const initial: Mode = params.mode === 'living' ? 'living' : 'tuition';
  // Re-mount when the Home screen links here with a different mode.
  return <PlanBody key={initial} initial={initial} />;
}

function PlanBody({ initial }: { initial: Mode }) {
  const { t } = useSession();
  const [mode, setMode] = useState<Mode>(initial);

  return (
    <Screen>
      <H1>{t('tabPlan')}</H1>
      <Segmented<Mode>
        value={mode}
        onChange={setMode}
        options={[
          { value: 'tuition', label: t('tuitionTab') },
          { value: 'living', label: t('livingTab') },
        ]}
      />
      {mode === 'tuition' ? <TuitionPlanner /> : <LivingPlanner />}
    </Screen>
  );
}

const STATUS_TONE = { on_track: 'ok', urgent: 'warn', urgent_no_buffer: 'warn', at_risk_late: 'block' } as const;

function TuitionPlanner() {
  const { t, lang, call } = useSession();
  const [amount, setAmount] = useState('35200');
  const [deadline, setDeadline] = useState('2026-11-15');
  const [plan, setPlan] = useState<TuitionPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    // Prefill from the timeline (the fee notice on file).
    call<Timeline>('/timeline')
      .then((tl) => {
        const item = tl.items.find((i) => i.type === 'tuition_due');
        if (item?.amount_cny) setAmount(String(Math.round(Number(item.amount_cny))));
        if (item?.due) setDeadline(item.due);
      })
      .catch(() => {});
  }, [call]);

  async function compare() {
    setBusy(true);
    setError(null);
    try {
      setPlan(await call<TuitionPlan>('/plan/tuition', post({ amount_cny: amount, deadline })));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function prepare(quoteId: string) {
    setBusy(true);
    setError(null);
    try {
      const d = await call<Draft>(
        '/drafts',
        post({ kind: 'tt_tuition', amount_cny: amount, payee_id: 'univ_demo', quote_id: quoteId, memo: `Tuition ${amount} CNY` }),
      );
      router.push({ pathname: '/draft/[id]', params: { id: d.id } });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const best = plan?.options.find((o) => o.quote_id === plan.best_quote_id);
  return (
    <>
      <Card>
        <Field label={t('amountCny')} value={amount} onChangeText={setAmount} keyboardType="numeric" />
        <Field label={t('deadline')} value={deadline} onChangeText={setDeadline} autoCapitalize="none" />
        <Button title={t('compareBanks')} onPress={compare} loading={busy} />
      </Card>
      <ErrorBox error={error} />
      {plan && (
        <>
          {plan.data_is_sample && <Banner tone="warn">{t('sampleBanner')}</Banner>}
          <Card tone={STATUS_TONE[plan.status]}>
            <Row style={styles.between}>
              <H2>
                {t('sendBy')} {shortDate(plan.send_by, lang)}
              </H2>
              <Badge tone={STATUS_TONE[plan.status]}>
                {num(plan.days_left_to_send, lang)} {t('daysLeft')}
              </Badge>
            </Row>
            <Muted>
              {t('due')} {shortDate(plan.deadline, lang)} − {num(plan.transfer_days, lang)} {t('transferDays')} − {num(plan.buffer_days, lang)} {t('bufferDays')}
            </Muted>
          </Card>
          {best && (
            <Card tone="ok">
              <Badge tone="ok">{t('bestOption')}</Badge>
              <H2>{best.bank}</H2>
              <Row style={styles.between}>
                <Muted>{t('total')}</Muted>
                <ThemedText type="smallBold">{bdt(best.total_bdt, lang)}</ThemedText>
              </Row>
              {best.lines.map((l) => (
                <Row key={l.label} style={styles.between}>
                  <Muted style={{ flex: 1 }}>{l.label}</Muted>
                  <ThemedText type="small">{bdt(l.bdt, lang)}</ThemedText>
                </Row>
              ))}
              <ThemedText type="smallBold">
                {t('saves')} {bdt(plan.savings_best_vs_worst_bdt, lang)} {t('vsWorst')}
              </ThemedText>
              <Button title={t('createDraft')} onPress={() => prepare(best.quote_id)} loading={busy} />
            </Card>
          )}
          {plan.options
            .filter((o) => o.quote_id !== plan.best_quote_id)
            .map((o) => (
              <Card key={o.quote_id}>
                <Row style={styles.between}>
                  <ThemedText type="smallBold">{o.bank}</ThemedText>
                  <ThemedText type="smallBold">{bdt(o.total_bdt, lang)}</ThemedText>
                </Row>
                <Muted>
                  {t('hiddenCost')}: {bdt(o.overhead_bdt, lang)} ({num(o.overhead_pct, lang)}%)
                </Muted>
              </Card>
            ))}
        </>
      )}
    </>
  );
}

function LivingPlanner() {
  const { t, lang, call } = useSession();
  const [need, setNeed] = useState('6000');
  const [bridge, setBridge] = useState('1000');
  const [reserved, setReserved] = useState('0');
  const [plan, setPlan] = useState<LivingPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function makePlan() {
    setBusy(true);
    setError(null);
    try {
      setPlan(
        await call<LivingPlan>('/plan/living', post({ need_cny: need, bridge_cny: bridge || '0', reserved_card_tx: Number(reserved || 0) })),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function prepare() {
    if (!plan?.best) return;
    setBusy(true);
    setError(null);
    try {
      const b = plan.best;
      if (Number(b.tt_cny) > 0) {
        await call<Draft>('/drafts', post({ kind: 'tt_living', amount_cny: b.tt_cny, payee_id: 'student_own_cn', quote_id: b.quote_id, memo: 'Living costs' }));
      }
      if (b.atm_withdrawals_cny.length > 0) {
        const total = b.atm_withdrawals_cny.reduce((s, w) => s + Number(w), 0);
        await call<Draft>('/drafts', post({ kind: 'atm_plan', amount_cny: String(total), withdrawals: b.atm_withdrawals_cny }));
      }
      router.push('/activity');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const b = plan?.best;
  return (
    <>
      <Card>
        <Field label={t('needCny')} value={need} onChangeText={setNeed} keyboardType="numeric" />
        <Field label={t('bridgeCny')} value={bridge} onChangeText={setBridge} keyboardType="numeric" />
        <Field label={t('reservedTx')} value={reserved} onChangeText={setReserved} keyboardType="numeric" />
        <Button title={t('makePlan')} onPress={makePlan} loading={busy} />
      </Card>
      <ErrorBox error={error} />
      {plan && plan.data_is_sample && <Banner tone="warn">{t('sampleBanner')}</Banner>}
      {plan && !b && (
        <Card tone="block">
          <H2>{t('noPlan')}</H2>
          {plan.baseline_all_atm.violations.map((v) => (
            <Muted key={v}>• {v}</Muted>
          ))}
        </Card>
      )}
      {plan && b && (
        <>
          <Card tone="ok">
            <Badge tone="ok">{t('bestOption')}</Badge>
            {plan.steps.map((s, i) => (
              <ThemedText key={i} type="small">
                {num(i + 1, lang)}. {s}
              </ThemedText>
            ))}
            <Row style={styles.between}>
              <Muted>{t('total')}</Muted>
              <ThemedText type="smallBold">{bdt(b.total_bdt, lang)}</ThemedText>
            </Row>
            <Row style={styles.between}>
              <Muted>{t('allAtm')}</Muted>
              <ThemedText type="small">{bdt(plan.baseline_all_atm.total_bdt, lang)}</ThemedText>
            </Row>
            {plan.savings_vs_all_atm_bdt && (
              <ThemedText type="smallBold">
                {t('cheaperBy')} {bdt(plan.savings_vs_all_atm_bdt, lang)}
              </ThemedText>
            )}
            <Button title={t('createDrafts')} onPress={prepare} loading={busy} />
          </Card>
          <Card>
            <H2>{t('limitsUsed')}</H2>
            <Meter
              label={t('transactions')}
              used={b.cap_usage.card_tx_after}
              cap={b.cap_usage.card_tx_cap}
              display={`${num(b.cap_usage.card_tx_after, lang)} / ${num(b.cap_usage.card_tx_cap, lang)}`}
            />
            <Meter
              label={t('amountCharged')}
              used={Number(b.cap_usage.card_bdt_after)}
              cap={Number(b.cap_usage.card_bdt_cap)}
              display={`${bdt(b.cap_usage.card_bdt_after, lang)} / ${bdt(b.cap_usage.card_bdt_cap, lang)}`}
            />
            <Meter
              label={t('livingRemit')}
              used={Number(b.cap_usage.living_remit_usd_after)}
              cap={Number(b.cap_usage.living_remit_usd_cap)}
              display={`${num(Math.round(Number(b.cap_usage.living_remit_usd_after)), lang)} / ${num(b.cap_usage.living_remit_usd_cap, lang)}`}
            />
            {b.tt_cny !== '0.00' && <Muted>{cny(b.tt_cny, lang)} → {b.bank}</Muted>}
          </Card>
        </>
      )}
    </>
  );
}
