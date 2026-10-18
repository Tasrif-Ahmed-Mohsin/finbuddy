import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { ListenButton } from '@/components/listen-button';
import { ThemedText } from '@/components/themed-text';
import { BigNumber, Kicker, Panel, RingGauge, SpaceText } from '@/components/neo';
import { Badge, Banner, Button, Card, ErrorBox, Field, H2, Label, Meter, Muted, Row, Segmented, styles } from '@/components/ui';
import { Space, Tone } from '@/constants/theme';
import {
  post,
  type CrisisTest,
  type HundiCheck,
  type IncomeSource,
  type SavingsRule,
  type SavingsView,
  type ShieldSummary,
  type SpendResult,
} from '@/lib/api';
import type { StringKey } from '@/lib/i18n';
import { bdt, cny, fill, localDigits, num, shortDate } from '@/lib/format';
import { confirmPresence } from '@/lib/presence';
import { useSession } from '@/lib/session';

/** Run a request with a busy flag and an error message (the pattern every card here uses). */
function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function run<T>(fn: () => Promise<T>): Promise<T | null> {
    setBusy(true);
    setError(null);
    try {
      return await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return null;
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, run };
}

/** Today: the Shield in one card (the parent sees it only if the student shares it). */
export function ShieldMini({ shield }: { shield: ShieldSummary }) {
  const { t, lang } = useSession();
  return (
    <Pressable accessibilityRole="button" onPress={() => router.push('/save')}>
      <Card tone={shield.rule_on ? 'ok' : 'neutral'}>
        <Row style={styles.between}>
          <Label icon="shield-checkmark">{t('shieldTitle')}</Label>
          <Badge tone={shield.rule_on ? 'ok' : 'neutral'}>
            {localDigits(shield.days_of_living, lang)} {t('daysOfLiving')}
          </Badge>
        </Row>
        <Meter
          label={shield.rule_on ? t('ruleSigned') : t('ruleOff')}
          used={Number(shield.balance_cny)}
          cap={Number(shield.target_cny)}
          display={`${cny(shield.balance_cny, lang)} / ${cny(shield.target_cny, lang)}`}
        />
      </Card>
    </Pressable>
  );
}

