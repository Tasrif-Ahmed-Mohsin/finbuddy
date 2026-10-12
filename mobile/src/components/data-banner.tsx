import { Banner } from '@/components/ui';
import type { DataQuality } from '@/lib/api';
import { shortDate } from '@/lib/format';
import { useSession } from '@/lib/session';

/** Always tell the user where the numbers come from: real market rate, estimated bank prices. */
export function DataBanner({ dq }: { dq?: DataQuality | null }) {
  const { t, lang } = useSession();
  if (!dq) return null;
  const rate = dq.mid === 'fixture' ? t('sampleBanner') : `${dq.mid === 'live' ? t('liveRate') : t('savedRate')} ${shortDate(dq.mid_as_of, lang)}`;
  const quotes = dq.bank_quotes === 'real' ? t('bankReal') : dq.bank_quotes === 'mixed' ? t('bankMixed') : t('bankEstimates');
  return <Banner tone={dq.bank_quotes === 'real' && dq.mid !== 'fixture' ? 'ok' : 'warn'}>{`${rate} · ${quotes}`}</Banner>;
}
