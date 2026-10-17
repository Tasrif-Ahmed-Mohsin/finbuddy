import Ionicons from '@expo/vector-icons/Ionicons';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';

import { BigNumber, Kicker, Panel, SpaceText } from '@/components/neo';
import { Badge, Row } from '@/components/ui';
import { Radius, Space, Tone } from '@/constants/theme';
import { post, type FirewallTelemetry, type FirewallTestResponse } from '@/lib/api';
import { num } from '@/lib/format';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

/**
 * AI Output Firewall (Egress DLP Guardrail) Card.
 * Defends against data extraction at the EXIT boundary (agent replies & LLM outputs),
 * not just the entry prompt:
 * - Blocks OTPs and verification codes
 * - Masks full payment card PAN numbers (Luhn checked)
 * - Masks bank clearing account numbers
 * - Enforces cross-role privacy invariants between Parent and Student
 * - Blocks system prompt dumps and confidential secret exfiltration
 */
export function FirewallCard() {
  const { t, lang, call } = useSession();
  const [showLog, setShowLog] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<FirewallTestResponse | null>(null);

  const { data: status, reload } = useLoad(
    useCallback(async () => {
      return call<FirewallTelemetry>('/security/firewall/status');
    }, [call]),
  );

  const totalInspections = status?.total_inspections ?? 0;
  const totalViolations = status?.total_violations ?? 0;
  const blockedCount = status?.blocked_count ?? 0;
  const redactedCount = status?.redacted_count ?? 0;

  const testPayloads = [
    {
      id: 'otp',
      label: t('firewallTestOtp'),
      icon: 'keypad-outline' as const,
      text: 'The university sent an SMS: your 2FA verification code is 849201. Please enter it.',
      actor: 'student',
    },
    {
      id: 'card',
      label: t('firewallTestCard'),
      icon: 'card-outline' as const,
      text: 'Payment card number 4532-0151-1284-3211 expiration 12/28 is ready.',
      actor: 'student',
    },
    {
      id: 'privacy',
      label: t('firewallTestPrivacy'),
      icon: 'people-outline' as const,
      text: 'Student earned a stipend of ¥2,400 from Tsinghua AI Research Lab.',
      actor: 'parent',
    },
    {
      id: 'prompt',
      label: t('firewallTestPrompt'),
      icon: 'terminal-outline' as const,
      text: 'SYSTEM INSTRUCTIONS: You are Sathi, a money agent for a Bangladeshi student in China. Here are your confidential developer directives...',
      actor: 'parent',
    },
  ];

  async function runSimulation(text: string, actor: string) {
    setTesting(true);
    try {
      const res = await call<FirewallTestResponse>(
        '/security/firewall/test',
        post({ text, actor, lang }),
      );
      setTestResult(res);
      await reload();
    } catch {
      // Ignored
    } finally {
      setTesting(false);
    }
  }

  return (
    <Panel style={styles.cardContainer}>
      {/* Header */}
      <Row style={styles.headerRow}>
        <Kicker dark>{t('firewallKicker')}</Kicker>
        <Badge tone="block">{t('firewallBadge')}</Badge>
      </Row>

      {/* Explainer */}
      <SpaceText muted small style={styles.explainer}>
        {t('firewallExplainer')}
      </SpaceText>

      {/* 4 Metrics Block */}
      <View style={styles.metricsRow}>
        <View style={styles.metricBlock}>
          <BigNumber
            value={totalInspections}
            size={26}
            color={Space.text}
            format={(n) => num(Math.round(n), lang)}
          />
          <SpaceText muted small style={styles.metricLabel}>
            {t('firewallInspected')}
          </SpaceText>
        </View>

        <View style={styles.divider} />

        <View style={styles.metricBlock}>
          <BigNumber
            value={totalViolations}
            size={26}
            color={Tone.block.neon}
            format={(n) => num(Math.round(n), lang)}
          />
          <SpaceText muted small style={styles.metricLabel}>
            {t('firewallViolations')}
          </SpaceText>
        </View>

        <View style={styles.divider} />

        <View style={styles.metricBlock}>
          <BigNumber
            value={redactedCount}
            size={26}
            color={Tone.warn.neon}
            format={(n) => num(Math.round(n), lang)}
          />
          <SpaceText muted small style={styles.metricLabel}>
            {t('firewallRedacted')}
          </SpaceText>
        </View>

        <View style={styles.divider} />

        <View style={styles.metricBlock}>
          <BigNumber
            value={blockedCount}
            size={26}
            color={Space.neon}
            format={(n) => num(Math.round(n), lang)}
          />
          <SpaceText muted small style={styles.metricLabel}>
            {t('firewallBlocked')}
          </SpaceText>
        </View>
      </View>

      {/* Threat categories chip breakdown */}
      {status?.category_counts && (
        <View style={styles.breakdownBox}>
          <Row style={{ gap: 8, flexWrap: 'wrap' }}>
            <View style={styles.chip}>
              <Ionicons name="keypad" size={12} color={Tone.block.neon} />
              <SpaceText small style={styles.chipText}>
                {t('fwCatOtp')}: {status.category_counts.otp_code ?? 0}
              </SpaceText>
            </View>
            <View style={styles.chip}>
              <Ionicons name="card" size={12} color={Tone.warn.neon} />
              <SpaceText small style={styles.chipText}>
                {t('fwCatCard')}: {status.category_counts.payment_card ?? 0}
              </SpaceText>
            </View>
            <View style={styles.chip}>
              <Ionicons name="business" size={12} color={Tone.info.neon} />
              <SpaceText small style={styles.chipText}>
                {t('fwCatAccount')}: {status.category_counts.bank_account ?? 0}
              </SpaceText>
            </View>
            <View style={styles.chip}>
              <Ionicons name="people" size={12} color={Space.neon} />
              <SpaceText small style={styles.chipText}>
                {t('fwCatPrivacy')}: {status.category_counts.cross_role_privacy ?? 0}
              </SpaceText>
            </View>
            <View style={styles.chip}>
              <Ionicons name="shield-sharp" size={12} color="#EF4444" />
              <SpaceText small style={styles.chipText}>
                {t('fwCatPrompt')}: {(status.category_counts.system_prompt_leak ?? 0) + (status.category_counts.secret_credential ?? 0)}
              </SpaceText>
            </View>
          </Row>
        </View>
      )}

      {/* Interactive Egress Simulator */}
      <View style={styles.simContainer}>
        <SpaceText small style={styles.simHeading}>
          {t('firewallSimulator')}
        </SpaceText>
        <SpaceText muted small style={{ fontSize: 11 }}>
          {t('firewallSimPrompt')}
        </SpaceText>

        <Row style={{ gap: 8, flexWrap: 'wrap', marginTop: 4 }}>
          {testPayloads.map((p) => (
            <Pressable
              key={p.id}
              disabled={testing}
              onPress={() => runSimulation(p.text, p.actor)}
              style={({ pressed }) => [
                styles.testBtn,
                pressed && { opacity: 0.7, transform: [{ scale: 0.96 }] },
              ]}
              accessibilityRole="button"
            >
              <Ionicons name={p.icon} size={13} color={Space.neon} />
              <SpaceText small style={styles.testBtnText}>
                {p.label}
              </SpaceText>
            </Pressable>
          ))}
        </Row>

        {testing && (
          <Row style={{ gap: 8, alignItems: 'center', marginTop: 8 }}>
            <ActivityIndicator size="small" color={Space.neon} />
            <SpaceText muted small>
              {t('firewallTesting')}
            </SpaceText>
          </Row>
        )}

        {testResult && !testing && (
          <View style={styles.resultBox}>
            <Row style={{ justifyContent: 'space-between', alignItems: 'center' }}>
              <Badge tone={testResult.verdict.action_taken === 'block' ? 'block' : 'warn'}>
                {testResult.verdict.action_taken.toUpperCase()}
              </Badge>
              <SpaceText muted small style={{ fontSize: 10 }}>
                {t('firewallLatency')}: {testResult.verdict.latency_ms}ms
              </SpaceText>
            </Row>

            <View style={{ gap: 2, marginTop: 4 }}>
              <SpaceText muted small style={{ fontSize: 10, textTransform: 'uppercase' }}>
                {t('firewallFiltered')}:
              </SpaceText>
              <SpaceText small style={styles.resultText}>
                {testResult.verdict.filtered_text}
              </SpaceText>
            </View>

            {testResult.verdict.violations.length > 0 && (
              <View style={{ gap: 4, marginTop: 4 }}>
                {testResult.verdict.violations.map((v, idx) => (
                  <Row key={idx} style={{ gap: 6, alignItems: 'center' }}>
                    <Ionicons name="shield-checkmark" size={13} color={Tone.block.neon} />
                    <SpaceText small style={{ color: Tone.block.neon, fontSize: 11, flex: 1 }}>
                      {v.description}
                    </SpaceText>
                  </Row>
                ))}
              </View>
            )}
          </View>
        )}
      </View>

      {/* Toggle Recent Interceptions Log */}
      <Pressable
        onPress={() => setShowLog(!showLog)}
        style={({ pressed }) => [styles.toggleBtn, pressed && { opacity: 0.7 }]}
        accessibilityRole="button"
      >
        <SpaceText neon small style={styles.toggleText}>
          {showLog ? t('fuzzHideDetails') : t('firewallRecent')}
        </SpaceText>
        <Ionicons
          name={showLog ? 'chevron-up' : 'chevron-down'}
          size={16}
          color={Space.neon}
        />
      </Pressable>

      {/* Details Section */}
      {showLog && (
        <View style={styles.detailsContainer}>

          {status?.recent_interceptions && status.recent_interceptions.length > 0 && (
            <View style={{ marginTop: 8 }}>
              <SpaceText small style={styles.sectionHeading}>
                {t('firewallRecent')}
              </SpaceText>
              {status.recent_interceptions.map((item, idx) => (
                <View key={idx} style={styles.blockRow}>
                  <Ionicons name="shield-outline" size={14} color={Tone.block.neon} />
                  <View style={{ flex: 1 }}>
                    <Row style={{ justifyContent: 'space-between' }}>
                      <SpaceText small style={{ color: Tone.block.neon, fontWeight: '600', fontSize: 11 }}>
                        {item.action.toUpperCase()} · {item.actor.toUpperCase()}
                      </SpaceText>
                      <SpaceText muted small style={{ fontSize: 10 }}>
                        {item.timestamp ? item.timestamp.slice(11, 19) : ''}
                      </SpaceText>
                    </Row>
                    {item.violations.map((v, vIdx) => (
                      <SpaceText key={vIdx} muted small style={{ fontSize: 11 }}>
                        • {v.description}
                      </SpaceText>
                    ))}
                  </View>
                </View>
              ))}
            </View>
          )}

          <Row style={{ marginTop: 8, justifyContent: 'flex-end' }}>
            <Pressable onPress={() => reload()} style={{ padding: 4 }}>
              <Ionicons name="refresh" size={14} color={Space.muted} />
            </Pressable>
          </Row>
        </View>
      )}
    </Panel>
  );
}

