import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { useCallback } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { BuddyBubble, BuddyLoading } from '@/components/buddy';
import { DataBanner } from '@/components/data-banner';
import type { MascotMood } from '@/components/mascot';
import { Battery, BigNumber, Bento, DayStrip, Kicker, LiquidCapsule, Panel, RingGauge, RoundButton, RouteBeam, Seal, SectionHeader, SpaceText, Tile, useBentoColumn, type DayInfo } from '@/components/neo';
import { NeedCard, NoteCard } from '@/components/note-card';
import { InsightCard } from '@/components/sathi-updates';
import { ThemedText } from '@/components/themed-text';
import { ErrorBox, H1, Muted, Row, Screen, Segmented } from '@/components/ui';
import { Brand, Space } from '@/constants/theme';
import type { BanksView, Feed, FxOverview, Insight, Role, Timeline, ValueSummary } from '@/lib/api';
import { cny, fill, localDigits, num, shortDate } from '@/lib/format';
import type { Lang, StringKey } from '@/lib/i18n';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

/**
 * Home, the mission-control dashboard. Hero: how many days of money the student has. Then the money route,
 * the bank days in both countries, Bluefin, the card, the live rate and the black box. Then what needs you.
 */
export default function HomeScreen() {
  const { t, lang, role, setRole, call } = useSession();
  const { data, error, loading, reload } = useLoad(
    useCallback(async () => {
      const [feed, ins, timeline, week, fx, audit, value] = await Promise.all([
        call<Feed>(`/feed?lang=${lang}`),
        call<{ insights: Insight[] }>(`/insights?lang=${lang}`),
        call<Timeline>('/timeline'),
        call<DayInfo[]>('/calendar/week'),
        call<FxOverview>('/fx'),
        call<{ verify: { valid: boolean; entries: number } }>('/audit?limit=1'),
        call<ValueSummary>('/value'),
      ]);
      return { feed, insights: ins.insights, timeline, week, fx, verify: audit.verify, value };
    }, [call, lang]),
  );

  const needs = data?.feed.needs_you ?? [];
  const notes = data?.feed.notes ?? [];
  const hello = data ? greeting(data.feed, needs.length, t, lang) : null;
  const weekday = (iso: string) => weekdayName(iso, lang);

  return (
    <Screen refreshing={loading} onRefresh={reload} wide>
      <View style={local.header}>
        <View style={{ flex: 1 }}>
          <Kicker>{t(partOfDay())}</Kicker>
          <H1>{t('appName')}</H1>
        </View>
        <RoundButton icon="alert" tone="danger" label={t('emergencyLink')} onPress={() => router.push('/emergency')} />
        <RoundButton icon="settings-outline" label={t('settingsLink')} onPress={() => router.push('/settings')} />
      </View>
      <Segmented<Role>
        value={role}
        onChange={setRole}
        options={[
          { value: 'parent', label: t('parent') },
          { value: 'student', label: t('student') },
        ]}
      />
      <Muted style={{ textAlign: 'center' }}>{t('roleHint')}</Muted>
      <Pressable accessibilityRole="button" accessibilityLabel={t('storyTileTitle')} onPress={() => router.push('/story')}>
        <Panel>
          <Row style={{ flexWrap: 'nowrap', gap: 12 }}>
            <View style={local.play}>
              <Ionicons name="play" size={22} color="#FFFFFF" />
            </View>
            <View style={{ flex: 1, gap: 2 }}>
              <SpaceText style={local.storyTitle}>{t('storyTileTitle')}</SpaceText>
              <SpaceText muted small>
                {t('storyTileBody')}
              </SpaceText>
            </View>
            <Ionicons name="chevron-forward" size={20} color={Space.neon} />
          </Row>
        </Panel>
      </Pressable>
      <ErrorBox error={error} />
      {!data && loading && <BuddyLoading text={t('todayLoading')} />}

      {data && (
        <>
          <Bento>
            <HeroTile feed={data.feed} />
            <ValueTile v={data.value} />
            <RouteTile feed={data.feed} />
            <Tile span={2}>
              <Row style={{ justifyContent: 'space-between' }}>
                <Kicker>{t('bankDaysKicker')}</Kicker>
                <Row style={{ gap: 10 }}>
                  <Legend color="#3DDC97" label={t('bankOpen')} />
                  <Legend color="#FF5C5C" label={t('bankClosed')} />
                </Row>
              </Row>
              <DayStrip days={data.week} weekday={weekday} />
              <Muted>{t('bankDaysLegend')}</Muted>
            </Tile>
            <Tile span={2} style={local.buddyTile}>
              {hello && <BuddyBubble mood={hello.mood} title={t('sathiHello')} text={hello.text} size={96} onPressMascot={() => router.push('/buddy')} />}
            </Tile>
            <CardDialTile timeline={data.timeline} />
            <Tile label={t('rateKicker')}>
              <Kicker>{t('rateKicker')}</Kicker>
              <View style={local.globe}>
                <Ionicons name="globe-outline" size={30} color={Brand.ink} />
              </View>
              <ThemedText display style={local.rate}>
                ৳{localDigits(Number(data.fx.mid.bdt_per_cny).toFixed(2), lang)}
              </ThemedText>
              <Muted>{fill(t('rateAsOfFmt'), { date: shortDate(data.fx.mid.as_of, lang) })}</Muted>
            </Tile>
            <Tile span={hasBattery(data.feed) ? 1 : 2} label={t('sealKicker')} onPress={() => router.push({ pathname: '/family', params: { pane: 'proof' } })}>
              <Kicker>{t('sealKicker')}</Kicker>
              <View style={hasBattery(data.feed) ? local.sealCol : local.sealRow}>
                <Seal ok={data.verify.valid} size={68} />
                <View style={{ gap: 2, alignItems: hasBattery(data.feed) ? 'center' : 'flex-start' }}>
                  <ThemedText type="smallBold">{data.verify.valid ? t('sealOk') : t('sealBad')}</ThemedText>
                  <Muted>
                    {num(data.verify.entries, lang)} {t('proofEntries')}
                  </Muted>
                </View>
              </View>
            </Tile>
            <BatteryTile feed={data.feed} />
            <BanksTile />
          </Bento>

          {needs.length > 0 && (
            <>
              <SectionHeader kicker={t('actionKicker')} title={t('needsYou')} />
              {needs.map((n) => (
                <NeedCard
                  key={n.type === 'sign_mandate' ? n.proposal_id : n.type === 'confirm_safe' ? n.check_id : n.type === 'approve_release' ? n.release_id : n.draft_id}
                  need={n}
                />
              ))}
            </>
          )}
          <SectionHeader kicker={t('feedKicker')} title={t('whatSathiDid')} />
          {notes.length === 0 && <Muted>{t('nothingYet')}</Muted>}
          {notes.slice(0, 6).map((n) => (
            <NoteCard key={n.id} note={n} />
          ))}
          {data.insights.length > 0 && (
            <>
              <SectionHeader kicker={t('inboxKicker')} title={t('alertsFromMessages')} />
              {data.insights.slice(0, 3).map((i) => (
                <InsightCard key={i.id} insight={i} onChanged={reload} />
              ))}
            </>
          )}
          <DataBanner dq={data.timeline.data_quality} />
          <ThemedText type="small" themeColor="textSecondary" style={local.tip}>
            {t('homeTip')}
          </ThemedText>
        </>
      )}
    </Screen>
  );
}

