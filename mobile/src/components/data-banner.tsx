import { Banner } from '@/components/ui';
import type { DataQuality } from '@/lib/api';
import { shortDate } from '@/lib/format';
import { useSession } from '@/lib/session';

/** Always tell the user where the numbers come from: real market rate, estimated bank prices. */
export function DataBanner({ dq }: { dq?: DataQuality | null }) {
  const { t, lang } = useSession();
  if (!dq) return null;
  const rate = dq.mid === 'fixture' ? t('sampleBanner') : `${dq.mid === 'live' ? t('liveRate') : t('savedRate')} ${shortDate(dq.mid_as_of, lang)}`;
  const quotes = dq.bank_quotes === 'published' ? t('pricesPublished') : dq.bank_quotes === 'mixed' ? t('pricesMixed') : t('bankEstimates');
  const tone = dq.mid === 'fixture' || dq.bank_quotes === 'estimated' ? 'warn' : dq.bank_quotes === 'published' ? 'ok' : 'info';
  return <Banner tone={tone}>{`${rate} · ${quotes}`}</Banner>;
}
