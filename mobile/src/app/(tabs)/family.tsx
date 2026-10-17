import { useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';

import { CardControls } from '@/components/card-controls';
import { ActiveMandateCard, MandateComposer, ProposalCard } from '@/components/mandate';
import { Kicker } from '@/components/neo';
import { NeedCard } from '@/components/note-card';
import { ProofPanel } from '@/components/proof-panel';
import { TimelineCard } from '@/components/timeline-card';
import { Banner, ErrorBox, H1, H2, Muted, Screen, Segmented } from '@/components/ui';
import type { Feed, MandateView, Proposal, Timeline, NeedItem } from '@/lib/api';
import { cny } from '@/lib/format';
import { useSession } from '@/lib/session';
import { useLoad } from '@/lib/use-load';

type Pane = 'act' | 'cards' | 'proof';

/**
 * Family, the command deck. Act: the family mandate (what Sathi may do alone) and what waits for this person.
 * Cards: the card and its renewals. Proof: receipts and the tamper-evident log.
 */
export default function FamilyScreen() {
  const { t, lang, call } = useSession();
  // Home's widgets can open a pane directly (?pane=cards / ?pane=proof); a tap on the capsule wins until the next link.
  const params = useLocalSearchParams<{ pane?: string }>();
  const wanted = params.pane === 'act' || params.pane === 'cards' || params.pane === 'proof' ? params.pane : undefined;
  const [pick, setPick] = useState<{ v: Pane; at?: string }>({ v: wanted ?? 'act', at: params.pane });
  const pane: Pane = pick.at === params.pane ? pick.v : (wanted ?? pick.v);
  const setPane = (v: Pane) => setPick({ v, at: params.pane });
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
      <Kicker>{t('familyKicker')}</Kicker>
      <H1>{t('tabFamily')}</H1>
      <Segmented<Pane>
        value={pane}
        onChange={setPane}
        options={[
          { value: 'act', label: t('famAct') },
          { value: 'cards', label: t('famCards') },
          { value: 'proof', label: t('tabProof') },
        ]}
      />
      <ErrorBox error={error} />

      {pane === 'act' && (
        <>
          {signed && <Banner tone="ok">{signed}</Banner>}
          {active && <ActiveMandateCard m={active} onChanged={reload} />}
          {shown && shown.status !== 'active' && <ProposalCard proposal={shown} onSigned={onSigned} />}
          {!shown && !active && <MandateComposer onProposal={setProposal} />}
          {payments.length > 0 && (
            <>
              <H2 icon="finger-print">{t('approvals')}</H2>
              {payments.map((n) => (
                <NeedCard key={n.draft_id} need={n} />
              ))}
            </>
          )}
        </>
      )}

      {pane === 'cards' && data && (
        <>
          <H2 icon="card">{t('cards')}</H2>
          <CardControls card={data.timeline.card} onChange={reload} />
          <H2 icon="refresh">{t('renewals')}</H2>
          {data.timeline.items
            .filter((i) => i.type === 'endorsement_expiry' || i.type === 'student_file_renewal')
            .map((i) => (
              <TimelineCard key={i.type} item={i} />
            ))}
          <Muted>{t('readAloudHint')}</Muted>
        </>
      )}

      {pane === 'proof' && <ProofPanel />}
    </Screen>
  );
}