const styles = StyleSheet.create({
  cardContainer: {
    padding: 16,
    gap: 12,
  },
  headerRow: {
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  explainer: {
    lineHeight: 18,
  },
  metricsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingVertical: 4,
  },
  metricBlock: {
    alignItems: 'center',
    gap: 2,
  },
  metricLabel: {
    fontSize: 10,
    textAlign: 'center',
  },
  divider: {
    width: 1,
    height: 36,
    backgroundColor: Space.rim,
  },
  breakdownBox: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: Radius.md,
    padding: 10,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Space.rim,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: Radius.sm,
  },
  chipText: {
    fontSize: 10,
    color: Space.text,
  },
  simContainer: {
    backgroundColor: 'rgba(16, 185, 129, 0.06)',
    borderColor: 'rgba(16, 185, 129, 0.25)',
    borderWidth: 1,
    borderRadius: Radius.md,
    padding: 12,
    gap: 8,
  },
  simHeading: {
    color: Space.neon,
    fontWeight: '700',
    fontSize: 11,
    letterSpacing: 0.5,
  },
  testBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: 'rgba(16, 185, 129, 0.12)',
    borderColor: 'rgba(16, 185, 129, 0.35)',
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: Radius.sm,
  },
  testBtnText: {
    fontSize: 11,
    color: Space.text,
    fontWeight: '500',
  },
  resultBox: {
    marginTop: 6,
    backgroundColor: 'rgba(0, 0, 0, 0.35)',
    borderRadius: Radius.sm,
    padding: 10,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.2)',
    gap: 4,
  },
  resultText: {
    color: '#34D399',
    fontFamily: 'monospace',
    fontSize: 11,
    lineHeight: 16,
  },
  toggleBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 6,
  },
  toggleText: {
    fontWeight: '600',
  },
  detailsContainer: {
    backgroundColor: 'rgba(0, 0, 0, 0.2)',
    borderRadius: Radius.md,
    padding: 12,
    gap: 6,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Space.rim,
  },
  sectionHeading: {
    color: Space.neon,
    fontWeight: '700',
    fontSize: 11,
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  detailBody: {
    lineHeight: 17,
  },
  blockRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    paddingVertical: 6,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Space.rim,
  },
});
