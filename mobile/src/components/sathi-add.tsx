import * as Clipboard from 'expo-clipboard';
import { useState } from 'react';

import { ThemedText } from '@/components/themed-text';
import { Badge, Banner, Button, Card, ErrorBox, Field, Muted, Row, Segmented } from '@/components/ui';
import { post, type IngestResult } from '@/lib/api';
import { bdt, cny } from '@/lib/format';
import { useSession } from '@/lib/session';

type Source = 'sms' | 'email';

export function SathiAdd() {
  const { t, lang, call } = useSession();
  const [source, setSource] = useState<Source>('sms');
  const [sender, setSender] = useState('');
  const [text, setText] = useState('');
  const [result, setResult] = useState<IngestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function paste() {
    const s = await Clipboard.getStringAsync();
    if (s) setText(s);
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      setResult(await call<IngestResult>('/inbox/messages', post({ source, sender: sender || 'unknown', text })));
      setText('');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const txn = result?.transaction;
  return (
    <>
      <Card>
        <Segmented<Source> value={source} onChange={setSource} options={[{ value: 'sms', label: 'SMS' }, { value: 'email', label: 'Email' }]} />
        <Field label={t('sender')} value={sender} onChangeText={setSender} autoCapitalize="none" />
        <Field label={t('messageText')} value={text} onChangeText={setText} multiline style={{ minHeight: 110, textAlignVertical: 'top' }} />
        <Row>
          <Button title={t('pasteClipboard')} variant="secondary" onPress={paste} />
        </Row>
        <Button title={t('addToSathi')} onPress={submit} loading={busy} disabled={!text.trim()} />
      </Card>
      <ErrorBox error={error} />
      {result && !result.kept && <Banner tone="neutral">{t('notStored')}</Banner>}
      {result?.kept && (
        <Card tone={result.flags?.some((f) => f.severity === 'high') ? 'block' : 'ok'}>
          {txn && (
            <Row>
              <Badge tone="ok">{t('tracked')}</Badge>
              <ThemedText type="smallBold">
                {txn.direction === 'credit' ? '+' : '−'}
                {txn.currency === 'CNY' ? cny(txn.amount, lang) : bdt(txn.amount, lang)}
              </ThemedText>
              <Muted>
                {txn.kind} · {txn.parser === 'llm' ? 'AI' : 'rules'}
              </Muted>
            </Row>
          )}
          {result.message?.otp && <Banner tone="info">One-time code removed. Never share it.</Banner>}
          {result.flags?.map((f) => (
            <ThemedText key={f.category} type="small">
              ⚠ {f.advice}
            </ThemedText>
          ))}
          <Muted>{result.message?.text}</Muted>
        </Card>
      )}
    </>
  );
}
