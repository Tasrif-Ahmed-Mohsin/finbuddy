import Ionicons from '@expo/vector-icons/Ionicons';
import { StyleSheet, View } from 'react-native';

import { Kicker, Panel, SpaceText } from '@/components/neo';
import { Badge, Row } from '@/components/ui';
import { Radius, Space, Tone } from '@/constants/theme';
import type { CopVerification } from '@/lib/api';
import { useSession } from '@/lib/session';

type Props = {
  cop?: CopVerification | null;
  compact?: boolean;
};

/**
 * Confirmation of Payee (CoP) verification card.
 * Simulates UK PSR & EU VoP (2024/886) Authorised Push Payment (APP) fraud prevention.
 * Validates that the account holder's registered legal name matches the intended recipient.
 */
export function CopCard({ cop, compact = false }: Props) {
  const { t } = useSession();

  if (!cop) return null;

  const isMatch = cop.status === 'match';
  const isClose = cop.status === 'close_match';
  const isNoMatch = cop.status === 'no_match';

  const badgeTone = isMatch ? 'info' : isClose ? 'warn' : 'block';
  const statusLabel = isMatch
    ? t('copMatched')
    : isClose
    ? t('copCloseMatch')
    : t('copNoMatch');

  const statusIcon = isMatch
    ? 'checkmark-circle'
    : isClose
    ? 'alert-circle'
    : 'close-circle';

  const iconColor = isMatch
    ? Tone.info.neon
    : isClose
    ? Tone.warn.neon
    : Tone.block.neon;

  if (compact) {
    return (
      <View style={[styles.compactContainer, { borderColor: iconColor }]}>
        <Ionicons name={statusIcon} size={15} color={iconColor} />
        <SpaceText small style={{ color: iconColor, fontWeight: '700' }}>
          {statusLabel}
        </SpaceText>
        <SpaceText muted small style={{ fontSize: 10 }}>
          ({cop.registered_name})
        </SpaceText>
      </View>
    );
  }

  return (
    <Panel style={styles.cardContainer} tone={isNoMatch ? 'red' : 'blue'}>
      {/* Header */}
      <Row style={styles.headerRow}>
        <Kicker dark>{t('copKicker')}</Kicker>
        <Badge tone={badgeTone}>{statusLabel}</Badge>
      </Row>

      {/* Main Verification Status */}
      <View style={styles.statusBanner}>
        <Ionicons name={statusIcon} size={22} color={iconColor} />
        <View style={{ flex: 1, gap: 2 }}>
          <SpaceText small style={[styles.statusTitle, { color: iconColor }]}>
            {cop.reason}
          </SpaceText>
          <SpaceText muted small style={{ fontSize: 11 }}>
            {cop.bank_name} ({cop.bic})
          </SpaceText>
        </View>
      </View>

      {/* Comparison Grid */}
      <View style={styles.gridContainer}>
        <View style={styles.gridRow}>
          <SpaceText muted small style={styles.gridLabel}>
            Intended Payee:
          </SpaceText>
          <SpaceText small style={styles.gridValue}>
            {cop.intended_name}
          </SpaceText>
        </View>

        <View style={styles.gridRow}>
          <SpaceText muted small style={styles.gridLabel}>
            {t('copRegisteredName')}:
          </SpaceText>
          <SpaceText small style={[styles.gridValue, { color: isNoMatch ? Tone.block.neon : Space.text }]}>
            {cop.registered_name}
          </SpaceText>
        </View>

        <View style={styles.gridRow}>
          <SpaceText muted small style={styles.gridLabel}>
            {t('copAccountType')}:
          </SpaceText>
          <Badge tone="neutral">
            {cop.account_type.toUpperCase()}
          </Badge>
        </View>
      </View>

      {/* APP Fraud Advice Box */}
      {(isClose || isNoMatch) && (
        <View style={[styles.adviceBox, { borderColor: iconColor }]}>
          <Ionicons name="shield-outline" size={16} color={iconColor} />
          <SpaceText small style={{ flex: 1, fontSize: 11, color: Space.text, lineHeight: 16 }}>
            {cop.advice}
          </SpaceText>
        </View>
      )}

      {/* Standard Note */}
      <SpaceText muted small style={styles.standardNote}>
        {t('copStandardNote')}
      </SpaceText>
    </Panel>
  );
}

const styles = StyleSheet.create({
  cardContainer: {
    padding: 16,
    gap: 12,
  },
  compactContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: Radius.sm,
    borderWidth: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.2)',
  },
  headerRow: {
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statusBanner: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderColor: Space.rim,
    borderWidth: 1,
    borderRadius: Radius.sm,
    padding: 10,
  },
  statusTitle: {
    fontWeight: '700',
    lineHeight: 16,
  },
  gridContainer: {
    gap: 6,
    paddingVertical: 2,
  },
  gridRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  gridLabel: {
    fontSize: 11,
  },
  gridValue: {
    fontWeight: '600',
    fontSize: 12,
  },
  adviceBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    backgroundColor: 'rgba(255, 92, 92, 0.08)',
    borderWidth: 1,
    borderRadius: Radius.sm,
    padding: 10,
  },
  standardNote: {
    fontSize: 10,
    marginTop: 2,
  },
});
