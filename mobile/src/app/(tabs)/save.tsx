import { useCallback } from 'react';

import { CrisisCard, HundiCard, IncomeCard, SavingsRuleCard, ShieldCard, ShieldHistory, WantsCard } from '@/components/save';
import { Kicker } from '@/components/neo';
import { ErrorBox, H1, Muted, Screen } from '@/components/ui';
import type { CrisisTest, SavingsView } from '@/lib/api';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

/**
 * Earn & Save: the student's own money abroad (Interview #2). Its own small loop, in sync with the main one:
 * Sense (income, wants in taka) → Plan (savings rule, dollar-crisis test, hundi check) → Act (the signed rule fills the
 * Shield; emergencies use it at once) → Prove (every Shield move in the hash-chained log).
 * The parent sees the Shield level if the student shares it, and approves releases only if the student chose that.
 */
export default function SaveScreen() {
  const { t, lang, role, call } = useSession();
  const { data, error, loading, reload } = useLoad(
    useCallback(async () => {
      const [v, crisis] = await Promise.all([call<SavingsView>(`/save?lang=${lang}`), call<CrisisTest>('/save/crisis')]);
      return { v, crisis };
    }, [call, lang]),
  );

  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <Kicker>{t('saveKicker')}</Kicker>
      <H1>{t('saveTitle')}</H1>
      <Muted>{role === 'student' ? t('saveIntro') : t('saveIntroParent')}</Muted>
      <ErrorBox error={error} />
      {data && (
        <>
          <ShieldCard v={data.v} onChanged={reload} />
          {role === 'student' && <SavingsRuleCard key={data.v.proposal?.id ?? 'new'} v={data.v} onChanged={reload} />}
          {role === 'student' && <IncomeCard v={data.v} onChanged={reload} />}
          {role === 'student' && <WantsCard v={data.v} onChanged={reload} />}
          <CrisisCard crisis={data.crisis} />
          <HundiCard />
          <ShieldHistory v={data.v} />
        </>
      )}
    </Screen>
  );
}
