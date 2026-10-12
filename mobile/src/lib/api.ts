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
  status: 'draft' | 'blocked' | 'approved' | 'executed' | 'expired';
  checks: Check[];
  created_by: string;
  required_approvers: Role[];
  approved_by: Role[];
  withdrawals: string[];
};

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
  options: (CostBreakdown & { bank: string; quote_id: string; sample: boolean })[];
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

export type DataQuality = {
  mid: 'live' | 'saved' | 'fixture';
  mid_as_of: string;
  mid_source: string;
  bdt_per_cny: string;
  bank_quotes: 'estimated' | 'mixed' | 'real';
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
  action: { screen: string; mode?: string; need_cny?: string; op?: 'freeze' | 'report_lost'; last4?: string } | null;
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

export type ChatReply = { reply: string; mode: 'llm' | 'fallback'; actions: ({ type: 'draft'; draft_id: string; status: string } | { type: 'card'; last4: string; status: string })[]; tools_used: string[] };

export type Sources = Record<string, { available: boolean; note: string; path?: string; header?: string }> & { privacy: string[] };
