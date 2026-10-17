import Ionicons from '@expo/vector-icons/Ionicons';
import { useCallback, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { BigNumber, Kicker, Panel, SpaceText } from '@/components/neo';
import { Badge, Row } from '@/components/ui';
import { Radius, Space, Tone } from '@/constants/theme';
import type { TaintStatus } from '@/lib/api';
import { num } from '@/lib/format';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

/**
 * CaMeL (2025) Taint Tracking and Information Flow Control (IFC) Card.
 * Proves that outside text (SMS, email, photos) is tagged UNTRUSTED by design,
 * and payment sinks refuse un-endorsed entities without relying on pattern matching.
 */
export function TaintCard() {
  const { t, lang, call } = useSession();
  const [showDetails, setShowDetails] = useState(false);

  const { data: status, reload } = useLoad(
    useCallback(async () => {
      return call<TaintStatus>('/security/taint/status');
    }, [call]),
  );

  const untrustedCount = status?.untrusted_entities ?? 0;
  const endorsedCount = status?.endorsed_entities ?? 0;
  const blockedCount = status?.total_injections_blocked ?? 0;

  return (
    <Panel style={styles.cardContainer}>
      {/* Header */}
      <Row style={styles.headerRow}>
        <Kicker dark>{t('taintKicker')}</Kicker>
        <Badge tone="info">{t('taintBadge')}</Badge>
      </Row>

      {/* Explainer */}
      <SpaceText muted small style={styles.explainer}>
        {t('taintExplainer')}
      </SpaceText>

      {/* 3 Metrics Block */}
      <View style={styles.metricsRow}>
        <View style={styles.metricBlock}>
          <BigNumber
            value={untrustedCount}
            size={28}
            color={Tone.block.neon}
            format={(n) => num(Math.round(n), lang)}
          />
          <SpaceText muted small style={styles.metricLabel}>
            {t('taintUntrusted')}
          </SpaceText>
        </View>

        <View style={styles.divider} />

        <View style={styles.metricBlock}>
          <BigNumber
            value={endorsedCount}
            size={28}
            color={Tone.info.neon}
            format={(n) => num(Math.round(n), lang)}
          />
          <SpaceText muted small style={styles.metricLabel}>
            {t('taintEndorsed')}
          </SpaceText>
        </View>

        <View style={styles.divider} />

        <View style={styles.metricBlock}>
          <BigNumber
            value={blockedCount}
            size={28}
            color={Space.neon}
            format={(n) => num(Math.round(n), lang)}
          />
          <SpaceText muted small style={styles.metricLabel}>
            {t('taintBlocked')}
          </SpaceText>
        </View>
      </View>

      {/* DeepMind CaMeL Architectural Banner */}
      <View style={styles.camelPill}>
        <Ionicons name="git-branch-outline" size={16} color={Space.neon} />
        <View style={{ flex: 1 }}>
          <SpaceText small style={styles.camelHeading}>
            {t('taintRuleTitle')}
          </SpaceText>
          <SpaceText muted small style={styles.camelFormula}>
            {t('taintRule')}
          </SpaceText>
        </View>
      </View>

      {/* Toggle Recent Blocks */}
      <Pressable
        onPress={() => setShowDetails(!showDetails)}
        style={({ pressed }) => [styles.toggleBtn, pressed && { opacity: 0.7 }]}
        accessibilityRole="button"
      >
        <SpaceText neon small style={styles.toggleText}>
          {showDetails ? t('fuzzHideDetails') : t('taintShow')}
        </SpaceText>
        <Ionicons
          name={showDetails ? 'chevron-up' : 'chevron-down'}
          size={16}
          color={Space.neon}
        />
      </Pressable>

      {/* Details Section */}
      {showDetails && (
        <View style={styles.detailsContainer}>

          {status?.recent_blocks && status.recent_blocks.length > 0 && (
            <View style={{ marginTop: 8 }}>
              <SpaceText small style={styles.sectionHeading}>
                {t('taintBlocked')}
              </SpaceText>
              {status.recent_blocks.map((blk, idx) => (
                <View key={idx} style={styles.blockRow}>
                  <Ionicons name="shield-outline" size={14} color={Tone.block.neon} />
                  <View style={{ flex: 1 }}>
                    <SpaceText small style={{ color: Tone.block.neon, fontWeight: '600' }}>
                      {blk.sink} ({blk.parameter})
                    </SpaceText>
                    <SpaceText muted small>
                      {blk.reason}
                    </SpaceText>
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
    fontSize: 11,
  },
  divider: {
    width: 1,
    height: 36,
    backgroundColor: Space.rim,
  },
  camelPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: 'rgba(56, 189, 248, 0.08)',
    borderColor: 'rgba(56, 189, 248, 0.25)',
    borderWidth: 1,
    borderRadius: Radius.sm,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  camelHeading: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.6,
    color: Space.neon,
  },
  camelFormula: {
    fontSize: 11,
    fontFamily: 'monospace',
    marginTop: 1,
  },
  toggleBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: Space.rim,
  },
  toggleText: {
    fontWeight: '600',
  },
  detailsContainer: {
    gap: 6,
    paddingTop: 4,
  },
  sectionHeading: {
    fontWeight: '700',
    color: Space.neon,
    fontSize: 11,
    letterSpacing: 0.6,
    marginBottom: 4,
  },
  detailBody: {
    fontSize: 11,
    lineHeight: 16,
  },
  blockRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    paddingVertical: 4,
  },
});
