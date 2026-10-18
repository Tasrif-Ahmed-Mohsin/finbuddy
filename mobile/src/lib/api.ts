/** Typed client for the Bluefin backend. All money values arrive as strings (server uses Decimal). */

export type Role = 'student' | 'parent';

// Sandbox demo tokens (see backend/app/main.py). Listed as a known risk in the security report.
const TOKENS: Record<Role, string> = { student: 'demo-student', parent: 'demo-parent' };

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(base: string, role: Role, path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${base}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKENS[role]}`, ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, `Cannot reach the server at ${base}. Is the backend running?`);
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = body?.detail;
    throw new ApiError(res.status, typeof detail === 'string' ? detail : JSON.stringify(detail ?? res.statusText));
  }
  return body as T;
}

export const post = (body: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(body) });

// ---- response types ------------------------------------------------------
export type Check = { id: string; passed: boolean; severity: 'block' | 'warn' | 'info'; message: string; source: string };

export type PasskeyApproval = {
  actor: Role;
  credential_id: string;
  label: string;
  thumbprint: string;
  draft_hash: string;
  verified_at: string;
  biometric_uv: boolean;
  alg: string;
  kind?: 'webauthn' | 'device_key' | 'simulated';
  origin?: string;
};

export type CopVerification = {
  status: 'match' | 'close_match' | 'no_match' | 'opted_out' | 'unavailable';
  intended_name: string;
  registered_name: string;
  account_type: 'business' | 'personal';
  match_score: number;
  bank_name: string;
  bic: string;
  app_scam_risk: 'low' | 'medium' | 'critical';
  reason: string;
  advice: string;
  verified_at: string;
};

export type Draft = {
  id: string;
  kind: 'tt_tuition' | 'tt_living' | 'atm_plan';
  payer: Role;
  amount_cny: string;
  total_bdt: string;
  payee_id: string;
  payee_name: string;
  quote_id: string | null;
  rate_bdt_per_cny: string | null;
  memo: string;
  expires_at: string;
  status: 'draft' | 'blocked' | 'approved' | 'executed' | 'expired' | 'cancelled';
  checks: Check[];
  created_by: string;
  required_approvers: Role[];
  approved_by: Role[];
  withdrawals: string[];
  summary: Lang3;
  draft_hash: string;
  passkey_approvals?: PasskeyApproval[];
  is_passkey_signed?: boolean;
  uetr?: string | null;
  iso_msg_id?: string | null;
  cop_verification?: CopVerification;
};

export type Lang3 = { en: string; bn: string; zh: string };

export type CostBreakdown = {
  route: string;
  delivered_cny: string;
  total_bdt: string;
  mid_value_bdt: string;
  overhead_bdt: string;
  overhead_pct: string;
  card_transactions: number;
  lines: { label: string; bdt: string }[];
  notes: string[];
};

export type TuitionPlan = {
  amount_cny: string;
  deadline: string;
  send_by: string;
  days_left_to_send: number;
  status: 'on_track' | 'urgent' | 'urgent_no_buffer' | 'at_risk_late';
  transfer_days: number;
  buffer_days: number;
  options: (CostBreakdown & { bank: string; quote_id: string; sample: boolean; basis: QuoteBasis; fees_assumed: boolean; rate_source: string; rate_date: string })[];
  best_quote_id: string;
  savings_best_vs_worst_bdt: string;
  wait_risk: null | {
    pay_now_bdt: string;
    if_wait_low_bdt: string;
    if_wait_high_bdt: string;
    level: number;
    horizon_days: number;
    honest_note: string;
    backtest?: { empirical_coverage: number; tests: number } | null;
  };
  data_is_sample: boolean;
  data_quality: DataQuality;
};

export type LivingOption = {
  tt_cny: string;
  bank: string | null;
  quote_id: string | null;
  atm_withdrawals_cny: string[];
  total_bdt: string;
  overhead_bdt: string;
  feasible: boolean;
  violations: string[];
  cap_usage: {
    card_tx_after: number;
    card_tx_cap: number;
    card_bdt_after: string;
    card_bdt_cap: string;
    living_remit_usd_after: string;
    living_remit_usd_cap: string;
  };
};

export type LivingPlan = {
  feasible: boolean;
  best: LivingOption | null;
  baseline_all_atm: LivingOption;
  savings_vs_all_atm_bdt: string | null;
  baseline_feasible: boolean;
  steps: string[];
  limits: Record<string, string | number>;
  data_is_sample: boolean;
  data_quality: DataQuality;
};

export type TimelineItem = {
  type: 'tuition_due' | 'endorsement_expiry' | 'student_file_renewal' | 'living_money';
  title: string;
  amount_cny?: string;
  due?: string;
  send_by?: string;
  days_to_send_by?: number;
  days_left?: number;
  warn?: boolean;
};

export type Timeline = {
  today: string;
  items: TimelineItem[];
  card_usage: { month: string; tx_used: number; tx_cap: number; bdt_used: string; bdt_cap: string };
  data_is_sample: boolean;
  data_quality: DataQuality;
  card: Card;
};

export type QuoteBasis = 'published' | 'real_payment' | 'user_quote' | 'estimate';

export type DataQuality = {
  mid: 'live' | 'saved' | 'fixture';
  mid_as_of: string;
  mid_source: string;
  bdt_per_cny: string;
  bank_quotes: 'estimated' | 'mixed' | 'published';
  quotes?: { bank: string; basis: QuoteBasis; as_of: string; fees_assumed: boolean }[];
};

export type StudentFileFee = {
  bank_id: string;
  bank: string;
  opening_bdt: string | null;
  renewal_bdt: string | null;
  confidence: string;
  source: string;
  url: string;
};

export type RateWatch = {
  bank_id: string;
  sheets: number;
  from: string;
  to: string;
  series: { date: string; market: number; bank: number; markup_pct: number }[];
  markup: { median: number; p25: number; p75: number; low: number; high: number };
  latest: { date: string; markup_pct: number; position: 'high' | 'usual' | 'low'; share_of_days_cheaper_pct: number };
  timing_backtest: { rule: string; cases: number; cheaper_cases: number; mean_saving_pct: number | null; saving_per_lakh_bdt: number | null };
};

export type BankPrices = {
  quotes: {
    quote_id: string;
    bank: string;
    basis: QuoteBasis;
    bdt_per_cny: string;
    markup_pct: string;
    as_of: string;
    rate_source: string;
    fees_assumed: boolean;
    fee_example: { for_bdt: string; total_bdt: string; lines: { label: string; bdt: string }[] };
  }[];
  student_file_fees: StudentFileFee[];
  published_history: { date: string; bank_id: string; cny_tt_selling: string; cny_bank_mid: string }[];
  rate_watch: RateWatch | null;
  quality: DataQuality['bank_quotes'];
  fees_reviewed: string | null;
};

export type Card = {
  last4: string;
  owner: string;
  label: string;
  status: 'active' | 'frozen' | 'lost';
  reason: string | null;
  changed_at: string | null;
  replacement_last4: string | null;
};

export type FxPoint = { date: string; bdt_per_cny: number };

export type FxOverview = {
  mid: { bdt_per_cny: string; as_of: string; source: string };
  status: string;
  history_days: number;
  change_pct: { '90d': number | null; '365d': number | null };
  horizons: Record<string, { range: { low: number; high: number; spot: number } | null; backtest: { empirical_coverage: number; tests: number } | null }>;
  method: string;
  caveat: string;
};

export type Account = { id: string; owner: string; label: string; currency: string; balance: string };
export type Accounts = {
  now: string;
  accounts: Account[];
  pending: { id: string; draft_id: string; to: string; amount_cny: string; arrives_at: string }[];
};

export type AuditEntry = {
  seq: number;
  ts: string;
  sim_time: string | null;
  event: string;
  actor: string;
  permission_level: string;
  data: Record<string, unknown>;
  prev_hash: string;
  hash: string;
};

export type Flag = { category: string; term: string; severity: string; advice: string };

export type CorridorParam = { value: string; confidence: string; source: string; note: string };

export type Insight = {
  id: string;
  type: string;
  severity: 'info' | 'warn' | 'alert';
  title: string;
  body: string;
  savings_bdt: string | null;
  action: { screen: string; mode?: string; need_cny?: string; op?: 'freeze' | 'report_lost'; last4?: string; item?: string } | null;
  txn_ids: string[];
  translated?: boolean;
};

export type InboxSummary = { month: string; messages: number; dropped: number; transactions: number; spent_bdt: string; fees_bdt: string };

export type InboxTxn = {
  id: string;
  received_at: string;
  sender: string;
  amount: string;
  currency: 'BDT' | 'CNY' | 'USD';
  direction: 'debit' | 'credit' | null;
  kind: string;
  owner: string;
  bdt_value: string;
  bdt_is_estimate: boolean;
  counterparty: string | null;
  parser: string;
  counted_on_card: boolean;
  notes: string[];
};

export type StoredMessage = { id: string; source: string; sender: string; received_at: string; text: string; otp: boolean; flags: Flag[]; txn_id: string | null };

export type IngestResult = { kept: boolean; reason?: string; message?: StoredMessage; transaction?: InboxTxn | null; flags?: Flag[] };

export type ChatSignal = 'refused' | 'corrected' | 'drafted' | 'cancelled' | 'checked' | 'card_locked' | 'clarify' | 'offline';
export type ChatChoice = { kind: 'purpose'; value: 'tt_tuition' | 'tt_living' } | { kind: 'amount'; value: string } | { kind: 'cancel' };
export type ChatReply = { reply: string; mode: 'llm' | 'fallback'; signals?: ChatSignal[]; choices?: ChatChoice[]; actions: ({ type: 'draft'; draft_id: string; status: string } | { type: 'card'; last4: string; status: string } | { type: 'renewal'; item: string; case_id: string } | { type: 'mandate'; proposal_id: string; status: string })[]; tools_used: string[]; firewall?: FirewallVerdict };

export type Sources = Record<string, { available: boolean; note: string; path?: string; header?: string }> & { privacy: string[] };

export type RenewalStep = {
  id: string;
  owner: 'student' | 'parent' | 'bank';
  due: string;
  days_left: number;
  title: string;
  detail: string;
  status: 'todo' | 'done';
  state: 'done' | 'overdue' | 'due_soon' | 'upcoming';
};

export type RenewalDoc = { key: string; en: string; zh?: string; bn: string; confidence: string; source: string };

export type RenewalCase = {
  id: string;
  item: 'endorsement_expiry' | 'student_file_expiry';
  label: { en: string; bn: string; zh: string };
  expiry: string;
  days_to_expiry: number;
  status: 'open' | 'completed';
  late: boolean;
  new_expiry: string | null;
  next_step: string | null;
  steps: RenewalStep[];
  documents: { university: RenewalDoc[]; bank: RenewalDoc[] };
  messages: { university_email: { en: string; zh: string }; parent_message: { bn: string; en: string } };
  note: string;
};

export type PassportEntry = {
  kind: 'tuition' | 'living_transfer' | 'renewal';
  date: string;
  payee: string;
  amount_cny: string | null;
  due: string | null;
  arrived: string | null;
  on_time: boolean | null;
  audit_seq: number;
};

export type Passport = {
  id: string;
  holder: { name: string; university: string; corridor: string };
  issued_at: string;
  valid_until: string;
  include_amounts: boolean;
  stats: { payments: number; renewals: number; with_deadline: number; on_time: number; on_time_pct: number | null; months_active: number; total_cny: string | null };
  entries: PassportEntry[];
  disclaimer: string;
  signature: string;
  verify_url: string;
  qr_svg: string;
};

export type DocumentResult = {
  doc_type: 'fee_notice' | 'document_checklist' | 'bank_form' | 'residence_permit' | 'other';
  title: string;
  language: string;
  summary_en: string;
  summary_local: string;
  amounts: { label: string; amount: string; currency: string | null }[];
  amounts_dropped: number;
  deadlines: { label: string; date: string | null; as_written: string }[];
  checklist: { original: string; english: string }[];
  transcript: string;
  flags: Flag[];
  suggestion: { type: 'set_tuition'; amount_cny: string; deadline: string; note: string } | null;
  privacy: string;
};

// ---- the loop: Sense → Plan → Act → Prove ----------------------------------------------------
export type NoteRef = {
  screen?: 'draft' | 'topup' | 'family' | 'renewal' | 'proof' | 'plan' | 'emergency' | 'save';
  release_id?: string;
  draft_id?: string;
  amount_cny?: string;
  item?: 'endorsement_expiry' | 'student_file_expiry';
  proposal_id?: string;
  mandate_id?: string;
  mode?: string;
};

export type Note = {
  id: string;
  at: string;
  audience: 'parent' | 'student' | 'both';
  kind: 'did' | 'needs_you' | 'warning' | 'info';
  key: string;
  title: string;
  body: string;
  ref: NoteRef;
};

export type MandateView = {
  id: string;
  payee_id: string;
  max_bdt_per_payment: string;
  max_bdt_per_period: string;
  period: 'month' | 'rolling';
  period_days: number;
  expires_at: string;
  revoked: boolean;
  active: boolean;
  spent_in_period_bdt: string;
  left_in_period_bdt: string;
  payments: number;
  kinds: string[];
  auto_topup: boolean;
  signed_by: Role[];
  proposal_id: string | null;
  proposal_hash: string | null;
  summary: Lang3 | null;
};

export type TopupDecision = {
  send_on: string;
  lands: string;
  amount_cny: string;
  bridge_cny: string;
  next_chance: string;
  wait_would_land: string;
  low_on: string;
  safety_days: number;
  closures: string[];
  reason: string;
};

export type Runway = {
  balance_cny: string;
  daily_spend_cny: string;
  days_left: number | null;
  runs_out_on: string | null;
  in_transit: { arrives: string; amount_cny: string }[];
  card_works_until: string;
  card_usable: boolean;
  send_today: TopupDecision | null;
  mandate: MandateView | null;
  stuck_days: number;
  bank_open_today: { BD: boolean; CN: boolean };
};

export type NeedItem =
  | { type: 'approve_draft' | 'send_draft'; draft_id: string; kind: Draft['kind']; amount_cny: string; total_bdt: string; payee_name: string }
  | { type: 'sign_mandate'; proposal_id: string; summary: string }
  | { type: 'confirm_safe'; check_id: string; asked_at: string }
  | { type: 'approve_release'; release_id: string; amount_cny: string; available_at: string };

export type SafetyCheck = { id: string; asked_by: Role; asked_at: string; status: 'open' | 'safe'; answered_at: string | null };
export type EmergencyGuide = { title: string; steps: string[] };
export type EmergencyView = {
  plan: { today: string; balance_cny: string; days_left: number | null; card_usable: boolean; bridge_needed_cny: string; urgent_lands_on: string };
  text: { headline: string; options: { kind: 'shield' | 'card_atm' | 'on_the_way' | 'urgent_transfer' | 'local_bridge'; text: string }[] };
  guides: { scam_call: EmergencyGuide; family_call: EmergencyGuide; card_lost: EmergencyGuide };
  card: { last4: string; status: string };
  safety_checks: SafetyCheck[];
};

export type ShieldSummary = { balance_cny: string; target_cny: string; pct_of_target: number; days_of_living: string; rule_on: boolean };

export type Feed = { now: string; runway: Runway; needs_you: NeedItem[]; notes: Note[]; shield: ShieldSummary | null };

export type Proposal = {
  id: string;
  payee_id: string;
  payee_label: string;
  max_bdt_per_payment: string;
  max_bdt_per_period: string;
  period: 'month' | 'rolling';
  period_days: number;
  valid_until: string;
  required_signers: Role[];
  signatures: Partial<Record<Role, string>>;
  missing_signers: Role[];
  status: 'proposed' | 'needs_changes' | 'active' | 'superseded';
  errors: string[];
  notes: string[];
  summary: Lang3;
  hash: string;
  parser: 'rules' | 'llm';
  text: string;
  mandate_id: string | null;
  mandate?: MandateView;
  autopilot?: { type: string; amount_cny?: string; draft_id?: string }[];
};

export type StuckPeriod = { from: string; to: string; days: number; reasons: string[] };

export type YearStrategy = {
  name: 'today' | 'sathi';
  stuck_days: number;
  stuck_periods: StuckPeriod[];
  transfers: { send_on: string; lands: string; amount_cny: string; total_bdt: string; bank: string; why: string; closures: string[] }[];
  atm: { date: string; amount_cny: string; total_bdt: string }[];
  cost: {
    delivered_cny: string;
    total_bdt: string;
    rate_bdt: string;
    fees_bdt: string;
    overhead_bdt: string;
    overhead_pct: string;
    transfers: number;
    atm_withdrawals: number;
  };
};

export type YearEvent = {
  date: string;
  type: 'transfer_send' | 'atm_bridge' | 'card_stops' | 'tuition_send_by' | 'bank_closure' | 'stuck_without_sathi';
  amount_cny?: string;
  total_bdt?: string;
  bank?: string;
  lands?: string;
  why?: string;
  name?: string;
  name_bn?: string;
  name_zh?: string;
  country?: 'BD' | 'CN';
  to?: string;
  days?: number;
  reasons?: string[];
  deadline?: string;
  confidence?: string;
};

export type CostTruth = {
  bank: string;
  amount_cny: string;
  bdt_per_cny_paid: string;
  mid_avg: string;
  mid_low: string;
  mid_high: string;
  paid_bdt: string;
  rate_markup_bdt: string;
  rate_markup_pct: string;
  fee_bdt: string;
  fee_vs_rate: string | null;
  fee_note: string | null;
  source: string;
  note: string;
  window: [string, string];
  published_same_window: { bank_id: string; sheets: number; avg: string; low: string; high: string; paid_vs_published_avg_pct: string; paid_below_every_sheet: boolean } | null;
};

export type YearShield = {
  income_month_cny: string;
  shield_cny: string;
  rule_is_suggestion: boolean;
  saving: { pct: number; target_cny: string } | null;
  end_cny: string | null;
  used_cny: string | null;
  saved_cny?: string;
};

export type YearPlan = {
  horizon: { from: string; to: string; days: number };
  headline: {
    stuck_days_today: number;
    stuck_days_sathi: number;
    overhead_today_bdt: string;
    overhead_sathi_bdt: string;
    overhead_today_pct: string;
    overhead_sathi_pct: string;
    saved_bdt: string;
    fees_share_today_pct: string | null;
  };
  strategies: { today: YearStrategy; sathi: YearStrategy };
  events: YearEvent[];
  cost_truth: CostTruth[];
  student_file_fees: StudentFileFee[];
  assumptions: ({ name: string } & CorridorParam)[];
  mandate: MandateView | null;
  shield?: YearShield;
  data_quality: DataQuality;
  method: string;
};

export type StuckStats = { zero_share_pct: number; median: number; p90: number; worst: number; mean: number };
export type WhatIfKey = 'taka_weakens_10' | 'spending_plus_30' | 'transfers_3_days_late' | 'holidays_2_days_later' | 'all_at_once' | 'dollar_crisis';
export type StressTest = {
  runs: number;
  seed: number;
  assumptions: Record<string, string>;
  stuck_days: { today: StuckStats; sathi: StuckStats };
  sathi_worst: { stuck_days: number; holiday_shift: number; periods: { from: string; to: string; days: number; reasons: string[] }[] } | null;
  what_if: {
    key: WhatIfKey;
    stuck_days_sathi: number;
    stuck_days_today: number;
    stuck_days_sathi_shield?: number | null;
    shield_needed_cny?: string;
    basis?: 'median_start';
    worst?: { from: string; stuck_today: number; stuck_sathi: number; stuck_sathi_shield: number | null };
    family_pays_bdt: string;
    change_bdt: string;
    overhead_pct: string;
    overhead_pct_today: string;
  }[];
  crisis?: CrisisTest;
  method: string;
};

export type Receipt = {
  draft: Draft;
  authority:
    | { type: 'approvals'; level: string; executed_by: string; approved_by: Role[]; draft_hash: string; passkey_signed?: boolean }
    | { type: 'mandate'; level: string; executed_by: string; mandate_id: string; signed_by: Role[]; proposal_hash: string | null; draft_hash: string }
    | null;
  sent: { seq: number; hash: string; sim_time: string; permission_level: string; arrives_at?: string } | null;
  landed: { seq: number; hash: string; sim_time: string } | null;
  uetr?: string | null;
  iso20022?: {
    uetr: string;
    msg_id: string;
    schema: string;
    valid: boolean;
    checks_passed: number;
    origin_bic: string;
    origin_bank_name: string;
    dest_bic: string;
    dest_bank_name: string;
    created_at: string;
    regulatory_reporting?: string;
  } | null;
};

export type Iso20022Record = {
  uetr: string;
  msg_id: string;
  draft_id: string;
  xml: string;
  schema: string;
  validation: {
    valid: boolean;
    schema: string;
    uetr: string;
    msg_id: string;
    amount: string;
    currency: string;
    checks_passed: number;
    checks: string[];
    errors: string[];
  };
  origin_bic: string;
  origin_bank_name: string;
  dest_bic: string;
  dest_bank_name: string;
  created_at: string;
  regulatory_reporting: string;
};

export function getIso20022(base: string, role: Role, draftId: string) {
  return api<Iso20022Record>(base, role, `/receipts/${draftId}/iso20022`);
}

export type FuzzReport = {
  timestamp: string;
  total_attacks: number;
  violations_detected: number;
  duration_seconds: number;
  attacks_per_second: number;
  deepseek_tokens_consumed: number;
  deepseek_cost_usd: number;
  attacks_by_vector: Record<string, number>;
  invariant_status: Record<string, { desc: string; violations: number }>;
  hostile_steps?: number;
  payments_completed?: number;
  payments_under_mandate?: number;
  refusals?: number;
  seed?: number;
  mutants?: { mutant: string; doc: string; expected: string; caught: boolean; first_seen_at_step: number | null }[];
};

// ---- double-entry books (GET /ledger) ----------------------------------------
export type LedgerView = {
  books: {
    ok: boolean;
    balanced: boolean;
    reconciled: boolean;
    trial_balance: Record<string, string>;
    mismatches: { account: string; books: string; shown: string }[];
    booked_twice: string[];
    entries: number;
  };
  accounts: { id: string; label: string; currency: string; owner: string; books: string; shown: string }[];
  entries: { id: string; at: string; event: string; ref: string | null; postings: { account: string; currency: string; amount: string }[] }[];
  payments_booked: number;
  idempotent_replays: number;
};

// ---- open-banking connections (GET /banks) -------------------------------------
export type BankConsent = {
  id: string;
  connector: string;
  bank: string;
  country: string;
  standard: string;
  holder: Role;
  permissions: { id: string; text: string }[];
  days: number;
  created_at: string;
  expires_at: string;
  days_left: number;
  status: 'AwaitingAuthorisation' | 'Authorised' | 'Revoked' | 'Expired';
  authorised_at: string | null;
  revoked_at: string | null;
  reads: number;
  last_read: string | null;
  hash: string;
  can_move_money: false;
};
export type BanksView = {
  connectors: { id: string; bank: string; country: string; standard: string; holder: Role; yours: boolean; active: BankConsent | null }[];
  consents: BankConsent[];
  permissions: { id: string; text: string }[];
  max_days: number;
};
export type BankRead = {
  consent_id: string;
  bank: string;
  standard: string;
  Data: { Account: { AccountId: string; Nickname: string; Currency: string; Balance?: { Amount: { Amount: string; Currency: string } } }[] };
};

// ---- privacy & data rights (GET /privacy) ----------------------------------------
export type PrivacyView = {
  held: { id: string; count: number; deletable: boolean; what: string; why: string }[];
  recipients: { id: string; name: string; law: string; what: string[]; why: string; when: string; kept_there: string; switch: string }[];
  not_stored: string[];
  switches: { ai: boolean; ai_asked: boolean; ai_available: boolean; whatsapp: boolean; banks: boolean };
  rights: string[];
  law: string;
};

export type TaintStatus = {
  taint_tracking_active: boolean;
  defense_standard: string;
  enforcement_mode: string;
  total_entities_tracked: number;
  untrusted_entities: number;
  endorsed_entities: number;
  total_injections_blocked: number;
  recent_blocks: {
    timestamp: string;
    sink: string;
    parameter: string;
    reason: string;
  }[];
};

export type FirewallViolation = {
  violation_type: 'otp_code' | 'payment_card' | 'bank_account' | 'cross_role_privacy' | 'system_prompt_leak' | 'secret_credential';
  severity: 'low' | 'medium' | 'critical';
  description: string;
  snippet_masked: string;
  action: 'redacted' | 'blocked';
};

export type FirewallVerdict = {
  passed: boolean;
  action_taken: 'allow' | 'redact' | 'block';
  original_length: number;
  filtered_length: number;
  filtered_text: string;
  violations: FirewallViolation[];
  actor: string;
  checked_at: string;
  latency_ms: number;
};

export type FirewallTelemetry = {
  status: string;
  mode: string;
  total_inspections: number;
  total_violations: number;
  blocked_count: number;
  redacted_count: number;
  category_counts: Record<string, number>;
  recent_interceptions: {
    timestamp: string;
    actor: string;
    action: string;
    violations_count: number;
    violations: FirewallViolation[];
  }[];
};

export type FirewallTestResponse = {
  verdict: FirewallVerdict;
  telemetry: FirewallTelemetry;
};

// ---- Earn & Save: the student's own money abroad and the Shield ----------------------------------------
export type IncomeSource = {
  id: string;
  kind: 'stipend' | 'work_study' | 'other';
  label: string;
  amount_cny: string;
  every: 'month' | 'week';
  pay_day: number;
  hours_per_week: string | null;
  permission: boolean;
  added_on: string;
  status: 'ok' | 'at_risk';
  monthly_cny: string;
  checks: Check[];
};

export type ShieldRelease = {
  id: string;
  amount_cny: string;
  reason: 'emergency' | 'planned';
  requested_by: Role | 'agent';
  requested_at: string;
  available_at: string;
  needs_family: boolean;
  family_approved_at: string | null;
  status: 'waiting' | 'released' | 'cancelled';
  released_at: string | null;
  note: string;
  released_now_cny?: string;
};

export type ShieldProjection = { pct: number; target_cny: string; reaches_target_on: string | null; points: { date: string; shield_cny: string }[] };

export type SavingsRule = {
  id: string;
  owner: 'student';
  shield_pct: number;
  target_cny: string;
  cooling_off_hours: number;
  family_lock: boolean;
  share_with_family: boolean;
  valid_until: string;
  emergency_release: boolean;
  to_account: 'student_shield';
  created_at: string;
  created_by: string;
  text: string;
  errors: string[];
  notes: string[];
  signatures: { student?: string };
  status: 'proposed' | 'needs_changes' | 'active' | 'revoked' | 'superseded' | 'expired';
  summary: Lang3;
  hash: string;
  projection?: ShieldProjection | null;
};

export type TakaLens = { amount_cny: string; bdt: string; days_of_living: string };

export type WantsWeek = {
  from: string;
  to: string;
  wants_cny: string;
  needs_cny: string;
  count: number;
  by_category: { category: string; label: string; cny: string }[];
  allowance_cny: string;
  left_cny: string;
  over_cny: string;
  lens: TakaLens;
  over_lens: TakaLens;
};

export type ShieldEvent = { seq: number; hash: string; event: string; sim_time: string | null; actor: string; level: string; amount_cny: string | null };

export type SavingsView = {
  now: string;
  role: Role | 'agent';
  shared_with_family: boolean;
  shield: { balance_cny: string; target_cny: string; free_cny: string; pct_of_target: number; days_of_living: string; full: boolean } | null;
  rule: SavingsRule | null;
  terms: { rule_id: string; cooling_off_hours: number; family_lock: boolean; share_with_family: boolean; status: string } | null;
  history: ShieldEvent[];
  family_rate: { bdt_per_cny: string; basis: string };
  releases: ShieldRelease[];
  // student only
  income?: { sources: IncomeSource[]; monthly_cny: string; next_pay: { date: string; amount_cny: string; label: string } | null };
  wants?: WantsWeek;
  projection?: ShieldProjection | null;
  proposal?: SavingsRule | null;
  suggested?: { pct: number; target_cny: string; cooling_off_hours: number; projection: ShieldProjection } | null;
  categories?: { key: string; label: string; kind: 'want' | 'need' }[];
  work_rules?: ({ name: string } & CorridorParam)[];
};

export type SpendResult = { amount_cny: string; paid_cny: string; category: string; kind: 'want' | 'need'; label: string; lens: TakaLens; week: WantsWeek };

export type HundiOption =
  | { key: 'hundi'; legal: false; total_bdt: string; extra_bdt: string; rate_bdt_per_usd: string; premium_bdt_per_usd: string; premium_source: string }
  | { key: 'bank_once'; legal: true; bank: string; total_bdt: string; extra_bdt: string; fees_bdt: string; rate_markup_bdt: string; send_on: string; lands: string }
  | { key: 'shield'; legal: true; amount_cny: string; total_bdt: string; extra_bdt: string; available_on: string; covers_all: boolean }
  | { key: 'planned'; legal: true; send_on: string; lands: string; amount_cny: string; extra_bdt: string };

export type HundiCheck = {
  amount_cny: string;
  amount_usd: string;
  mid_bdt: string;
  mid_bdt_per_usd: string;
  options: HundiOption[];
  verdict: 'use_shield' | 'shield_then_bank' | 'wait_for_planned' | 'bank';
  bank_costs_more_on_paper_bdt: string | null;
  shield_saves_vs_hundi_bdt: string | null;
  risks: { key: string; text: string; confidence: string; source: string }[];
  legal_routes: { key: string; text: string; confidence: string; source: string }[];
  honest_note: string;
  data_is_sample: boolean;
};

export type CrisisTest = {
  weeks: number;
  starts_tested: number;
  first_start: string;
  last_start: string;
  zero_share_pct: { today: number | null; sathi: number | null; sathi_shield: number | null };
  median_stuck: { today: number | null; sathi: number | null; sathi_shield: number | null };
  worst: { from: string; to: string; stuck_today: number; stuck_sathi: number; stuck_sathi_shield: number | null; shield_on_start_cny: string; shield_needed_cny: string };
  protected_from: string | null;
  with_shield: boolean;
  rule_is_suggestion?: boolean;
  student_money_shown?: boolean;
  saving: { pct: number; target_cny: string } | null;
  method: string;
};

export type JudgeTask = {
  id: string;
  criterion: 'task' | 'security' | 'interaction';
  title: string;
  goal: string;
  steps: { who: string; did: string; got: string }[];
  checks: { what: string; ok: boolean }[];
  value: string | null;
  evidence: { seq: number | null; event: string; hash: string; chain_valid: boolean } | null;
  error: string | null;
  ms: number;
  passed: boolean;
};
export type JudgeRun = {
  summary: Record<'task' | 'security' | 'interaction', { passed: number; total: number }>;
  passed: number;
  total: number;
  tasks: JudgeTask[];
};
export type ValueSummary = {
  stuck_days_today: number;
  stuck_days_sathi: number;
  saved_bdt: string;
  stopped: number;
  flagged_messages: number;
  payments: number;
};
