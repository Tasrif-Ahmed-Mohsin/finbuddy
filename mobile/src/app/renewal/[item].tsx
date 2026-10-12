import * as Clipboard from 'expo-clipboard';
import { useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import { Pressable, Share } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Badge, Banner, Button, Card, ErrorBox, Field, H1, H2, Muted, Row, Screen, Segmented, styles } from '@/components/ui';
import { post, type RenewalCase, type RenewalStep } from '@/lib/api';
import { localDigits, num, shortDate } from '@/lib/format';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

const STATE_TONE = { done: 'ok', overdue: 'block', due_soon: 'warn', upcoming: 'neutral' } as const;
const CONF_TONE = { secondary: 'warn', assumption: 'neutral', field: 'info', official: 'ok' } as const;

/** Renewal assistant (T3): steps worked back from the expiry date + messages the user shares themselves. */
export default function RenewalScreen() {
  const { item } = useLocalSearchParams<{ item: string }>();
  const { t, lang, call } = useSession();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newExpiry, setNewExpiry] = useState('');

  const { data: c, reload } = useLoad(
    useCallback(async () => {
      try {
        return await call<RenewalCase>(`/renewals/${item}`);
      } catch {
        return null; // no plan yet
      }
    }, [call, item]),
  );

  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!c) {
    return (
      <Screen>
        <H1>{t('renewalPlan')}</H1>
        <ErrorBox error={error} />
        <Button title={t('makeRenewalPlan')} onPress={() => act(() => call(`/renewals/${item}`, { method: 'POST' }))} loading={busy} />
      </Screen>
    );
  }

  const label = c.label[lang] ?? c.label.en;
  return (
    <Screen>
      <H1>{label}</H1>
      <Row>
        <Badge tone={c.status === 'completed' ? 'ok' : c.days_to_expiry <= 21 ? 'warn' : 'info'}>
          {c.status === 'completed' ? t('completedLabel') : `${t('expires')} ${shortDate(c.expiry, lang)} · ${num(c.days_to_expiry, lang)} ${t('daysLeft')}`}
        </Badge>
      </Row>
      {c.late && c.status === 'open' && <Banner tone="block">{t('lateWarning')}</Banner>}
      <ErrorBox error={error} />

      <Card>
        {c.steps.map((s) => (
          <StepRow key={s.id} step={s} disabled={busy || c.status === 'completed'}
            onToggle={() => act(() => call(`/renewals/case/${c.id}/steps/${s.id}`, post({ status: s.status === 'done' ? 'todo' : 'done' })))} />
        ))}
      </Card>

      <MessageCard title={t('universityEmail')} texts={c.messages.university_email} options={[{ value: 'en', label: 'English' }, { value: 'zh', label: '中文' }]} />
      <MessageCard title={t('parentMessage')} texts={c.messages.parent_message} options={[{ value: 'bn', label: 'বাংলা' }, { value: 'en', label: 'English' }]} />
      <Muted>{t('sendsNothing')}</Muted>

      <Card>
        <H2>{t('documentsNeeded')}</H2>
        <Muted>{t('fromUniversity')}</Muted>
        {c.documents.university.map((d) => (
          <DocRow key={d.key} text={`${lang === 'bn' ? d.bn : d.en}${d.zh ? ` · ${d.zh}` : ''}`} confidence={d.confidence} />
        ))}
        <Muted>{t('forBank')}</Muted>
        {c.documents.bank.map((d) => (
          <DocRow key={d.key} text={lang === 'bn' ? d.bn : d.en} confidence={d.confidence} />
        ))}
        <Muted>{c.note}</Muted>
      </Card>

      {c.status === 'open' && (
        <Card>
          <H2>{t('renewalDone')}</H2>
          <Field label={t('newExpiry')} value={newExpiry} onChangeText={setNewExpiry} autoCapitalize="none" />
          <Button title={t('saveNewExpiry')} disabled={!/^\d{4}-\d{2}-\d{2}$/.test(newExpiry)} loading={busy}
            onPress={() => act(() => call(`/renewals/case/${c.id}/complete`, post({ new_expiry: newExpiry })))} />
        </Card>
      )}
    </Screen>
  );
}

function StepRow({ step, onToggle, disabled }: { step: RenewalStep; onToggle: () => void; disabled: boolean }) {
  const { t, lang } = useSession();
  const stateLabel = step.state === 'overdue' ? t('overdue') : step.state === 'due_soon' ? t('dueSoon') : '';
  return (
    <Pressable onPress={onToggle} disabled={disabled} style={{ paddingVertical: 8, gap: 4 }}>
      <Row style={{ alignItems: 'flex-start' }}>
        <ThemedText style={{ fontSize: 20 }}>{step.status === 'done' ? '☑' : '☐'}</ThemedText>
        <ThemedText type="smallBold" style={{ flex: 1, textDecorationLine: step.status === 'done' ? 'line-through' : 'none' }}>
          {step.title}
        </ThemedText>
      </Row>
      <Row>
        <Badge tone={step.owner === 'parent' ? 'info' : 'neutral'}>{step.owner === 'parent' ? t('parent') : t('student')}</Badge>
        <Badge tone={STATE_TONE[step.state]}>
          {shortDate(step.due, lang)}
          {stateLabel ? ` · ${stateLabel}` : ''}
        </Badge>
      </Row>
      <Muted>{step.detail}</Muted>
    </Pressable>
  );
}

function MessageCard<K extends string>({ title, texts, options }: { title: string; texts: Record<K, string>; options: { value: K; label: string }[] }) {
  const { t } = useSession();
  const [which, setWhich] = useState<K>(options[0].value);
  const [copied, setCopied] = useState(false);
  const text = texts[which];
  async function copy() {
    await Clipboard.setStringAsync(text);
    setCopied(true);
  }
  async function share() {
    try {
      await Share.share({ message: text });
    } catch {
      await copy(); // e.g. browsers without the share sheet
    }
  }
  return (
    <Card>
      <H2>{title}</H2>
      <Segmented<K> value={which} onChange={(v) => { setWhich(v); setCopied(false); }} options={options} />
      <ThemedText type="small" selectable>
        {text}
      </ThemedText>
      <Row style={styles.between}>
        <Button title={copied ? `✓ ${t('copied')}` : t('copy')} variant="secondary" onPress={copy} />
        <Button title={t('share')} onPress={share} />
      </Row>
    </Card>
  );
}

function DocRow({ text, confidence }: { text: string; confidence: string }) {
  const { lang } = useSession();
  return (
    <Row style={{ alignItems: 'flex-start' }}>
      <ThemedText type="small">•</ThemedText>
      <ThemedText type="small" style={{ flex: 1 }}>
        {localDigits(text, lang)}
      </ThemedText>
      <Badge tone={CONF_TONE[confidence as keyof typeof CONF_TONE] ?? 'neutral'}>{confidence}</Badge>
    </Row>
  );
}
