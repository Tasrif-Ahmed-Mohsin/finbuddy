import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { useEffect, useRef, useState, type ComponentProps } from 'react';
import { ActivityIndicator, Platform, Pressable, StyleSheet, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';

import { Mascot, type MascotAction, type MascotMood } from '@/components/mascot';
import { Kicker, Panel, SpaceText } from '@/components/neo';
import { ThemedText } from '@/components/themed-text';
import { Button, Chip, ErrorBox, Field, Muted, Row } from '@/components/ui';
import { Brand, Elevation, Radius, Space, Tone, type ToneName } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { post, type ChatChoice, type ChatReply, type ChatSignal } from '@/lib/api';
import type { StringKey } from '@/lib/i18n';
import { useSession } from '@/lib/session';
import { VoiceButton } from '@/components/voice-button';

type Turn = { role: 'user' | 'assistant'; content: string; reply?: ChatReply };
type IconName = ComponentProps<typeof Ionicons>['name'];

/** The model is asked for plain text; this strips any markdown that slips through. */
function plain(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^\s*[-*]\s+/gm, '• ');
}

/** How each kind of turn is shown, and how Bluefin's face reacts to it (the most important signal wins). */
const SIGNALS: { key: ChatSignal; label: StringKey; icon: IconName; tone: ToneName; mood: MascotMood; gesture?: MascotAction['type'] }[] = [
  { key: 'refused', label: 'sigRefused', icon: 'shield-checkmark', tone: 'block', mood: 'protect', gesture: 'shake' },
  { key: 'card_locked', label: 'card', icon: 'lock-closed', tone: 'warn', mood: 'protect' },
  { key: 'checked', label: 'sigScam', icon: 'shield-half', tone: 'ok', mood: 'protect' },
  { key: 'clarify', label: 'sigClarify', icon: 'help-circle', tone: 'info', mood: 'curious' },
  { key: 'corrected', label: 'sigCorrected', icon: 'create', tone: 'ok', mood: 'happy', gesture: 'nod' },
  { key: 'drafted', label: 'sigDrafted', icon: 'document-text', tone: 'info', mood: 'happy', gesture: 'nod' },
  { key: 'cancelled', label: 'sigCancelled', icon: 'close-circle', tone: 'neutral', mood: 'idle', gesture: 'nod' },
  { key: 'offline', label: 'sigOffline', icon: 'cloud-offline', tone: 'neutral', mood: 'idle' },
];

const SUGGESTIONS: StringKey[] = ['sug_year', 'sug_send', 'sug_hundi', 'sug_card'];

