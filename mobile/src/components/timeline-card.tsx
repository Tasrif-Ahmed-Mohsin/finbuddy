import { router } from 'expo-router';

import { ThemedText } from '@/components/themed-text';
import { Badge, Button, Card, H2, Muted, Row, styles } from '@/components/ui';
import type { TimelineItem } from '@/lib/api';
import { cny, num, shortDate } from '@/lib/format';
import { useSession } from '@/lib/session';

/** A deadline from the profile: tuition (send-by date) or a renewal (endorsement / Student File). */
export function TimelineCard({ item }: { item: TimelineItem }) {
  const { t, lang } = useSession();
  if (item.type === 'tuition_due') {
    const days = item.days_to_send_by ?? 0;
    const tone = days < 0 ? 'block' : days <= 2 ? 'warn' : 'ok';
    return (
      <Card tone={tone}>
        <Row style={styles.between}>
          <H2>{t('tuition')}</H2>
          <ThemedText type="smallBold">{cny(item.amount_cny ?? 0, lang)}</ThemedText>
        </Row>
        <Muted>
          {t('due')}: {shortDate(item.due, lang)} · {t('sendBy')}: {shortDate(item.send_by, lang)}
        </Muted>
        <Badge tone={tone}>
          {num(days, lang)} {t('daysLeft')}
        </Badge>
        <Button title={t('planIt')} onPress={() => router.push({ pathname: '/plan', params: { mode: 'tuition' } })} />
      </Card>
    );
  }
  if (item.type === 'living_money') return null;
  const title = item.type === 'endorsement_expiry' ? t('endorsement') : t('studentFile');
  const days = item.days_left ?? 0;
  const tone = days < 0 ? 'block' : item.warn ? 'warn' : 'ok';
  return (
    <Card tone={tone}>
      <H2>{title}</H2>
      <Muted>
        {t('expires')}: {shortDate(item.due, lang)}
      </Muted>
      <Row>
        <Badge tone={tone}>
          {num(days, lang)} {t('daysLeft')}
        </Badge>
        {item.warn && <Badge tone="warn">{t('renewSoon')}</Badge>}
      </Row>
      <Button
        title={t('renewalPlan')}
        variant={item.warn ? 'primary' : 'secondary'}
        onPress={() =>
          router.push({ pathname: '/renewal/[item]', params: { item: item.type === 'endorsement_expiry' ? item.type : 'student_file_expiry' } })
        }
      />
    </Card>
  );
}