/** The Shield: how full it is, releases waiting out their cooling-off, and taking money out (student) or approving (parent). */
export function ShieldCard({ v, onChanged }: { v: SavingsView; onChanged: () => void }) {
  const { t, lang, role, call } = useSession();
  const { busy, error, run } = useAction();
  const [amount, setAmount] = useState('');
  const [done, setDone] = useState<string | null>(null);
  const s = v.shield;
  if (!s) {
    return (
      <Card>
        <H2 icon="shield-checkmark">{t('shieldTitle')}</H2>
        <Muted>{t('shieldPrivate')}</Muted>
      </Card>
    );
  }
  const terms = v.terms;

  async function takeOut() {
    if (!(await confirmPresence(t('takeOut')))) return;
    const r = await run(() => call('/save/shield/release', post({ amount_cny: amount })));
    if (r) {
      setAmount('');
      setDone(t('releaseAsked'));
      onChanged();
    }
  }
  async function cancel(id: string) {
    if (await run(() => call(`/save/shield/release/${id}/cancel`, post({})))) onChanged();
  }
  async function approve(id: string) {
    if (!(await confirmPresence(t('approveRelease')))) return;
    if (await run(() => call(`/save/shield/release/${id}/approve`, post({})))) onChanged();
  }
  async function stop() {
    if (await run(() => call('/save/rule', { method: 'DELETE' }))) onChanged();
  }

  return (
    <>
      {/* Shield bay: the Shield as a reactor ring, how much is in it, and how many days of living it buys. */}
      <Panel>
        <Row style={styles.between}>
          <Kicker dark>{t('shieldTitle')}</Kicker>
          {s.full && <Badge tone="ok">{t('shieldFull')}</Badge>}
        </Row>
        <Row style={{ flexWrap: 'nowrap', gap: 16 }}>
          <RingGauge pct={s.pct_of_target / 100} value={`${num(s.pct_of_target, lang)}%`} label={t('targetLabel')} sub={cny(s.target_cny, lang)} size={136} />
          <View style={{ flex: 1, gap: 6 }}>
            <BigNumber value={Number(s.balance_cny)} size={34} weight="600" color={Space.text} format={(n) => cny(Math.round(n), lang)} />
            <SpaceText neon small>
              {localDigits(s.days_of_living, lang)} {t('daysOfLiving')}
            </SpaceText>
            <SpaceText muted small>
              {v.rule ? fill(t('ruleOnFmt'), { pct: num(v.rule.shield_pct, lang) }) : t('ruleOff')}
            </SpaceText>
          </View>
        </Row>
      </Panel>
    <Card tone={s.full ? 'ok' : v.rule ? 'info' : 'neutral'}>
      <Muted>{role === 'parent' ? t('shieldExplainParent') : t('shieldExplain')}</Muted>

      {v.releases.map((r) => (
        <Banner key={r.id} tone="warn">
          ⏳ {t('waitingRelease')}: {cny(r.amount_cny, lang)} · {t('leavesOn')} {shortDate(r.available_at, lang)}
          {r.needs_family ? ` · 👪` : ''}
        </Banner>
      ))}
      {role === 'student' &&
        v.releases.map((r) => <Button key={`c-${r.id}`} title={`${t('cancelRelease')} ${cny(r.amount_cny, lang)}`} variant="secondary" onPress={() => cancel(r.id)} />)}
      {role === 'parent' &&
        v.releases.map((r) => <Button key={`a-${r.id}`} title={`${t('approveRelease')} (${cny(r.amount_cny, lang)})`} onPress={() => approve(r.id)} loading={busy} />)}

      {role === 'student' && Number(s.free_cny) > 0 && (
        <View style={{ gap: 8 }}>
          <Field label={t('takeOutAmount')} value={amount} onChangeText={setAmount} keyboardType="numeric" />
          {terms && (
            <Muted>
              {fill(t('takeOutRuleFmt'), { hours: num(terms.cooling_off_hours, lang), lock: terms.family_lock ? t('takeOutLock') : '' })}
            </Muted>
          )}
          <Button title={t('takeOut')} variant="secondary" onPress={takeOut} loading={busy} disabled={!amount} />
        </View>
      )}
      {role === 'student' && v.rule && <Button title={t('stopRule')} variant="danger" onPress={stop} />}
      {done && <Badge tone="ok">{done}</Badge>}
      <ErrorBox error={error} />
    </Card>
    </>
  );
}

const KIND_LABEL: Record<IncomeSource['kind'], StringKey> = { stipend: 'kindStipend', work_study: 'kindJob', other: 'kindOther' };

