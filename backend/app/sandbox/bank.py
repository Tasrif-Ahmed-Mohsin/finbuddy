"""Sandbox bank: simulated accounts, clock, transfer delays and fees. NO real money.

Rules of the sandbox:
  * It only executes drafts handed over by the API after approval/mandate checks passed.
  * Bank transfers leave on the next Bangladeshi bank day and land after the corridor's transfer days
    (field data: ~7) on the next Chinese bank day (app/data/bank_holidays.yaml), on a simulated clock
    that can be fast-forwarded for demos.
  * Each simulated day the student spends their daily living money in China (cash first, then the
    Chinese account). A day they cannot cover is recorded as a "stuck day".
  * The student's own income (stipend or approved campus job) lands in the Chinese account; the Shield is a
    separate savings pocket of the same account. It is NOT counted as money to spend: it is kept for the days
    money from home cannot arrive (Earn & Save).
  * Every operation writes to the hash-chained audit log: this is the execution evidence.
  * Every movement of money is also a balanced double-entry journal entry (app/sandbox/ledger.py). Account balances
    change ONLY through those entries, the books are checked after every operation (trial balance zero per
    currency, every account reconciled), and a payment draft is booked at most once (exactly-once).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from app.audit.log import AuditLog
from app.corridors.loader import Corridor
from app.engines.year_plan import BankCalendar
from app.money import q2
from app.sandbox.ledger import ZERO, Ledger
from app.security.compliance import Payee

FX_DESK, TRANSIT, SPENDING, INCOME, OPENING = "fx_desk", "transit:CNY", "world:spending", "world:income", "equity:opening"


@dataclass
class Account:
    id: str
    owner: str  # student | parent | university
    label: str
    currency: str
    balance: Decimal

    def to_dict(self) -> dict:
        return {"id": self.id, "owner": self.owner, "label": self.label, "currency": self.currency, "balance": str(q2(self.balance))}


@dataclass
class PendingTransfer:
    id: str
    draft_id: str
    to_account_id: str
    amount: Decimal
    currency: str
    arrives_at: datetime


@dataclass
class Card:
    """A payment card in the sandbox. Card controls mirror real banking apps (freeze / unfreeze / report lost)."""
    last4: str
    owner: str
    label: str
    status: str = "active"  # active | frozen | lost
    reason: str | None = None
    changed_at: str | None = None
    replacement_last4: str | None = None

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class CardUsage:
    """Bangladeshi student card usage this month (the 5 lakh BDT / 30 transactions limits)."""
    month: str
    tx_count: int = 0
    bdt_charged: Decimal = Decimal(0)


@dataclass
class SandboxBank:
    corridor: Corridor
    audit: AuditLog
    clock: datetime
    accounts: dict[str, Account] = field(default_factory=dict)
    payees: dict[str, Payee] = field(default_factory=dict)
    pending: list[PendingTransfer] = field(default_factory=list)
    card: CardUsage | None = None
    living_remitted_usd: dict[str, Decimal] = field(default_factory=dict)  # month -> USD
    cards: dict[str, Card] = field(default_factory=dict)
    calendar: BankCalendar | None = None
    daily_spend_cny: Decimal = Decimal(0)  # simulated living spending in China (0 = off)
    stuck_days: list[str] = field(default_factory=list)
    spend_log: list[Decimal] = field(default_factory=list)  # what the student needed each day
    # (when, amount, category, need|want): purchases the student logged. Kept apart from spend_log on purpose: wants paid
    # from the student's own pay must not look like faster LIVING spending, or the autopilot would send more from home.
    wants_log: list[tuple] = field(default_factory=list)
    ledger: Ledger = field(default_factory=Ledger)
    _seq: int = 0
    _cny_per_usd: Decimal = Decimal("6.95")  # set from market data at seed time

    # ---- helpers -----------------------------------------------------------
    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}-{self._seq:04d}"

    @property
    def month(self) -> str:
        return self.clock.strftime("%Y-%m")

    def card_usage(self) -> CardUsage:
        if self.card is None or self.card.month != self.month:
            self.card = CardUsage(self.month)
        return self.card

    def log(self, event: str, actor: str, level: str, data: dict) -> dict:
        return self.audit.append(event, actor, level, data, sim_time=self.clock.isoformat())

    # ---- the books -------------------------------------------------------------
    def _book(self, event: str, ref: str | None, legs: list[tuple[str, str, Decimal]]) -> None:
        """Book one balanced entry, then move the customer balances it touches. The only way balances change."""
        entry = self.ledger.post(self.clock.isoformat(), event, ref, legs)
        for leg in entry.postings:
            if leg.account in self.accounts:
                self.accounts[leg.account].balance += leg.amount

    def booked(self, draft_id: str) -> bool:
        return draft_id in self.ledger.refs_of("payment_sent")

    def check_books(self) -> dict:
        """Trial balance (each currency sums to zero) and reconciliation (books = what each account shows)."""
        trial = self.ledger.trial_balance()
        mismatches = []
        for a in self.accounts.values():
            in_books = self.ledger.balance(a.id, a.currency)
            if in_books != a.balance:
                mismatches.append({"account": a.id, "books": str(in_books), "shown": str(a.balance)})
        transit = sum((t.amount for t in self.pending), ZERO)
        if self.ledger.balance(TRANSIT, "CNY") != transit:
            mismatches.append({"account": TRANSIT, "books": str(self.ledger.balance(TRANSIT, "CNY")), "shown": str(transit)})
        sent = self.ledger.refs_of("payment_sent")
        twice = sorted({r for r in sent if sent.count(r) > 1})
        return {"balanced": all(v == 0 for v in trial.values()), "trial_balance": {k: str(v) for k, v in trial.items()},
                "reconciled": not mismatches, "mismatches": mismatches, "booked_twice": twice,
                "entries": len(self.ledger.entries), "ok": all(v == 0 for v in trial.values()) and not mismatches and not twice}

    # ---- operations --------------------------------------------------------
    def execute_tt(self, draft_id: str, from_account_id: str, payee_id: str, amount_cny: Decimal,
                   total_bdt: Decimal, actor: str, level: str, purpose: str) -> dict:
        src = self.accounts[from_account_id]
        payee = self.payees[payee_id]
        if self.booked(draft_id):
            raise ValueError(f"{draft_id} is already booked: the bank never books one payment twice")
        if src.currency != "BDT":
            raise ValueError("bank transfers in this sandbox are sent from a BDT account")
        if src.balance < total_bdt:
            raise ValueError(f"insufficient funds: {q2(src.balance)} BDT available, {q2(total_bdt)} BDT needed")
        # taka out to the bank's FX desk, yuan from the FX desk into transit (one balanced leg per currency)
        self._book("payment_sent", draft_id, [(from_account_id, "BDT", -total_bdt), (FX_DESK, "BDT", total_bdt),
                                              (FX_DESK, "CNY", -amount_cny), (TRANSIT, "CNY", amount_cny)])
        days = self.corridor.i("bd_tt_transfer_days")
        if self.calendar:  # leaves on the next Bangladeshi bank day, lands on a Chinese bank day
            leaves = self.calendar.next_open("BD", self.clock.date())
            arrives_at = datetime.combine(self.calendar.arrival(leaves, days), self.clock.time())
        else:
            leaves, arrives_at = self.clock.date(), self.clock + timedelta(days=days)
        transfer = PendingTransfer(
            id=self._next_id("tt"),
            draft_id=draft_id,
            to_account_id=payee.credit_account_id,
            amount=amount_cny,
            currency="CNY",
            arrives_at=arrives_at,
        )
        self.pending.append(transfer)
        if purpose == "living":
            self.living_remitted_usd[self.month] = self.living_remitted_usd.get(self.month, Decimal(0)) + amount_cny / self._cny_per_usd
        return self.log("transfer_sent", actor, level, {
            "transfer_id": transfer.id, "draft_id": draft_id, "from": from_account_id, "payee": payee_id,
            "amount_cny": str(q2(amount_cny)), "debited_bdt": str(q2(total_bdt)),
            "leaves_on": leaves.isoformat(), "arrives_at": transfer.arrives_at.isoformat(), "purpose": purpose,
            "balance_after_bdt": str(q2(src.balance)),
        })

    def execute_atm_withdrawals(self, draft_id: str, card_account_id: str, cash_account_id: str,
                                withdrawals_cny: list[Decimal], total_bdt: Decimal, actor: str, level: str) -> dict:
        card_acct = self.accounts[card_account_id]
        card = next((c for c in self.cards.values() if c.owner == card_acct.owner), None)
        if card and card.status != "active":
            raise ValueError(f"card ending {card.last4} is {card.status}; unfreeze it first")
        usage = self.card_usage()
        tx_cap = self.corridor.i("bd_student_card_tx_cap_per_month")
        bdt_cap = self.corridor.v("bd_student_card_cap_bdt_per_month")
        if usage.tx_count + len(withdrawals_cny) > tx_cap:
            raise ValueError("card transaction cap would be exceeded")
        if usage.bdt_charged + total_bdt > bdt_cap:
            raise ValueError("card monthly BDT cap would be exceeded")
        if card_acct.balance < total_bdt:
            raise ValueError("insufficient funds on the card account")
        if self.booked(draft_id):
            raise ValueError(f"{draft_id} is already booked: the bank never books one payment twice")
        cash = sum(withdrawals_cny, Decimal(0))
        self._book("payment_sent", draft_id, [(card_account_id, "BDT", -total_bdt), (FX_DESK, "BDT", total_bdt),
                                              (FX_DESK, "CNY", -cash), (cash_account_id, "CNY", cash)])
        usage.tx_count += len(withdrawals_cny)
        usage.bdt_charged += total_bdt
        return self.log("atm_withdrawals", actor, level, {
            "draft_id": draft_id, "withdrawals_cny": [str(q2(w)) for w in withdrawals_cny],
            "charged_bdt": str(q2(total_bdt)), "card_tx_used": usage.tx_count, "card_tx_cap": tx_cap,
            "card_bdt_used": str(q2(usage.bdt_charged)), "card_bdt_cap": str(bdt_cap),
        })

    # ---- card controls -------------------------------------------------------
    def set_card_status(self, last4: str, status: str, actor: str, level: str, reason: str | None = None) -> dict:
        card = self.cards[last4]
        if card.status == "lost":
            raise ValueError("this card was reported lost and cannot be reactivated; use the replacement card")
        previous, card.status, card.reason, card.changed_at = card.status, status, reason, self.clock.isoformat()
        if status == "lost":
            card.replacement_last4 = "9034"  # sandbox: a replacement card is ordered
        self.log(f"card_{status}", actor, level, {"card": last4, "from": previous, "to": status, "reason": reason,
                                                  "replacement": card.replacement_last4})
        return card.to_dict()

    # ---- simulated time ---------------------------------------------------------
    def student_cny(self) -> Decimal:
        return self.accounts["student_cash"].balance + self.accounts["student_cn"].balance

    def surprise_expense(self, amount: Decimal, memo: str, actor: str) -> dict:
        """A one-off bill paid from the student's money in China (sandbox only), e.g. a doctor or a deposit."""
        paid = self.take_from_spending(amount, "surprise_expense")
        if self.spend_log:
            self.spend_log[-1] += amount
        self.log("surprise_expense", actor, "SANDBOX", {"amount_cny": str(amount), "paid_cny": str(paid), "memo": memo[:80]})
        return {"amount_cny": str(amount), "paid_cny": str(paid), "unpaid_cny": str(amount - paid),
                "balance_cny": str(self.student_cny())}

    # ---- the student's own money (Earn & Save) ---------------------------------------
    def credit_income(self, source_id: str | None, kind: str, amount: Decimal, actor: str) -> dict:
        """Pay or a stipend lands in the student's own Chinese account (sandbox: the employer or university pays)."""
        self._book("income_received", source_id, [(INCOME, "CNY", -amount), ("student_cn", "CNY", amount)])
        return self.log("income_received", actor, "SANDBOX", {"source_id": source_id, "kind": kind,
                        "amount_cny": str(q2(amount)), "balance_cny": str(q2(self.student_cny()))})

    def move_cny(self, from_id: str, to_id: str, amount: Decimal, actor: str, level: str, event: str, data: dict) -> dict:
        """Move yuan between the student's OWN pockets (spending account ↔ Shield). Nothing leaves the student."""
        own = {"student_cn", "student_cash", "student_shield"}
        if from_id not in own or to_id not in own:
            raise ValueError("the Shield only moves between the student's own accounts")
        src = self.accounts[from_id]
        if amount <= 0 or src.balance < amount:
            raise ValueError(f"not enough money in {src.label}: ¥{q2(src.balance)} available")
        self._book(event, data.get("rule_id") or data.get("reason"), [(from_id, "CNY", -amount), (to_id, "CNY", amount)])
        return self.log(event, actor, level, {**data, "from": from_id, "to": to_id, "amount_cny": str(q2(amount)),
                        "shield_cny": str(q2(self.accounts["student_shield"].balance))})

    def take_from_spending(self, amount: Decimal, event: str = "spending") -> Decimal:
        """Pay from cash first, then the Chinese account. Returns what was actually paid."""
        paid, legs = Decimal(0), []
        for acct_id in ("student_cash", "student_cn"):
            take = min(self.accounts[acct_id].balance, amount - paid)
            if take > 0:
                legs.append((acct_id, "CNY", -take))
                paid += take
        if paid > 0:
            self._book(event, None, legs + [(SPENDING, "CNY", paid)])
        return paid

    def spend_logged(self, amount: Decimal, category: str, kind: str, actor: str) -> dict:
        """A purchase the student logged (or a bank alert showed). The merchant text is never logged, only the category."""
        paid = self.take_from_spending(amount, "spending_logged")
        self.wants_log.append((self.clock, amount, category, kind))
        self.log("spending_logged", actor, "SANDBOX", {"amount_cny": str(q2(amount)), "paid_cny": str(q2(paid)),
                 "category": category, "kind": kind})
        return {"amount_cny": str(q2(amount)), "paid_cny": str(q2(paid)), "unpaid_cny": str(q2(amount - paid)),
                "balance_cny": str(q2(self.student_cny()))}

    def spend_day(self) -> tuple[Decimal, bool]:
        """End of the current day: the student spends today's living money. Returns (spent, stuck)."""
        need = self.daily_spend_cny
        if need <= 0:
            return Decimal(0), False
        self.spend_log = (self.spend_log + [need])[-30:]
        spent = self.take_from_spending(need, "daily_living")
        stuck = spent < need
        if stuck:
            self.stuck_days.append(self.clock.date().isoformat())
        return spent, stuck

    def next_day(self, actor: str = "system") -> list[dict]:
        """Move to the next morning; transfers due by then land."""
        self.clock += timedelta(days=1)
        arrived, events = [], []
        for t in self.pending:
            if t.arrives_at <= self.clock:
                self._book("payment_arrived", t.draft_id, [(TRANSIT, "CNY", -t.amount), (t.to_account_id, "CNY", t.amount)])
                arrived.append(t)
                events.append(self.log("transfer_arrived", actor, "SYSTEM", {
                    "transfer_id": t.id, "draft_id": t.draft_id, "to": t.to_account_id,
                    "amount_cny": str(q2(t.amount)), "arrived_at": t.arrives_at.isoformat(),
                }))
        self.pending = [t for t in self.pending if t not in arrived]
        return events

    def advance(self, days: int, actor: str = "system") -> list[dict]:
        """Fast-forward without the agent (AppState.advance also runs the autopilot each day)."""
        if days < 0 or days > 365:
            raise ValueError("days must be between 0 and 365")
        events = []
        for _ in range(days):
            self.spend_day()
            events += self.next_day(actor)
        self.log("clock_advanced", actor, "SYSTEM", {"days": days, "now": self.clock.isoformat()})
        return events


