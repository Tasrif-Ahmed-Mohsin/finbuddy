import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { router } from 'expo-router';
import { useState } from 'react';

import { ThemedText } from '@/components/themed-text';
import { Badge, Banner, Button, Card, ErrorBox, H2, Muted, Row, styles } from '@/components/ui';
import { post, type DocumentResult } from '@/lib/api';
import { cny, localDigits, shortDate } from '@/lib/format';
import { useSession } from '@/lib/session';

/** Photo a fee notice / Chinese form / checklist → explained in the user's language. Nothing is applied without confirmation. */
export function SathiDocument() {
  const { t, lang, call } = useSession();
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<DocumentResult | null>(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function pick(source: 'camera' | 'library') {
    setError(null);
    if (source === 'camera') {
      const perm = await ImagePicker.requestCameraPermissionsAsync();
      if (!perm.granted) {
        setError(t('cameraDenied'));
        return;
      }
    }
    const options: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], base64: true, quality: 0.5 };
    const res = source === 'camera' ? await ImagePicker.launchCameraAsync(options) : await ImagePicker.launchImageLibraryAsync(options);
    if (res.canceled) return;
    const asset = res.assets[0];
    const b64 = asset.base64 ?? (asset.uri.startsWith('data:') ? asset.uri.split(',')[1] : null);
    if (!b64) {
      setError(t('error'));
      return;
    }
    setPreview(asset.uri);
    setResult(null);
    setSaved(false);
    setBusy(true);
    try {
      setResult(await call<DocumentResult>('/documents/read', post({ image_base64: b64, lang })));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function useAsFeeNotice() {
    if (!result?.suggestion) return;
    setError(null);
    try {
      await call('/documents/apply', post({ amount_cny: result.suggestion.amount_cny, deadline: result.suggestion.deadline }));
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  const s = result?.suggestion;
  return (
    <>
      <Card>
        <H2>{t('document')}</H2>
        <Muted>{t('docIntro')}</Muted>
        <Row style={styles.between}>
          <Button title={`📷 ${t('takePhoto')}`} onPress={() => pick('camera')} loading={busy} />
          <Button title={t('choosePhoto')} variant="secondary" onPress={() => pick('library')} disabled={busy} />
        </Row>
        <Banner tone="info">{t('docPrivacy')}</Banner>
      </Card>
      <ErrorBox error={error} />
      {preview && <Image source={{ uri: preview }} style={{ width: '100%', height: 220, borderRadius: 12 }} contentFit="contain" />}
      {busy && <Muted>{t('reading')}</Muted>}

      {result && (
        <>
          <Card>
            <Row style={styles.between}>
              <ThemedText type="smallBold" style={{ flex: 1 }}>
                {result.title}
              </ThemedText>
              <Badge tone="info">{result.doc_type.replace('_', ' ')}</Badge>
            </Row>
            <ThemedText type="small">{lang === 'en' ? result.summary_en : result.summary_local || result.summary_en}</ThemedText>
          </Card>

          {result.flags.length > 0 && (
            <Card tone="block">
              {result.flags.map((f) => (
                <ThemedText key={f.category} type="small">
                  ⚠ {f.advice}
                </ThemedText>
              ))}
            </Card>
          )}

          {(result.amounts.length > 0 || result.deadlines.length > 0) && (
            <Card>
              {result.amounts.map((a, i) => (
                <Row key={`a${i}`} style={styles.between}>
                  <Muted style={{ flex: 1 }}>{a.label}</Muted>
                  <ThemedText type="smallBold">
                    {localDigits(a.amount, lang)} {a.currency ?? ''}
                  </ThemedText>
                </Row>
              ))}
              {result.deadlines.map((d, i) => (
                <Row key={`d${i}`} style={styles.between}>
                  <Muted style={{ flex: 1 }}>{d.label}</Muted>
                  <ThemedText type="smallBold">{d.date ? shortDate(d.date, lang) : d.as_written}</ThemedText>
                </Row>
              ))}
              {result.amounts_dropped > 0 && <Muted>{t('amountsDropped')}</Muted>}
            </Card>
          )}

          {result.checklist.length > 0 && (
            <Card>
              <H2>{t('documentsNeeded')}</H2>
              {result.checklist.map((c, i) => (
                <Row key={i} style={{ alignItems: 'flex-start' }}>
                  <ThemedText type="small">☐</ThemedText>
                  <ThemedText type="small" style={{ flex: 1 }}>
                    {c.english} <Muted>· {c.original}</Muted>
                  </ThemedText>
                </Row>
              ))}
            </Card>
          )}

          {s && !saved && (
            <Card tone="warn">
              <H2>{t('useAsFeeNotice')}</H2>
              <ThemedText type="smallBold">
                {cny(s.amount_cny, lang)} · {t('due')} {shortDate(s.deadline, lang)}
              </ThemedText>
              <Muted>{s.note}</Muted>
              <Button title={t('confirmFeeNotice')} onPress={useAsFeeNotice} />
            </Card>
          )}
          {saved && (
            <Card tone="ok">
              <ThemedText type="smallBold">✓ {t('feeNoticeSaved')}</ThemedText>
              <Button title={t('planIt')} onPress={() => router.push({ pathname: '/plan', params: { mode: 'tuition' } })} />
            </Card>
          )}
          <Muted>{result.privacy}</Muted>
        </>
      )}
    </>
  );
}