/** Income in China: a stipend or an approved campus job. Unauthorised work is flagged and never planned on. */
export function IncomeCard({ v, onChanged }: { v: SavingsView; onChanged: () => void }) {
  const { t, lang, call } = useSession();
  const { busy, error, run } = useAction();
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<IncomeSource['kind']>('work_study');
  const [label, setLabel] = useState('');
  const [amount, setAmount] = useState('1500');
  const [every, setEvery] = useState<'month' | 'week'>('month');
  const [payDay, setPayDay] = useState('10');
  const [hours, setHours] = useState('8');
  const [permission, setPermission] = useState<'yes' | 'no'>('yes');
  const income = v.income;
  if (!income) return null;

  async function add() {
    const body = {
      kind,
      label,
      amount_cny: amount,
      every,
      pay_day: Number(payDay || 0),
      hours_per_week: kind === 'work_study' ? hours || null : null,
      permission: permission === 'yes',
    };
    if (await run(() => call<IncomeSource>('/save/income/sources', post(body)))) {
      setOpen(false);
      onChanged();
    }
  }
  async function paidToday(src: IncomeSource) {
    if (await run(() => call('/save/income', post({ amount_cny: src.amount_cny, source_id: src.id })))) onChanged();
  }
  async function remove(id: string) {
    if (await run(() => call(`/save/income/sources/${id}`, { method: 'DELETE' }))) onChanged();
  }

  return (
    <Card>
      <H2>💼 {t('incomeTitle')}</H2>
      <Muted>{t('incomeIntro')}</Muted>
      {income.sources.length === 0 && <Muted>{t('incomeNone')}</Muted>}
      {income.sources.map((src) => (
        <View key={src.id} style={{ gap: 4 }}>
          <Row style={styles.between}>
            <ThemedText type="smallBold" style={{ flex: 1 }}>
              {src.label} · {t(KIND_LABEL[src.kind])}
            </ThemedText>
            <ThemedText type="smallBold">
              {cny(src.monthly_cny, lang)} {t('perMonth')}
            </ThemedText>
          </Row>
          {src.status === 'at_risk' ? (
            <Banner tone="block">⚠️ {t('atRisk')}. {src.checks.find((c) => !c.passed && c.severity === 'block')?.message}</Banner>
          ) : (
            src.checks
              .filter((c) => !c.passed)
              .map((c) => (
                <Banner key={c.id} tone="warn">
                  {c.message}
                </Banner>
              ))
          )}
          <Row>
            <Button title={t('logPayNow')} variant="secondary" onPress={() => paidToday(src)} loading={busy} />
            <Button title={t('removeIncome')} variant="secondary" onPress={() => remove(src.id)} />
          </Row>
        </View>
      ))}
      {income.next_pay && (
        <Muted>
          {t('nextPay')}: {cny(income.next_pay.amount_cny, lang)} · {shortDate(income.next_pay.date, lang)}
        </Muted>
      )}
      {open ? (
        <View style={{ gap: 8 }}>
          <Segmented<IncomeSource['kind']>
            value={kind}
            onChange={setKind}
            options={[
              { value: 'work_study', label: t('kindJob') },
              { value: 'stipend', label: t('kindStipend') },
              { value: 'other', label: t('kindOther') },
            ]}
          />
          <Field label={t('incomeLabel')} value={label} onChangeText={setLabel} />
          <Field label={t('incomeAmount')} value={amount} onChangeText={setAmount} keyboardType="numeric" />
          <Segmented<'month' | 'week'>
            value={every}
            onChange={setEvery}
            options={[
              { value: 'month', label: t('everyMonth') },
              { value: 'week', label: t('everyWeek') },
            ]}
          />
          <Field label={every === 'month' ? t('payDayMonth') : t('payDayWeek')} value={payDay} onChangeText={setPayDay} keyboardType="numeric" />
          {kind === 'work_study' && (
            <>
              <Field label={t('hoursWeek')} value={hours} onChangeText={setHours} keyboardType="numeric" />
              <Muted>{t('permissionQ')}</Muted>
              <Segmented<'yes' | 'no'>
                value={permission}
                onChange={setPermission}
                options={[
                  { value: 'yes', label: t('permissionYes') },
                  { value: 'no', label: t('permissionNo') },
                ]}
              />
            </>
          )}
          <Button title={t('addIncome')} onPress={add} loading={busy} disabled={!amount} />
        </View>
      ) : (
        <Button title={`+ ${t('addIncome')}`} variant="secondary" onPress={() => setOpen(true)} />
      )}
      <ErrorBox error={error} />
    </Card>
  );
}

