/** Typed client for the Sathi backend. All money values arrive as strings (server uses Decimal). */

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

export type ChatReply = { reply: string; mode: 'llm' | 'fallback'; actions: ({ type: 'draft'; draft_id: string; status: string } | { type: 'card'; last4: string; status: string } | { type: 'renewal'; item: string; case_id: string } | { type: 'mandate'; proposal_id: string; status: string })[]; tools_used: string[] };

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
  screen?: 'draft' | 'topup' | 'family' | 'renewal' | 'proof' | 'plan';
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
  | { type: 'sign_mandate'; proposal_id: string; summary: string };

export type Feed = { now: string; runway: Runway; needs_you: NeedItem[]; notes: Note[] };

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
  data_quality: DataQuality;
  method: string;
};

export type Receipt = {
  draft: Draft;
  authority:
    | { type: 'approvals'; level: string; executed_by: string; approved_by: Role[]; draft_hash: string }
    | { type: 'mandate'; level: string; executed_by: string; mandate_id: string; signed_by: Role[]; proposal_hash: string | null; draft_hash: string }
    | null;
  sent: { seq: number; hash: string; sim_time: string; permission_level: string; arrives_at?: string } | null;
  landed: { seq: number; hash: string; sim_time: string } | null;
};
