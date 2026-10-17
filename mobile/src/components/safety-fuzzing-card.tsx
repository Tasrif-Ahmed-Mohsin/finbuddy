import Ionicons from '@expo/vector-icons/Ionicons';
import { useCallback, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { BigNumber, Kicker, Panel, SpaceText } from '@/components/neo';
import { Badge, Button, Row } from '@/components/ui';
import { Space, Tone } from '@/constants/theme';
import { post, type FuzzReport } from '@/lib/api';
import { fill, num } from '@/lib/format';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

/**
 * Prove: the safety fuzzer's report. Random honest and hostile steps on the real code with every rule checked after
 * each step; the payments that still went through (it is not just refusing); and the deliberate bugs it caught.
 * "Run 2,000 more" does a live run in its own sandbox.
 */
export function SafetyFuzzingCard() {
  const { t, lang, call } = useSession();
  const [open, setOpen] = useState(false);
  const [live, setLive] = useState<FuzzReport | null>(null);
  const [busy, setBusy] = useState(false);
  const { data: report } = useLoad(useCallback(() => call<FuzzReport>('/security/fuzz-results'), [call]));

  async function runLive() {
    setBusy(true);
    try {
      setLive(await call<FuzzReport>('/security/fuzz/run?iterations=2000', post({})));
    } catch {
      setLive(null);
    } finally {
      setBusy(false);
    }
  }

  if (!report) return null;
  const broken = report.violations_detected;
  const mutants = report.mutants ?? [];
  return (
    <Panel tone={broken ? 'red' : 'blue'}>
      <Row style={{ justifyContent: 'space-between' }}>
        <Kicker dark>{t('fuzzProofKicker')}</Kicker>
        {mutants.length > 0 && (
          <Badge tone={mutants.every((m) => m.caught) ? 'ok' : 'block'} icon="bug">
            {fill(t('fuzzMutantsFmt'), { c: num(mutants.filter((m) => m.caught).length, lang), t: num(mutants.length, lang) })}
          </Badge>
        )}
      </Row>
      <Row style={{ flexWrap: 'nowrap', gap: 16 }}>
        <View style={local.metric}>
          <BigNumber value={report.total_attacks} size={34} color={Space.neon} format={(n) => num(Math.round(n).toLocaleString('en-US'), lang)} />
          <SpaceText muted small>
            {t('fuzzAttacksTested')}
          </SpaceText>
        </View>
        <View style={local.divider} />
        <View style={local.metric}>
          <BigNumber value={broken} size={34} color={broken ? Tone.block.neon : Tone.ok.neon} format={(n) => num(Math.round(n), lang)} />
          <SpaceText muted small>
            {t('fuzzViolationsDetected')}
          </SpaceText>
        </View>
      </Row>
      {report.hostile_steps != null && (
        <SpaceText muted small>
          {fill(t('fuzzHostileFmt'), { h: num(report.hostile_steps.toLocaleString('en-US'), lang) })}
        </SpaceText>
      )}
      {report.payments_completed != null && (
        <SpaceText neon small>
          {fill(t('fuzzLivenessFmt'), { p: num(report.payments_completed, lang) })}
        </SpaceText>
      )}

      <Button title={busy ? t('fuzzRunning') : t('fuzzRunLive')} variant="secondary" icon="flash" loading={busy} onPress={runLive} />
      {live && (
        <SpaceText neon={!live.violations_detected} small>
          {fill(t('fuzzLiveFmt'), { n: num(live.total_attacks.toLocaleString('en-US'), lang), v: num(live.violations_detected, lang), s: num(live.duration_seconds, lang) })}
        </SpaceText>
      )}

      <Pressable onPress={() => setOpen(!open)} style={local.toggle} accessibilityRole="button">
        <SpaceText neon small>
          {open ? t('fuzzHideDetails') : t('fuzzViewDetails')}
        </SpaceText>
        <Ionicons name={open ? 'chevron-up' : 'chevron-down'} size={16} color={Space.neon} />
      </Pressable>
      {open && (
        <View style={{ gap: 10 }}>
          <SpaceText small style={local.heading}>
            {t('fuzzRules')}
          </SpaceText>
          {Object.entries(report.invariant_status).map(([key, v]) => (
            <Row key={key} style={{ flexWrap: 'nowrap', gap: 8, alignItems: 'flex-start' }}>
              <Ionicons name={v.violations ? 'close-circle' : 'checkmark-circle'} size={15} color={v.violations ? Tone.block.neon : Tone.ok.neon} />
              <SpaceText muted small style={{ flex: 1 }}>
                {v.desc}
              </SpaceText>
              <SpaceText neon small>
                {num(v.violations, lang)}
              </SpaceText>
            </Row>
          ))}
          {mutants.map((m) => (
            <Row key={m.mutant} style={{ flexWrap: 'nowrap', gap: 8, alignItems: 'flex-start' }}>
              <Ionicons name="bug" size={15} color={m.caught ? Tone.ok.neon : Tone.block.neon} />
              <SpaceText muted small style={{ flex: 1 }}>
                {m.doc}
              </SpaceText>
              <SpaceText neon small>
                #{num(m.first_seen_at_step ?? 0, lang)}
              </SpaceText>
            </Row>
          ))}
          <SpaceText small style={local.heading}>
            {t('fuzzVectors')}
          </SpaceText>
          <View style={local.pills}>
            {Object.entries(report.attacks_by_vector).map(([vec, count]) => (
              <View key={vec} style={local.pill}>
                <SpaceText muted small>
                  {vec.replace(/_/g, ' ')}
                </SpaceText>
                <SpaceText neon small>
                  {num(count, lang)}
                </SpaceText>
              </View>
            ))}
          </View>
        </View>
      )}
    </Panel>
  );
}

const local = StyleSheet.create({
  metric: { flex: 1, gap: 2 },
  divider: { width: 1, alignSelf: 'stretch', backgroundColor: 'rgba(77, 163, 255, 0.25)' },
  toggle: { flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start', paddingVertical: 4 },
  heading: { fontWeight: '700', letterSpacing: 0.6, color: Space.text },
  pills: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  pill: { flexDirection: 'row', gap: 6, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999, backgroundColor: Space.bg2, borderWidth: 1, borderColor: 'rgba(77, 163, 255, 0.25)' },
});