/** Wants through the taka lens: prices in yuan look small, so every purchase is also shown as what it costs the family. */
export function WantsCard({ v, onChanged }: { v: SavingsView; onChanged: () => void }) {
  const { t, lang, call } = useSession();
  const { busy, error, run } = useAction();
  const [amount, setAmount] = useState('');
  const [where, setWhere] = useState('');
  const [kind, setKind] = useState<'auto' | 'want' | 'need'>('auto');
  const [last, setLast] = useState<SpendResult | null>(null);
  const w = v.wants;
  if (!w) return null;
  const over = Number(w.over_cny) > 0;

  async function log() {
    const r = await run(() =>
      call<SpendResult>('/save/spend', post({ amount_cny: amount, merchant: where, kind: kind === 'auto' ? null : kind, lang })),
    );
    if (r) {
      setLast(r);
      setAmount('');
      setWhere('');
      onChanged();
    }
  }
  const lens = (c: string, b: string, d: string) => fill(t('lensFmt'), { cny: cny(c, lang), bdt: bdt(b, lang), days: localDigits(d, lang) });

  return (
    <Card tone={over ? 'warn' : 'neutral'}>
      <H2>🔎 {t('wantsTitle')}</H2>
      <Muted>{t('wantsIntro')}</Muted>
      <Row style={styles.between}>
        <Muted>{t('wantsSpent')}</Muted>
        <ThemedText type="smallBold">{cny(w.wants_cny, lang)}</ThemedText>
      </Row>
      <Row style={styles.between}>
        <Muted>{t('wantsAtHome')}</Muted>
        <ThemedText type="smallBold" style={{ color: Tone.warn.fg }}>
          {bdt(w.lens.bdt, lang)} · {localDigits(w.lens.days_of_living, lang)} {t('daysOfLiving')}
        </ThemedText>
      </Row>
      <Row style={styles.between}>
        <Muted>{t('allowanceLeft')}</Muted>
        <ThemedText type="small">{cny(w.left_cny, lang)}</ThemedText>
      </Row>
      {over && (
        <Banner tone="warn">
          {t('overAllowance')}: {lens(w.over_cny, w.over_lens.bdt, w.over_lens.days_of_living)}
        </Banner>
      )}
      {w.by_category.map((c) => (
        <Row key={c.category} style={styles.between}>
          <Muted style={{ flex: 1 }}>• {c.label}</Muted>
          <ThemedText type="small">{cny(c.cny, lang)}</ThemedText>
        </Row>
      ))}
      <Field label={t('spendAmount')} value={amount} onChangeText={setAmount} keyboardType="numeric" />
      <Field label={t('spendWhere')} value={where} onChangeText={setWhere} />
      <Segmented<'auto' | 'want' | 'need'>
        value={kind}
        onChange={setKind}
        options={[
          { value: 'auto', label: t('kindAuto') },
          { value: 'want', label: t('kindWant') },
          { value: 'need', label: t('kindNeed') },
        ]}
      />
      <Button title={t('logIt')} variant="secondary" onPress={log} loading={busy} disabled={!amount} />
      {last && (
        <Banner tone={last.kind === 'want' ? 'warn' : 'info'}>
          {last.label}: {lens(last.lens.amount_cny, last.lens.bdt, last.lens.days_of_living)}
        </Banner>
      )}
      <ErrorBox error={error} />
    </Card>
  );
}