/** Hero: the days of money as a big thin numeral, beside a fuel capsule filled to a month. */
function HeroTile({ feed }: { feed: Feed }) {
  const { t, lang } = useSession();
  const r = feed.runway;
  const days = r.days_left ?? 0;
  const pct = Math.min(days / 30, 1);
  const next = r.in_transit[0];
  return (
    <Tile span={2} style={local.hero}>
      <View style={{ flex: 1, gap: 4 }}>
        <Kicker>{t('homeMoneyKicker')}</Kicker>
        <Row style={{ alignItems: 'flex-end', gap: 8, flexWrap: 'nowrap' }}>
          <BigNumber value={days} size={92} format={(n) => num(Math.round(n), lang)} />
          <Kicker style={{ marginBottom: 18 }}>{t('homeDays')}</Kicker>
        </Row>
        <ThemedText display style={local.heroBalance}>
          {cny(r.balance_cny, lang)}
        </ThemedText>
        <Muted>
          {next
            ? fill(t('homeNextLandsFmt'), { amount: cny(next.amount_cny, lang), date: shortDate(next.arrives, lang) })
            : r.runs_out_on
              ? fill(t('homeRunsOutFmt'), { date: shortDate(r.runs_out_on, lang) })
              : ''}
        </Muted>
      </View>
      <LiquidCapsule pct={pct} value={`${localDigits(String(Math.round(pct * 100)), lang)}%`} label={t('capsuleLabel')} width={84} height={176} />
    </Tile>
  );
}

