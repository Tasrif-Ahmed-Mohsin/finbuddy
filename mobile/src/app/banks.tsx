import Ionicons from '@expo/vector-icons/Ionicons';
import { useCallback, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Kicker, Panel, SpaceText } from '@/components/neo';
import { ThemedText } from '@/components/themed-text';
import { Badge, Banner, Button, Card, Chip, ErrorBox, H1, H2, Muted, Row, Screen } from '@/components/ui';
import { Space } from '@/constants/theme';
import { post, type BankConsent, type BankRead, type BanksView } from '@/lib/api';
import { fill, num, shortDate } from '@/lib/format';
import type { StringKey } from '@/lib/i18n';
import { signWithPasskey } from '@/lib/passkey';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

const FLAG: Record<string, string> = { BD: '🇧🇩', CN: '🇨🇳' };
const STATUS_TONE = { Authorised: 'ok', Revoked: 'neutral', Expired: 'warn', AwaitingAuthorisation: 'info' } as const;

/**
 * Connected banks (open banking, read-only): the account holder allows Bluefin to read balances for up to 90 days,
 * signed with their passkey, and can revoke it at any time. Bluefin can never pay through a connection.
 */
export default function BanksScreen() {
  const { t, lang, role, call } = useSession();
  const { data, error, reload } = useLoad(useCallback(() => call<BanksView>('/banks'), [call]));
  const [picking, setPicking] = useState<string | null>(null);
  const [perms, setPerms] = useState<string[]>(['ReadAccountsBasic', 'ReadBalances']);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [reads, setReads] = useState<Record<string, BankRead>>({});

  async function act(fn: () => Promise<void>) {
    setBusy(true);
    setErr(null);
    try {
      await fn();
      reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const allow = (connector: string) =>
    act(async () => {
      const c = await call<BankConsent>('/banks/consents', post({ connector, permissions: perms, days: 90 }));
      const assertion = await signWithPasskey(role, c.hash, `${t('banksAllow')}: ${c.bank}`, call);
      if (!assertion) return;
      await call(`/banks/consents/${c.id}/authorise`, post({ assertion }));
      setPicking(null);
    });
  const revoke = (id: string) => act(async () => void (await call(`/banks/consents/${id}`, { method: 'DELETE' })));
  const read = (connector: string) =>
    act(async () => {
      const r = await call<BankRead>(`/banks/${connector}/accounts`);
      setReads((m) => ({ ...m, [connector]: r }));
    });

  const history = (data?.consents ?? []).filter((c) => c.status !== 'Authorised');
  return (
    <Screen>
      <Kicker>{t('banksKicker')}</Kicker>
      <H1>{t('banksTitle')}</H1>
      <Muted>{t('banksIntro')}</Muted>
      <ErrorBox error={error ?? err} />

      {data?.connectors.map((c) => {
        const active = c.active;
        const r = reads[c.id];
        return (
          <Panel key={c.id}>
            <Row style={{ flexWrap: 'nowrap', gap: 12 }}>
              <View style={local.flag}>
                <ThemedText style={{ fontSize: 26, lineHeight: 32 }}>{FLAG[c.country]}</ThemedText>
              </View>
              <View style={{ flex: 1, gap: 2 }}>
                <SpaceText style={local.bank}>{c.bank}</SpaceText>
                <SpaceText muted small>
                  {t('banksStandard')}: {c.standard}
                </SpaceText>
              </View>
              {active && <Badge tone="ok">{t('status_Authorised')}</Badge>}
            </Row>
            <Row style={{ gap: 6 }}>
              <Ionicons name="lock-closed" size={14} color={Space.neon} />
              <SpaceText neon small>
                {t('banksNeverPay')}
              </SpaceText>
            </Row>

            {active ? (
              <>
                {active.permissions.map((p) => (
                  <SpaceText key={p.id} muted small>
                    ✓ {t(`perm_${p.id}` as StringKey)}
                  </SpaceText>
                ))}
                <SpaceText muted small>
                  {fill(t('banksDaysLeft'), { d: num(active.days_left, lang) })} · {fill(t('banksReads'), { n: num(active.reads, lang) })}
                </SpaceText>
                {r?.Data.Account.map((a) => (
                  <Card key={a.AccountId}>
                    <Row style={{ justifyContent: 'space-between' }}>
                      <ThemedText type="smallBold">{a.Nickname}</ThemedText>
                      <ThemedText display style={local.amount}>
                        {a.Balance ? `${num(Number(a.Balance.Amount.Amount).toLocaleString('en-US', { maximumFractionDigits: 2 }), lang)} ${a.Balance.Amount.Currency}` : '—'}
                      </ThemedText>
                    </Row>
                    <Muted>
                      {t('banksBalance')} · {r.consent_id}
                    </Muted>
                  </Card>
                ))}
                <Row style={{ gap: 8 }}>
                  <Button title={t('banksRead')} icon="eye" variant="secondary" onPress={() => read(c.id)} loading={busy} />
                  {c.yours && <Button title={t('banksRevoke')} icon="close-circle" variant="secondary" onPress={() => revoke(active.id)} disabled={busy} />}
                </Row>
              </>
            ) : c.yours ? (
              picking === c.id ? (
                <>
                  <SpaceText small style={local.heading}>
                    {t('banksAllowTitle')}
                  </SpaceText>
                  <Row style={{ gap: 6 }}>
                    {(data?.permissions ?? []).map((p) => (
                      <Chip
                        key={p.id}
                        label={t(`perm_${p.id}` as StringKey)}
                        selected={perms.includes(p.id)}
                        onPress={() =>
                          p.id !== 'ReadAccountsBasic' &&
                          setPerms((x) => (x.includes(p.id) ? x.filter((y) => y !== p.id) : [...x, p.id]))
                        }
                      />
                    ))}
                  </Row>
                  <SpaceText muted small>
                    {fill(t('banksForDays'), { d: num(data?.max_days ?? 90, lang) })}
                  </SpaceText>
                  <Button title={t('banksAllow')} icon="finger-print" onPress={() => allow(c.id)} loading={busy} />
                </>
              ) : (
                <Button title={t('banksConnect')} icon="link" onPress={() => setPicking(c.id)} />
              )
            ) : (
              <SpaceText muted small>
                {fill(t('banksNotYours'), { who: t(c.holder) })}
              </SpaceText>
            )}
          </Panel>
        );
      })}

      {history.length > 0 && (
        <Card>
          <H2 icon="time">{t('banksHistory')}</H2>
          {history.map((c) => (
            <Row key={c.id} style={{ justifyContent: 'space-between' }}>
              <Muted>
                {c.bank} · {shortDate(c.created_at, lang)}
              </Muted>
              <Badge tone={STATUS_TONE[c.status]}>{t(`status_${c.status}` as StringKey)}</Badge>
            </Row>
          ))}
        </Card>
      )}
      <Banner tone="info">{t('banksSimulated')}</Banner>
    </Screen>
  );
}

const local = StyleSheet.create({
  flag: { width: 48, height: 48, borderRadius: 16, backgroundColor: Space.bg2, alignItems: 'center', justifyContent: 'center' },
  bank: { fontSize: 17, lineHeight: 22, fontWeight: '600' },
  heading: { fontWeight: '700', color: Space.text },
  amount: { fontSize: 18, lineHeight: 24, fontWeight: '600' },
});
