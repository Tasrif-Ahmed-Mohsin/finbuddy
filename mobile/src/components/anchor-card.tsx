import Ionicons from '@expo/vector-icons/Ionicons';
import { useCallback } from 'react';
import { StyleSheet, View } from 'react-native';

import { Kicker, Panel, SpaceText } from '@/components/neo';
import { Space, Tone } from '@/constants/theme';
import type { AnchorStatus } from '@/lib/api';
import { fill, num } from '@/lib/format';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

const short = (h: string) => `${h.slice(0, 10)}…${h.slice(-4)}`;

/** Prove: the four-month evidence log's fingerprint (head hash) is written on WeBank's FISCO BCOS chain. The server
 * re-checks it against the chain every minute; a changed log entry would no longer match. Hidden where no anchor exists. */
export function AnchorCard() {
  const { t, lang, call } = useSession();
  const { data } = useLoad(useCallback(() => call<AnchorStatus>('/security/anchor').catch(() => ({ enabled: false }) as AnchorStatus), [call]));
  if (!data || !data.enabled) return null;
  const passed = data.checks.filter((c) => c.ok).length;
  const line = !data.ok
    ? t('anchorBroken')
    : fill(data.live ? t('anchorLive') : t('anchorOffline'), { n: num(passed, lang), t: num(data.checks.length, lang) });
  return (
    <Panel tone={data.ok ? 'blue' : 'red'}>
      <Kicker dark>{`${data.network.name} ${data.network.version}`.trim()}</Kicker>
      <View style={local.row}>
        <View style={local.icon}>
          <Ionicons name={data.ok ? 'link' : 'warning'} size={24} color={data.ok ? Space.neon : Tone.block.neon} />
        </View>
        <View style={{ flex: 1, gap: 2 }}>
          <SpaceText neon={data.ok} style={local.title}>
            {t('anchorTitle')}
          </SpaceText>
          <SpaceText muted small>
            {line}
          </SpaceText>
        </View>
      </View>
      <SpaceText muted small>
        {t('anchorExplain')}
      </SpaceText>
      <SpaceText small style={local.mono}>
        {`${t('anchorBlock')} ${num(data.block, lang)} · ${t('anchorTx')} ${short(data.transaction)}\n${t('anchorHead')} ${short(data.anchored_head)} · ${num(data.entries, lang)} ${t('proofEntries')}`}
      </SpaceText>
    </Panel>
  );
}

const local = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  icon: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center', backgroundColor: Space.bg2 },
  title: { fontSize: 17, lineHeight: 22, fontWeight: '700' },
  mono: { fontFamily: 'monospace', color: Space.text, opacity: 0.85, fontSize: 12, lineHeight: 18 },
});
