import { router } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Badge, Button, ErrorBox, Field, Muted, Row } from '@/components/ui';
import { Brand } from '@/constants/theme';
import { post, type ChatReply } from '@/lib/api';
import { useSession } from '@/lib/session';

type Turn = { role: 'user' | 'assistant'; content: string; reply?: ChatReply };

/** The model is asked for plain text; this strips any markdown that slips through. */
function plain(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^\s*[-*]\s+/gm, '• ');
}

export function SathiChat() {
  const { t, lang, call } = useSession();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send() {
    const message = text.trim();
    if (!message) return;
    setText('');
    setError(null);
    const history = turns.map(({ role, content }) => ({ role, content }));
    setTurns((prev) => [...prev, { role: 'user', content: message }]);
    setBusy(true);
    try {
      const reply = await call<ChatReply>('/agent/chat', post({ message, history, lang }));
      setTurns((prev) => [...prev, { role: 'assistant', content: reply.reply, reply }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {turns.length === 0 && <Muted>{t('chatHint')}</Muted>}
      {turns.map((turn, i) =>
        turn.role === 'user' ? (
          <View key={i} style={{ alignSelf: 'flex-end', maxWidth: '85%', backgroundColor: Brand.primary, borderRadius: 14, padding: 10 }}>
            <ThemedText style={{ color: Brand.primaryText }}>{turn.content}</ThemedText>
          </View>
        ) : (
          <ThemedView key={i} type="backgroundElement" style={{ alignSelf: 'flex-start', maxWidth: '92%', borderRadius: 14, padding: 10, gap: 6 }}>
            <ThemedText type="small">{plain(turn.content)}</ThemedText>
            <Row>
              <Badge tone={turn.reply?.mode === 'llm' ? 'info' : 'neutral'}>{turn.reply?.mode === 'llm' ? 'AI · DeepSeek' : 'offline rules'}</Badge>
              {turn.reply?.tools_used.length ? <Muted>{turn.reply.tools_used.join(', ')}</Muted> : null}
            </Row>
            {turn.reply?.actions.map((a) =>
              a.type === 'draft' ? (
                <Button key={a.draft_id} title={t('openDraft')} onPress={() => router.push({ pathname: '/draft/[id]', params: { id: a.draft_id } })} />
              ) : a.type === 'renewal' ? (
                <Button key={a.case_id} title={t('openRenewal')} onPress={() => router.push({ pathname: '/renewal/[item]', params: { item: a.item } })} />
              ) : a.type === 'mandate' ? (
                <Button key={a.proposal_id} title={t('signMandate')} onPress={() => router.push('/family')} />
              ) : (
                <Badge key={`card-${a.last4}`} tone="warn">
                  🔒 {t('card')} ••••{a.last4}: {a.status}
                </Badge>
              ),
            )}
          </ThemedView>
        ),
      )}
      <ErrorBox error={error} />
      <Field label="" value={text} onChangeText={setText} placeholder={t('typeMessage')} multiline onSubmitEditing={send} />
      <Button title={t('send')} onPress={send} loading={busy} disabled={!text.trim()} />
    </>
  );
}