/** Pay yourself first: the student chooses the share, target and waiting time, reads (or hears) the rule, and signs it. */
export function SavingsRuleCard({ v, onChanged }: { v: SavingsView; onChanged: () => void }) {
  const { t, lang, call } = useSession();
  const { busy, error, run } = useAction();
  const sug = v.suggested;
  const [pct, setPct] = useState(String(sug?.pct ?? 50));
  const [target, setTarget] = useState(String(Math.round(Number(sug?.target_cny ?? 6000))));
  const [wait, setWait] = useState<'0' | '24' | '72'>(String(sug?.cooling_off_hours ?? 24) as '0' | '24' | '72');
  const [lock, setLock] = useState<'yes' | 'no'>('no');
  const [share, setShare] = useState<'yes' | 'no'>('yes');
  const [words, setWords] = useState('');
  const [proposal, setProposal] = useState<SavingsRule | null>(v.proposal ?? null);
  if (v.rule) return null;

  async function prepare(useWords: boolean) {
    const body = useWords
      ? { text: words, lang, share_with_family: share === 'yes' }
      : { pct: Number(pct), target_cny: target, cooling_off_hours: Number(wait), family_lock: lock === 'yes', share_with_family: share === 'yes', lang };
    const r = await run(() => call<SavingsRule>('/save/rule/proposals', post(body)));
    if (r) setProposal(r);
  }
  async function sign(p: SavingsRule) {
    if (!(await confirmPresence(t('signRule')))) return;
    // The server checks this hash is the rule it holds now: what you read is what you sign.
    if (await run(() => call<SavingsRule>(`/save/rule/proposals/${p.id}/sign`, post({ rule_hash: p.hash })))) {
      setProposal(null);
      onChanged();
    }
  }

  if (proposal) {
    const summary = proposal.summary[lang];
    const when = proposal.projection?.reaches_target_on;
    return (
      <Card tone={proposal.errors.length ? 'block' : 'warn'}>
        <H2>{proposal.errors.length ? t('fixFirst') : t('readBack')}</H2>
        {proposal.text ? <Muted>“{proposal.text}”</Muted> : null}
        {proposal.errors.map((e) => (
          <Banner key={e} tone="block">
            {e}
          </Banner>
        ))}
        {!proposal.errors.length && (
          <>
            <ThemedText>{summary}</ThemedText>
            <ListenButton text={summary} lang={lang} />
            {proposal.notes.map((n) => (
              <Banner key={n} tone="warn">
                {n}
              </Banner>
            ))}
            <Muted>{when ? `${t('fullAround')} ${shortDate(when, lang)}` : t('fullSlow')}</Muted>
            {proposal.status === 'proposed' && <Button title={`✍️ ${t('signRule')}`} onPress={() => sign(proposal)} loading={busy} />}
          </>
        )}
        <Button title={t('cancelRelease')} variant="secondary" onPress={() => setProposal(null)} />
        <ErrorBox error={error} />
      </Card>
    );
  }

  return (
    <Card>
      <H2>📝 {t('ruleTitle')}</H2>
      <Muted>{t('ruleIntro')}</Muted>
      {sug && (
        <Banner tone="info">
          💡 {fill(t('suggestedFmt'), { pct: num(sug.pct, lang), target: cny(sug.target_cny, lang) })}
          {sug.projection.reaches_target_on ? ` · ${t('fullAround')} ${shortDate(sug.projection.reaches_target_on, lang)}` : ''}
        </Banner>
      )}
      <Muted>{t('shareOfPay')}</Muted>
      <Segmented<string>
        value={pct}
        onChange={setPct}
        options={['20', '30', '50', '70'].map((p) => ({ value: p, label: `${num(p, lang)}%` }))}
      />
      <Field label={t('targetLabel')} value={target} onChangeText={setTarget} keyboardType="numeric" />
      <Muted>{t('waitLabel')}</Muted>
      <Segmented<'0' | '24' | '72'>
        value={wait}
        onChange={setWait}
        options={[
          { value: '0', label: t('wait0') },
          { value: '24', label: t('wait24') },
          { value: '72', label: t('wait72') },
        ]}
      />
      <YesNo label={t('familyLockLabel')} value={lock} onChange={setLock} />
      <YesNo label={t('shareFamilyLabel')} value={share} onChange={setShare} />
      <Button title={t('writeRule')} onPress={() => prepare(false)} loading={busy} disabled={!pct || !target} />
      <Field label={t('orWords')} value={words} onChangeText={setWords} placeholder={t('ruleExample')} multiline />
      <Row>
        <Button title={t('useExample')} variant="secondary" onPress={() => setWords(t('ruleExample'))} />
        <Button title={t('writeRule')} variant="secondary" onPress={() => prepare(true)} disabled={words.trim().length < 3} />
      </Row>
      <ErrorBox error={error} />
    </Card>
  );
}

function YesNo({ label, value, onChange }: { label: string; value: 'yes' | 'no'; onChange: (v: 'yes' | 'no') => void }) {
  const { t } = useSession();
  return (
    <View style={{ gap: 4 }}>
      <Muted>{label}</Muted>
      <Segmented<'yes' | 'no'>
        value={value}
        onChange={onChange}
        options={[
          { value: 'yes', label: t('yesLabel') },
          { value: 'no', label: t('noLabel') },
        ]}
      />
    </View>
  );
}

const OPTION_KEY: Record<HundiCheck['options'][number]['key'], StringKey> = {
  hundi: 'hundiOpt_hundi',
  bank_once: 'hundiOpt_bank_once',
  shield: 'hundiOpt_shield',
  planned: 'hundiOpt_planned',
};
const VERDICT_KEY: Record<HundiCheck['verdict'], StringKey> = {
  use_shield: 'verdict_use_shield',
  shield_then_bank: 'verdict_shield_then_bank',
  wait_for_planned: 'verdict_wait_for_planned',
  bank: 'verdict_bank',
};