def seed_demo_bank(corridor: Corridor, audit: AuditLog, start: datetime, cny_per_usd: Decimal) -> SandboxBank:
    """Demo persona: a self-funded Bangladeshi student in China and a parent in Dhaka (fictional)."""
    bank = SandboxBank(corridor=corridor, audit=audit, clock=start)
    bank._cny_per_usd = cny_per_usd
    opening = []
    for acct in (
        Account("parent_bd", "parent", "Parent savings (Dhaka) [sandbox]", "BDT", Decimal("2000000")),
        Account("student_bd_card", "student", "Student File card account (Bangladesh) [sandbox]", "BDT", Decimal("300000")),
        Account("student_cn", "student", "Student's own Chinese bank account [sandbox]", "CNY", Decimal("500")),
        Account("student_cash", "student", "Cash wallet (CNY), from the airport exchange", "CNY", Decimal("1800")),
        Account("student_shield", "student", "Shield: savings pocket of the student's own Chinese account [sandbox]", "CNY",
                Decimal("0")),
        Account("university", "university", "Demo University finance office [sandbox]", "CNY", Decimal("0")),
    ):
        if acct.balance:
            opening.append((acct.id, acct.currency, acct.balance))
        acct.balance = Decimal(0)  # the opening entry below gives each account its starting money
        bank.accounts[acct.id] = acct
    for cur in sorted({c for _, c, _ in opening}):
        legs = [(a, c, v) for a, c, v in opening if c == cur]
        bank._book("opening_balances", None, legs + [(OPENING, cur, -sum(v for _, _, v in legs))])
    bank.payees = {
        "univ_demo": Payee("univ_demo", "Demo University Finance Office", "Sandbox Bank of China", "****6021", "CNY",
                           True, "University official fee page (sandbox)", "university"),
        "student_own_cn": Payee("student_own_cn", "Student's own Chinese account", "Sandbox Bank of China", "****3317", "CNY",
                                True, "Opened by the student in person", "student_cn"),
        "agent_x": Payee("agent_x", "'Fast Tuition Agency' (unverified)", "Unknown", "****9999", "CNY",
                         False, "Sent by a stranger on WeChat", "university"),
    }
    bank.cards["4821"] = Card("4821", "student", "Student File debit card (Bangladesh) [sandbox]")
    bank.log("sandbox_seeded", "system", "SYSTEM", {
        "accounts": [a.to_dict() for a in bank.accounts.values()],
        "note": "Fictional demo persona; no real money or real bank.",
    })
    return bank