/** Value delivered, in three numbers: days without money avoided, money saved this year, unsafe moves stopped. */
function ValueTile({ v }: { v: ValueSummary }) {
  const { t, lang } = useSession();
  return (
    <Tile span={2} label={t('valueKicker')} onPress={() => router.push('/judge')}>
      <Kicker>{t('valueKicker')}</Kicker>
      <View style={local.valueRow}>
        <View style={local.valueCell}>
          <ThemedText display style={local.valueBig}>
            {num(v.stuck_days_today, lang)}
            <ThemedText display style={[local.valueBig, { color: Brand.primary }]}>
              {' → '}
              {num(v.stuck_days_sathi, lang)}
            </ThemedText>
          </ThemedText>
          <Muted>{t('valueStuck')}</Muted>
        </View>
        <View style={local.valueCell}>
          <ThemedText display style={local.valueBig}>
            ৳{localDigits(Math.round(Number(v.saved_bdt)).toLocaleString('en-IN'), lang)}
          </ThemedText>
          <Muted>{t('valueSaved')}</Muted>
        </View>
        <View style={local.valueCell}>
          <ThemedText display style={local.valueBig}>
            {num(v.stopped + v.flagged_messages, lang)}
          </ThemedText>
          <Muted>{t('valueStopped')}</Muted>
        </View>
      </View>
    </Tile>
  );
}

/** The money route: a rocket glides from Bangladesh to China while a transfer is on the way. */
function RouteTile({ feed }: { feed: Feed }) {
  const { t, lang } = useSession();
  const r = feed.runway;
  const next = r.in_transit[0];
  return (
    <Tile span={2}>
      <Row style={{ justifyContent: 'space-between' }}>
        <Kicker>{t('routeKicker')}</Kicker>
        <Kicker color={r.mandate ? Brand.primary : undefined}>{r.mandate ? t('autopilotOn') : t('autopilotShortOff')}</Kicker>
      </Row>
      <RouteBeam moving={!!next} />
      <ThemedText type="small">
        {next
          ? fill(t('routeMovingFmt'), { amount: cny(next.amount_cny, lang), date: shortDate(next.arrives, lang) })
          : r.mandate
            ? t('routeIdleOn')
            : t('routeIdleOff')}
      </ThemedText>
    </Tile>
  );
}

/** How long the Bangladeshi card still works abroad, as a neon dial. */
function CardDialTile({ timeline }: { timeline: Timeline }) {
  const { t, lang } = useSession();
  const col = useBentoColumn();
  const item = timeline.items.find((i) => i.type === 'endorsement_expiry');
  const left = Math.max(item?.days_left ?? 0, 0);
  return (
    <Tile label={t('cardKicker')} onPress={() => router.push({ pathname: '/family', params: { pane: 'cards' } })} style={{ alignItems: 'center' }}>
      <Kicker style={{ alignSelf: 'flex-start' }}>{t('cardKicker')}</Kicker>
      <RingGauge
        pct={Math.min(left / 90, 1)}
        value={num(left, lang)}
        label={t('cardDaysLabel')}
        sub={item?.due ? shortDate(item.due, lang) : undefined}
        size={Math.min(Math.max(col - 32, 120), 170)}
      />
    </Tile>
  );
}

function hasBattery(feed: Feed): boolean {
  return !!feed.shield || !!feed.runway.mandate;
}

/** The Shield (the student's own savings) as a battery, or the autopilot's budget left this month. */
/** Sense: the bank connections (read-only, with consent). One line: connected and how often Bluefin read it, or how to connect. */
function BanksTile() {
  const { t, lang, call } = useSession();
  const { data } = useLoad(useCallback(() => call<BanksView>('/banks'), [call]));
  const active = data?.connectors.find((c) => c.active)?.active ?? null;
  return (
    <Tile span={2} label={t('settingsBanks')} onPress={() => router.push('/banks')}>
      <Row style={{ flexWrap: 'nowrap', gap: 12 }}>
        <View style={local.bankIcon}>
          <Ionicons name="business" size={22} color={Space.neon} />
        </View>
        <View style={{ flex: 1, gap: 2 }}>
          <Kicker>{t('banksKicker')}</Kicker>
          <ThemedText type="smallBold">
            {active ? `${active.bank} · ${t('status_Authorised')}` : t('banksTileConnect')}
          </ThemedText>
          <Muted>
            {active
              ? `${fill(t('banksReads'), { n: num(active.reads, lang) })} · ${fill(t('banksDaysLeft'), { d: num(active.days_left, lang) })}`
              : t('banksNeverPay')}
          </Muted>
        </View>
        <Ionicons name="chevron-forward" size={18} color={Brand.ink} />
      </Row>
    </Tile>
  );
}