/** Hundi, honestly: the offer against one legal bank transfer, the Shield and the planned transfer, plus the hidden risks. */
export function HundiCard() {
  const { t, lang, call } = useSession();
  const { busy, error, run } = useAction();
  const [amount, setAmount] = useState('500');
  const [currency, setCurrency] = useState<'USD' | 'CNY' | 'BDT'>('USD');
  const [rate, setRate] = useState('');
  const [res, setRes] = useState<HundiCheck | null>(null);

  async function check() {
    const r = await run(() =>
      call<HundiCheck>('/save/hundi-check', post({ amount, currency, offered_bdt_per_usd: rate || null, lang })),
    );
    if (r) setRes(r);
  }
  return (
    <Card>
      <H2>⚖️ {t('hundiTitle')}</H2>
      <Muted>{t('hundiIntro')}</Muted>
      <Field label={t('hundiAmount')} value={amount} onChangeText={setAmount} keyboardType="numeric" />
      <Segmented<'USD' | 'CNY' | 'BDT'>
        value={currency}
        onChange={setCurrency}
        options={[
          { value: 'USD', label: '$ USD' },
          { value: 'CNY', label: '¥ CNY' },
          { value: 'BDT', label: '৳ BDT' },
        ]}
      />
      <Field label={t('hundiRate')} value={rate} onChangeText={setRate} keyboardType="decimal-pad" />
      <Button title={t('hundiCompare')} onPress={check} loading={busy} disabled={!amount} />
      <ErrorBox error={error} />
      {res && (
        <View style={{ gap: 8 }}>
          <Banner tone="ok">✅ {t(VERDICT_KEY[res.verdict])}</Banner>
          {res.options.map((o) => (
            <Row key={o.key} style={{ ...styles.between, alignItems: 'flex-start' }}>
              <ThemedText type="small" style={{ flex: 1, color: o.legal ? undefined : Tone.block.fg }}>
                {o.legal ? '✓' : '✗'} {t(OPTION_KEY[o.key])}
                {o.key === 'bank_once' ? ` (${o.bank}) · ${shortDate(o.lands, lang)}` : ''}
                {o.key === 'shield' ? ` · ${cny(o.amount_cny, lang)}` : ''}
                {o.key === 'planned' ? ` · ${cny(o.amount_cny, lang)} · ${shortDate(o.lands, lang)}` : ''}
              </ThemedText>
              <ThemedText type="smallBold" style={{ textAlign: 'right' }}>
                {o.key === 'shield' || o.key === 'planned' ? bdt(0, lang) : `+${bdt(o.extra_bdt, lang)}`}
              </ThemedText>
            </Row>
          ))}
          <Muted>
            + = {t('aboveMarket')} ({bdt(res.mid_bdt, lang)})
          </Muted>
          <Banner tone={res.bank_costs_more_on_paper_bdt ? 'warn' : 'info'}>{res.honest_note}</Banner>
          <ThemedText type="smallBold">{t('hundiHides')}</ThemedText>
          {res.risks.map((r) => (
            <Row key={r.key} style={{ alignItems: 'flex-start' }}>
              <Badge tone={r.confidence === 'official' ? 'ok' : 'neutral'}>{r.confidence}</Badge>
              <ThemedText type="small" style={{ flex: 1 }}>
                {r.text}
              </ThemedText>
            </Row>
          ))}
          <ThemedText type="smallBold">{t('legalWays')}</ThemedText>
          {res.legal_routes.map((r) => (
            <Row key={r.key} style={{ alignItems: 'flex-start' }}>
              <Badge tone={r.confidence === 'official' ? 'ok' : 'warn'}>{r.confidence}</Badge>
              <ThemedText type="small" style={{ flex: 1 }}>
                {r.text}
              </ThemedText>
            </Row>
          ))}
        </View>
      )}
    </Card>
  );
}

