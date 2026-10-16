import { router } from 'expo-router';
import { useState } from 'react';

import { ThemedText } from '@/components/themed-text';
import { Badge, Button, Card, ErrorBox, Muted, Row, styles } from '@/components/ui';
import { post, type Draft, type NeedItem, type Note } from '@/lib/api';
import { bdt, cny, shortDate } from '@/lib/format';
import { useSession } from '@/lib/session';

const TONE = { did: 'ok', needs_you: 'warn', warning: 'block', info: 'info' } as const;
const ICON = { did: '🤖', needs_you: '✋', warning: '⚠️', info: 'ℹ️' } as const;

/** One entry of the family feed: what Sathi did, saw, or needs. Text comes from server templates in the user's language. */
export function NoteCard({ note }: { note: Note }) {
  const { t, lang, call } = useSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const r = note.ref;

  async function prepareTopup() {
    if (!r.amount_cny) return;
    setBusy(true);
    setError(null);
    try {
      // A fresh draft with a fresh rate quote: the family approves it with fingerprint on the next screen.
      const d = await call<Draft>('/drafts', post({ kind: 'tt_living', amount_cny: r.amount_cny, payee_id: 'student_own_cn', memo: 'Living money' }));
      router.push({ pathname: '/draft/[id]', params: { id: d.id } });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card tone={TONE[note.kind]}>
      <Row style={styles.between}>
        <ThemedText type="smallBold" style={{ flex: 1 }}>
          {ICON[note.kind]} {note.title}
        </ThemedText>
        <Muted>{shortDate(note.at, lang)}</Muted>
      </Row>
      <ThemedText type="small">{note.body}</ThemedText>
      {r.screen === 'topup' && <Button title={t('prepareTopup')} onPress={prepareTopup} loading={busy} />}
      {r.screen === 'draft' && r.draft_id && (
        <Button title={t('open')} variant="secondary" onPress={() => router.push({ pathname: '/draft/[id]', params: { id: r.draft_id! } })} />
      )}
      {r.screen === 'family' && note.kind !== 'info' && <Button title={t('tabFamily')} variant="secondary" onPress={() => router.push('/family')} />}
      {r.screen === 'emergency' && <Button title={t('emergencyLink')} variant="secondary" onPress={() => router.push('/emergency')} />}
      {r.screen === 'save' && note.kind !== 'info' && <Button title={t('openSave')} variant="secondary" onPress={() => router.push('/save')} />}
      {r.screen === 'renewal' && r.item && (
        <Button title={t('openRenewal')} variant="secondary" onPress={() => router.push({ pathname: '/renewal/[item]', params: { item: r.item! } })} />
      )}
      <ErrorBox error={error} />
    </Card>
  );
}

/** Something waiting for THIS person: approve or send a payment, or co-sign the family mandate. */
export function NeedCard({ need }: { need: NeedItem }) {
  const { t, lang } = useSession();
  if (need.type === 'confirm_safe') {
    return (
      <Card tone="warn">
        <ThemedText type="smallBold">🙋 {t('safeCheckNeed')}</ThemedText>
        <Button title={t('emImSafe')} onPress={() => router.push('/emergency')} />
      </Card>
    );
  }
  if (need.type === 'approve_release') {
    return (
      <Card tone="warn">
        <Row style={styles.between}>
          <ThemedText type="smallBold" style={{ flex: 1 }}>
            🛡️ {t('releaseNeedsYou')}
          </ThemedText>
          <Badge tone="warn">{cny(need.amount_cny, lang)}</Badge>
        </Row>
        <Button title={t('openSave')} onPress={() => router.push('/save')} />
      </Card>
    );
  }
  if (need.type === 'sign_mandate') {
    return (
      <Card tone="warn">
        <ThemedText type="smallBold">✍️ {t('signMandate')}</ThemedText>
        <ThemedText type="small" numberOfLines={3}>
          {need.summary}
        </ThemedText>
        <Button title={t('signMandate')} onPress={() => router.push('/family')} />
      </Card>
    );
  }
  return (
    <Card tone="warn">
      <Row style={styles.between}>
        <ThemedText type="smallBold" style={{ flex: 1 }}>
          {need.payee_name}
        </ThemedText>
        <Badge tone="warn">{cny(need.amount_cny, lang)}</Badge>
      </Row>
      <Muted>{bdt(need.total_bdt, lang)}</Muted>
      <Button
        title={need.type === 'approve_draft' ? t('approvePayment') : t('sendPayment')}
        onPress={() => router.push({ pathname: '/draft/[id]', params: { id: need.draft_id } })}
      />
    </Card>
  );
}