function BatteryTile({ feed }: { feed: Feed }) {
  const { t, lang } = useSession();
  const s = feed.shield;
  const m = feed.runway.mandate;
  if (s) {
    return (
      <Tile span={2} onPress={() => router.push('/save')} label={t('shieldTitle')}>
        <Battery icon="shield-half" pct={s.pct_of_target / 100} label={t('shieldTitle')} value={`${cny(s.balance_cny, lang)} · ${localDigits(String(s.pct_of_target), lang)}%`} />
      </Tile>
    );
  }
  if (m) {
    const left = Number(m.left_in_period_bdt);
    const cap = Number(m.max_bdt_per_period);
    return (
      <Tile span={2} onPress={() => router.push('/family')} label={t('budgetLeft')}>
        <Battery icon="flash" pct={cap ? left / cap : 0} label={t('budgetLeft')} value={`৳${localDigits(Math.round(left).toLocaleString('en-IN'), lang)}`} />
      </Tile>
    );
  }
  return null;
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <Row style={{ gap: 4 }}>
      <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: color }} />
      <ThemedText style={{ fontSize: 11, lineHeight: 14, color: '#5F6470' }}>{label}</ThemedText>
    </Row>
  );
}

function partOfDay(): StringKey {
  const h = new Date().getHours();
  return h < 12 ? 'homeMorning' : h < 17 ? 'homeAfternoon' : 'homeEvening';
}

const WEEKDAYS: Record<Lang, string[]> = {
  en: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
  bn: ['রবি', 'সোম', 'মঙ্গল', 'বুধ', 'বৃহঃ', 'শুক্র', 'শনি'],
  zh: ['周日', '周一', '周二', '周三', '周四', '周五', '周六'],
};

function weekdayName(iso: string, lang: Lang): string {
  const [y, m, d] = iso.split('-').map(Number);
  return WEEKDAYS[lang][new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
}

/** What Bluefin says first: what needs you, then money running low, then all is well. */
function greeting(feed: Feed, needs: number, t: (k: StringKey) => string, lang: Lang): { mood: MascotMood; text: string } {
  const r = feed.runway;
  const days = num(r.days_left ?? 0, lang);
  const covered = r.in_transit.length > 0 || !!r.mandate;
  if (needs > 0) return { mood: 'curious', text: needs === 1 ? t('todayNeedsOne') : fill(t('todayNeedsFmt'), { n: num(needs, lang) }) };
  if ((r.days_left ?? 0) < 5 && !covered && r.runs_out_on) {
    return { mood: 'worried', text: fill(t('todayLowFmt'), { date: shortDate(r.runs_out_on, lang) }) };
  }
  if (r.mandate) return { mood: 'happy', text: fill(t('todayCoveredFmt'), { days }) };
  return { mood: 'idle', text: fill(t('todayCalmFmt'), { days }) };
}

const local = StyleSheet.create({
  play: { width: 44, height: 44, borderRadius: 22, backgroundColor: Brand.primary, alignItems: 'center', justifyContent: 'center', boxShadow: '0px 0px 14px rgba(77, 163, 255, 0.6)' },
  storyTitle: { fontSize: 17, lineHeight: 22, fontWeight: '700' },
  bankIcon: { width: 44, height: 44, borderRadius: 14, backgroundColor: Space.bg, alignItems: 'center', justifyContent: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  hero: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  heroBalance: { fontSize: 24, lineHeight: 30, fontWeight: '600' },
  buddyTile: { paddingVertical: 12 },
  globe: {
    width: 54,
    height: 54,
    borderRadius: 27,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 4,
    backgroundColor: '#EEF0F4',
    boxShadow: '-3px -3px 8px rgba(255,255,255,0.92), 3px 3px 8px rgba(163,170,184,0.45)',
  },
  rate: { fontSize: 26, lineHeight: 32, fontWeight: '600' },
  valueRow: { flexDirection: 'row', gap: 10 },
  valueCell: { flex: 1, gap: 2 },
  valueBig: { fontSize: 22, lineHeight: 28, fontWeight: '600' },
  sealCol: { alignItems: 'center', gap: 8, paddingVertical: 6 },
  sealRow: { flexDirection: 'row', alignItems: 'center', gap: 16, paddingVertical: 4 },
  tip: { textAlign: 'center', fontStyle: 'italic', marginTop: 8, color: Space.muted },
});