/** The friend's problem as a test: banks stop student transfers for weeks. Today's habits vs Bluefin vs Bluefin + Shield. */
export function CrisisCard({ crisis }: { crisis: CrisisTest }) {
  const { t, lang, role } = useSession();
  const z = crisis.zero_share_pct;
  const w = crisis.worst;
  const pct = (x: number | null) => (x === null ? '–' : localDigits(`${Math.round(x)}%`, lang));
  const days = (x: number | null) => (x === null ? '–' : `${num(x, lang)} ${t('daysShort')}`);
  const m = crisis.median_stuck;
  const rows: [string, string, string, string][] = [
    [t('crisisCovered'), pct(z.today), pct(z.sathi), pct(z.sathi_shield)],
    [t('crisisMedian'), days(m.today), days(m.sathi), days(m.sathi_shield)],
    [`${t('crisisWorst')} (${shortDate(w.from, lang)})`, days(w.stuck_today), days(w.stuck_sathi), days(w.stuck_sathi_shield)],
  ];
  return (
    <Card tone="info">
      <H2>📉 {t('crisisTitle')}</H2>
      <Muted>{fill(t('crisisIntroFmt'), { weeks: num(crisis.weeks, lang) })}</Muted>
      <Row style={{ ...styles.between, flexWrap: 'nowrap' }}>
        <Muted style={{ flex: 1 }}> </Muted>
        <ThemedText type="smallBold" style={{ width: 70, textAlign: 'right', color: Tone.block.fg }}>
          {t('stuckToday')}
        </ThemedText>
        <ThemedText type="smallBold" style={{ width: 70, textAlign: 'right' }}>
          {t('stuckSathi')}
        </ThemedText>
        <ThemedText type="smallBold" style={{ width: 70, textAlign: 'right', color: Tone.ok.fg }}>
          {t('crisisShield')}
        </ThemedText>
      </Row>
      {rows.map(([label, a, b, c]) => (
        <Row key={label} style={{ ...styles.between, flexWrap: 'nowrap' }}>
          <ThemedText type="small" style={{ flex: 1 }}>
            {label}
          </ThemedText>
          <ThemedText type="small" style={{ width: 70, textAlign: 'right' }}>
            {a}
          </ThemedText>
          <ThemedText type="small" style={{ width: 70, textAlign: 'right' }}>
            {b}
          </ThemedText>
          <ThemedText type="smallBold" style={{ width: 70, textAlign: 'right' }}>
            {c}
          </ThemedText>
        </Row>
      ))}
      <ThemedText type="smallBold">{fill(t('crisisNeededFmt'), { amount: cny(w.shield_needed_cny, lang) })}</ThemedText>
      {crisis.protected_from && (
        <Badge tone="ok">
          {t('crisisProtectedFrom')} {shortDate(crisis.protected_from, lang)}
        </Badge>
      )}
      {!crisis.with_shield && <Muted>{role === 'parent' ? t('crisisParentNotShared') : t('crisisNoIncome')}</Muted>}
      {crisis.rule_is_suggestion && <Muted>{t('crisisSuggestion')}</Muted>}
      <Muted>{crisis.method}</Muted>
    </Card>
  );
}

/** Proof for the Shield: every move is an entry in the hash-chained log (who or what moved it, at which level). */
export function ShieldHistory({ v }: { v: SavingsView }) {
  const { t, lang } = useSession();
  if (v.history.length === 0) return null;
  return (
    <Card>
      <H2>🧾 {t('historyTitle')}</H2>
      {v.history.map((e) => (
        <Row key={e.seq} style={{ ...styles.between, flexWrap: 'nowrap' }}>
          <ThemedText type="small" style={{ flex: 1 }}>
            #{num(e.seq, lang)} {e.event.replace(/_/g, ' ')}
            {e.amount_cny ? ` · ${cny(e.amount_cny, lang)}` : ''}
          </ThemedText>
          <Badge tone={e.level === 'MANDATE' ? 'ok' : 'neutral'}>{e.level}</Badge>
        </Row>
      ))}
    </Card>
  );
}