export function SathiChat() {
  const { t, lang, call } = useSession();
  const theme = useTheme();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [typing, setTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [face, setFace] = useState<{ mood: MascotMood; say: StringKey; action?: MascotAction }>({ mood: 'idle', say: 'chatHello' });
  const settle = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastReply = turns.length > 0 && turns[turns.length - 1].role === 'assistant' ? turns[turns.length - 1].reply : undefined;
  useEffect(() => () => {
    if (settle.current) clearTimeout(settle.current);
  }, []);

  function react(reply: ChatReply) {
    const top = SIGNALS.find((s) => s.key !== 'offline' && reply.signals?.includes(s.key));
    // Talk for a moment, then show what happened.
    setFace({ mood: 'talking', say: top ? top.label : 'chatHello' });
    if (settle.current) clearTimeout(settle.current);
    settle.current = setTimeout(() => {
      setFace({
        mood: top?.mood ?? 'idle',
        say: top ? top.label : 'chatHello',
        action: top?.gesture ? { type: top.gesture, key: Date.now() } : undefined,
      });
    }, 1400);
  }

  async function send(preset?: string) {
    const message = (preset ?? text).trim();
    if (!message || busy) return;
    if (!preset) setText('');
    setError(null);
    const history = turns.map(({ role, content }) => ({ role, content }));
    setTurns((prev) => [...prev, { role: 'user', content: message }]);
    setBusy(true);
    setFace({ mood: 'thinking', say: 'chatThinking' });
    try {
      const reply = await call<ChatReply>('/agent/chat', post({ message, history, lang }));
      setTurns((prev) => [...prev, { role: 'assistant', content: reply.reply, reply }]);
      react(reply);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setFace({ mood: 'worried', say: 'chatHello' });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {/* Comms: Bluefin as a hologram on a dark panel, with what it is doing right now in neon. */}
      <Panel>
        <Row style={{ flexWrap: 'nowrap', gap: 14 }}>
          <View style={local.holo}>
            <View style={local.holoBase} />
            <Mascot size={96} mood={face.mood} action={face.action} look={typing && !busy ? 'down' : undefined} />
          </View>
          <View style={{ flex: 1, gap: 6 }}>
            <Kicker dark color={face.mood === 'protect' ? Tone.block.neon : Space.neon}>
              {t(`buddyMood_${face.mood}`)}
            </Kicker>
            <Animated.View key={face.say} entering={FadeInDown.duration(240)}>
              <SpaceText>{t(face.say)}</SpaceText>
            </Animated.View>
          </View>
        </Row>
      </Panel>

      {turns.length === 0 && (
        <View style={local.suggest}>
          <Muted>{t('chatTry')}</Muted>
          <Row>
            {SUGGESTIONS.map((k) => (
              <Chip key={k} label={t(k)} icon="chatbubble-ellipses-outline" onPress={() => send(t(k))} />
            ))}
          </Row>
        </View>
      )}

      {turns.map((turn, i) =>
        turn.role === 'user' ? (
          <Animated.View key={i} entering={FadeInDown.duration(220)} style={local.userBubble}>
            <ThemedText style={{ color: Brand.primaryText }}>{turn.content}</ThemedText>
          </Animated.View>
        ) : (
          <Animated.View key={i} entering={FadeInDown.duration(260)} style={[local.botBubble, { backgroundColor: theme.backgroundElement }]}>
            <ThemedText>{plain(turn.content)}</ThemedText>
            <Row>
              {SIGNALS.filter((s) => turn.reply?.signals?.includes(s.key)).map((s) => (
                <SignalChip key={s.key} icon={s.icon} tone={s.tone} label={t(s.label)} />
              ))}
              {turn.reply?.mode === 'llm' && <SignalChip icon="sparkles" tone="info" label={t('sigAi')} />}
              {turn.reply?.firewall && !turn.reply.firewall.passed && (
                <SignalChip
                  icon="shield-checkmark"
                  tone={turn.reply.firewall.action_taken === 'block' ? 'block' : 'warn'}
                  label={`${t('sigFirewallGuarded')} (${turn.reply.firewall.violations.length})`}
                />
              )}
            </Row>
            {turn.reply?.actions.map((a) =>
              a.type === 'draft' ? (
                <Button key={a.draft_id} icon="document-text-outline" title={t('openDraft')} onPress={() => router.push({ pathname: '/draft/[id]', params: { id: a.draft_id } })} />
              ) : a.type === 'renewal' ? (
                <Button key={a.case_id} icon="refresh" title={t('openRenewal')} onPress={() => router.push({ pathname: '/renewal/[item]', params: { item: a.item } })} />
              ) : a.type === 'mandate' ? (
                <Button key={a.proposal_id} icon="create-outline" title={t('signMandate')} onPress={() => router.push('/family')} />
              ) : (
                <SignalChip key={`card-${a.last4}`} icon="lock-closed" tone="warn" label={`${t('card')} ••••${a.last4}: ${a.status}`} />
              ),
            )}
            {turn.reply && <Steps tools={turn.reply.tools_used} />}
          </Animated.View>
        ),
      )}
      {/* One-tap answers for the newest reply: the missing detail, or a way out of the draft. */}
      {!busy && lastReply?.choices && lastReply.choices.length > 0 && (
        <Row style={local.choices}>
          {lastReply.choices.map((c) => {
            const label = choiceLabel(c, t);
            return <Chip key={label} label={label} icon={c.kind === 'cancel' ? 'close-circle-outline' : 'return-down-forward'} onPress={() => send(label)} />;
          })}
        </Row>
      )}
      {busy && (
        <View style={[local.botBubble, local.typingRow, { backgroundColor: theme.backgroundElement }]}>
          <ActivityIndicator size="small" color={Brand.primary} />
          <Muted>{t('chatThinking')}</Muted>
        </View>
      )}
      <ErrorBox error={error} />

      <View style={local.composer}>
        <View style={local.composerField}>
          <Field
            label=""
            value={text}
            onChangeText={setText}
            placeholder={t('typeMessage')}
            multiline
            onSubmitEditing={() => send()}
            onFocus={() => setTyping(true)}
            onKeyPress={(e) => {
              // On a keyboard (the web app), Enter sends and Shift+Enter starts a new line.
              const ev = e.nativeEvent as { key: string; shiftKey?: boolean };
              if (Platform.OS === 'web' && ev.key === 'Enter' && !ev.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            onBlur={() => setTyping(false)}
            style={local.input}
          />
        </View>
        <VoiceButton onText={setText} onError={setError} />
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('send')}
          onPress={() => send()}
          disabled={!text.trim() || busy}
          style={({ pressed }) => [
            local.sendButton,
            { backgroundColor: text.trim() && !busy ? Brand.primary : theme.backgroundSelected },
            text.trim() && !busy ? { boxShadow: Elevation.glow } : null,
            pressed && { transform: [{ scale: 0.94 }] },
          ]}>
          {busy ? <ActivityIndicator color="#FFFFFF" /> : <Ionicons name="arrow-up" size={22} color={text.trim() ? '#FFFFFF' : theme.textTertiary} />}
        </Pressable>
      </View>
    </>
  );
}

/** The tap-able text is also what is sent, so the agent reads exactly the words the user sees. */
function choiceLabel(c: ChatChoice, t: (k: StringKey) => string): string {
  if (c.kind === 'purpose') return t(c.value === 'tt_tuition' ? 'choiceTuition' : 'choiceLiving');
  if (c.kind === 'amount') return `¥${Number(c.value).toLocaleString('en-US')}`;
  return t('choiceCancel');
}

const STEP_KEYS = new Set([
  'get_overview', 'get_updates', 'list_transactions', 'compare_tuition', 'plan_living', 'check_message', 'start_renewal',
  'freeze_card', 'get_emergency_plan', 'ask_family_for_money', 'get_year_plan', 'propose_mandate', 'revise_payment_draft',
  'cancel_payment_draft', 'get_savings', 'propose_savings_rule', 'check_hundi_offer', 'create_payment_draft',
  'refuse_escalation', 'clarify',
]);

/** "How Bluefin did it": the steps the agent took for this answer, as a small neon timeline (task planning, visible). */
function Steps({ tools }: { tools: string[] }) {
  const { t } = useSession();
  const steps = tools.filter((x, i) => STEP_KEYS.has(x) && tools.indexOf(x) === i);
  if (steps.length === 0) return null;
  return (
    <View style={local.steps}>
      <ThemedText style={local.stepsTitle}>{t('stepsTitle')}</ThemedText>
      {steps.map((x, i) => (
        <View key={x} style={local.stepRow}>
          <View style={local.stepRail}>
            <View style={local.stepDot} />
            {i < steps.length - 1 && <View style={local.stepLine} />}
          </View>
          <ThemedText type="small" themeColor="textSecondary" style={{ flex: 1, paddingBottom: 6 }}>
            {t(`step_${x}` as StringKey)}
          </ThemedText>
        </View>
      ))}
    </View>
  );
}

function SignalChip({ icon, tone, label }: { icon: IconName; tone: ToneName; label: string }) {
  return (
    <View style={[local.signal, { backgroundColor: Tone[tone].bg }]}>
      <Ionicons name={icon} size={13} color={Tone[tone].fg} />
      <ThemedText style={[local.signalText, { color: Tone[tone].fg }]}>{label}</ThemedText>
    </View>
  );
}

const local = StyleSheet.create({
  holo: { width: 96, alignItems: 'center', justifyContent: 'flex-end' },
  holoBase: {
    position: 'absolute',
    bottom: 2,
    width: 78,
    height: 14,
    borderRadius: 39,
    backgroundColor: 'rgba(77, 163, 255, 0.35)',
    boxShadow: '0px 0px 18px rgba(77, 163, 255, 0.8)',
  },
  suggest: { gap: 10 },
  choices: { gap: 8 },
  steps: { gap: 2, paddingTop: 8, borderTopWidth: 1, borderTopColor: 'rgba(163, 170, 184, 0.35)' },
  stepsTitle: { fontSize: 11, lineHeight: 14, fontWeight: '600', letterSpacing: 1.2, textTransform: 'uppercase', color: '#5F6470', marginBottom: 4 },
  stepRow: { flexDirection: 'row', gap: 10 },
  stepRail: { width: 12, alignItems: 'center' },
  stepDot: { width: 8, height: 8, borderRadius: 4, marginTop: 6, backgroundColor: Space.neon, boxShadow: `0px 0px 6px ${Space.neon}` },
  stepLine: { flex: 1, width: 1.5, backgroundColor: 'rgba(77, 163, 255, 0.4)', marginTop: 2 },
  userBubble: { alignSelf: 'flex-end', maxWidth: '85%', backgroundColor: Brand.primary, borderRadius: 20, borderBottomRightRadius: 6, paddingHorizontal: 14, paddingVertical: 10, boxShadow: Elevation.glow },
  botBubble: { alignSelf: 'flex-start', maxWidth: '92%', borderRadius: 20, borderBottomLeftRadius: 6, padding: 14, gap: 10, boxShadow: Elevation[2] },
  typingRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  signal: { flexDirection: 'row', alignItems: 'center', gap: 5, borderRadius: Radius.pill, paddingHorizontal: 9, paddingVertical: 4 },
  signalText: { fontSize: 12, lineHeight: 16, fontWeight: '600' },
  composer: { flexDirection: 'row', alignItems: 'flex-end', gap: 10 },
  composerField: { flex: 1 },
  input: { maxHeight: 140 },
  sendButton: { width: 50, height: 50, borderRadius: 25, alignItems: 'center', justifyContent: 'center' },
});
