import { useState } from 'react';
import { Share, View } from 'react-native';
import { SvgXml } from 'react-native-svg';

import { ThemedText } from '@/components/themed-text';
import { Badge, Banner, Button, Card, ErrorBox, H1, H2, Muted, Row, Screen, Segmented, styles } from '@/components/ui';
import { post, type Passport } from '@/lib/api';
import { cny, localDigits, num, shortDate } from '@/lib/format';
import { useSession } from '@/lib/session';

type Amounts = 'hide' | 'show';

/** Credit building: a signed, verifiable record of on-time payments made through Bluefin. */
export default function PassportScreen() {
  const { t, lang, call } = useSession();
  const [amounts, setAmounts] = useState<Amounts>('hide');
  const [p, setP] = useState<Passport | null>(null);
  const [valid, setValid] = useState<boolean | null>(null);
  const [revoked, setRevoked] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function create() {
    setBusy(true);
    setError(null);
    setRevoked(false);
    try {
      const doc = await call<Passport>('/passport', post({ include_amounts: amounts === 'show' }));
      setP(doc);
      const v = await call<{ valid: boolean }>('/passport/verify', post({ passport: doc }));
      setValid(v.valid);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function revoke() {
    if (!p) return;
    try {
      await call(`/passport/${p.id}/revoke`, { method: 'POST' });
      setRevoked(true);
      setValid(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function share() {
    if (!p) return;
    const s = p.stats;
    const message = `${p.holder.name} · ${p.holder.university}\nSathi payment passport: on time ${s.on_time}/${s.with_deadline}, ${s.payments} payments, ${s.months_active} months.\nVerify: ${p.verify_url}`;
    try {
      await Share.share({ message });
    } catch {
      // share sheet unavailable (e.g. some browsers): nothing else to do
    }
  }

  return (
    <Screen>
      <H1>{t('passport')}</H1>
      <Muted>{t('passportIntro')}</Muted>
      <Card>
        <Segmented<Amounts> value={amounts} onChange={setAmounts} options={[{ value: 'hide', label: t('hideAmounts') }, { value: 'show', label: t('showAmounts') }]} />
        <Button title={t('createPassport')} onPress={create} loading={busy} />
      </Card>
      <ErrorBox error={error} />

      {p && (
        <>
          <Card tone={valid ? 'ok' : 'block'}>
            <Row style={styles.between}>
              <H2>{p.holder.name}</H2>
              <Badge tone={valid ? 'ok' : 'block'}>{revoked ? t('revokedLabel') : valid ? `✓ ${t('verified')}` : t('notVerified')}</Badge>
            </Row>
            <Muted>
              {p.holder.university} · {p.holder.corridor}
            </Muted>
            <Row style={styles.between}>
              <Stat label={t('onTimeLabel')} value={`${num(p.stats.on_time, lang)}/${num(p.stats.with_deadline, lang)}`} />
              <Stat label={t('paymentsLabel')} value={num(p.stats.payments, lang)} />
              <Stat label={t('monthsLabel')} value={num(p.stats.months_active, lang)} />
            </Row>
            {p.entries.length === 0 && <Muted>{t('noPayments')}</Muted>}
            {p.entries.map((e) => (
              <Row key={e.audit_seq} style={styles.between}>
                <Muted style={{ flex: 1 }}>
                  {shortDate(e.date, lang)} · {e.payee}
                </Muted>
                {e.amount_cny && <ThemedText type="small">{cny(e.amount_cny, lang)}</ThemedText>}
                <Badge tone={e.on_time === false ? 'block' : 'ok'}>
                  {e.on_time === true ? `✓ ${t('onTimeLabel')}` : e.on_time === false ? t('late') : t('completedShort')}
                </Badge>
              </Row>
            ))}
          </Card>

          <Card>
            <H2>{t('scanToVerify')}</H2>
            <View style={{ alignItems: 'center', backgroundColor: '#ffffff', borderRadius: 12, padding: 12 }}>
              <SvgXml xml={p.qr_svg} width={200} height={200} />
            </View>
            <Muted>
              {t('verifyCode')}: {p.signature.slice(0, 12)} · {t('expires')} {shortDate(p.valid_until, lang)}
            </Muted>
            <Row style={styles.between}>
              <Button title={t('share')} onPress={share} />
              <Button title={t('revoke')} variant="secondary" onPress={revoke} disabled={revoked} />
            </Row>
          </Card>
          <Banner tone="info">{p.disclaimer}</Banner>
        </>
      )}
    </Screen>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  const { lang } = useSession();
  return (
    <View style={{ alignItems: 'center', flex: 1 }}>
      <ThemedText style={{ fontSize: 24, fontWeight: '700' }}>{localDigits(value, lang)}</ThemedText>
      <Muted>{label}</Muted>
    </View>
  );
}
