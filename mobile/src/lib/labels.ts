export const STATUS_TONE = { draft: 'info', approved: 'ok', executed: 'ok', blocked: 'block', expired: 'neutral' } as const;

export const KIND_LABEL = {
  tt_tuition: 'Tuition transfer',
  tt_living: 'Living money transfer',
  atm_plan: 'ATM withdrawals',
} as const;
