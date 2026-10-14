import { useCallback, useState } from 'react';

import { CardControls } from '@/components/card-controls';
import { ActiveMandateCard, MandateComposer, ProposalCard } from '@/components/mandate';
import { NeedCard } from '@/components/note-card';
import { TimelineCard } from '@/components/timeline-card';
import { Banner, ErrorBox, H1, H2, Muted, Screen } from '@/components/ui';
import type { Feed, MandateView, Proposal, Timeline, NeedItem } from '@/lib/api';
import { cny } from '@/lib/format';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

/** Act: the family mandate (what Sathi may do alone), what waits for this person, the card and renewals. */
export default function FamilyScreen() {
  const { t, lang, call } = useSession();
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [signed, setSigned] = useState<string | null>(null);
  const { data, error, loading, reload } = useLoad(
    useCallback(async () => {
      const [mandates, feed, timeline] = await Promise.all([
        call<MandateView[]>('/mandates'),
        call<Feed>(`/feed?lang=${lang}`),
        call<Timeline>('/timeline'),
      ]);
      // A proposal someone else wrote that waits for MY signature (e.g. the student co-signs a large mandate).
      const waiting = feed.needs_you.find((n) => n.type === 'sign_mandate');
      const pending = waiting?.type === 'sign_mandate' ? await call<Proposal>(`/mandates/proposals/${waiting.proposal_id}`) : null;
      return { mandates, feed, timeline, pending };
    }, [call, lang]),
  );

  const active = data?.mandates.find((m) => m.active && m.auto_topup);
  const shown = proposal ?? data?.pending ?? null;
  const payments =
    data?.feed.needs_you.filter((n): n is Extract<NeedItem, { draft_id: string }> => n.type === 'approve_draft' || n.type === 'send_draft') ?? [];

  function onSigned(p: Proposal) {
    if (p.status === 'active') {
      setProposal(null);
      const sent = p.autopilot?.find((a) => a.type === 'autopilot_sent');
      setSigned(sent?.amount_cny ? `${t('mandateActive')} · ${t('autopilotActed')} ${cny(sent.amount_cny, lang)} ${t('sentAmount')}` : t('mandateActive'));
    } else {
      setProposal(p);
      setSigned(t('signedOk'));
    }
    reload();
  }

  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <H1>{t('tabFamily')}</H1>
      <ErrorBox error={error} />
      {signed && <Banner tone="ok">{signed}</Banner>}
      {active && <ActiveMandateCard m={active} onChanged={reload} />}
      {shown && shown.status !== 'active' && <ProposalCard proposal={shown} onSigned={onSigned} />}
      {!shown && !active && <MandateComposer onProposal={setProposal} />}

      {payments.length > 0 && (
        <>
          <H2>{t('approvals')}</H2>
          {payments.map((n) => (
            <NeedCard key={n.draft_id} need={n} />
          ))}
        </>
      )}

      {data && (
        <>
          <H2>{t('cards')}</H2>
          <CardControls card={data.timeline.card} onChange={reload} />
          <H2>{t('renewals')}</H2>
          {data.timeline.items
            .filter((i) => i.type === 'endorsement_expiry' || i.type === 'student_file_renewal')
            .map((i) => (
              <TimelineCard key={i.type} item={i} />
            ))}
          <Muted>{t('readAloudHint')}</Muted>
        </>
      )}
    </Screen>
  );
}
