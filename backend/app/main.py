"""Sathi API (FastAPI). Run:  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Demo authentication: `Authorization: Bearer <token>` where the token maps to a role. This is a
sandbox simplification (listed in the known-risk list); production would use real accounts plus
device-bound keys.
"""
from __future__ import annotations

import hmac
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.agent.llm import make_llm
from app.config import load_settings
from app.inbox.email_imap import fetch_recent
from app.security.permissions import Actor
from app.service import AppState

DEMO_TOKENS = {
    os.environ.get("SATHI_STUDENT_TOKEN", "demo-student"): Actor.STUDENT,
    os.environ.get("SATHI_PARENT_TOKEN", "demo-parent"): Actor.PARENT,
    os.environ.get("SATHI_AGENT_TOKEN", "demo-agent"): Actor.AGENT,
}

AUDIT_PATH = Path(os.environ.get("SATHI_AUDIT_PATH", Path(__file__).resolve().parent.parent / "var" / "audit.jsonl"))


# ---- request models ---------------------------------------------------
class TuitionIn(BaseModel):
    amount_cny: Decimal = Field(gt=0)
    deadline: date
    current_quote_id: str | None = None


class LivingIn(BaseModel):
    need_cny: Decimal = Field(gt=0)
    bridge_cny: Decimal = Field(default=Decimal(0), ge=0)
    reserved_card_tx: int = Field(default=0, ge=0, le=30)
    days_available: int = Field(default=30, ge=1, le=31)


class MessageIn(BaseModel):
    text: str = Field(max_length=10000)


class DraftIn(BaseModel):
    kind: str
    amount_cny: Decimal = Field(gt=0)
    payee_id: str = "univ_demo"
    quote_id: str | None = None
    memo: str = Field(default="", max_length=140)
    origin_message: str | None = Field(default=None, max_length=10000)
    withdrawals: list[Decimal] | None = None


class MandateIn(BaseModel):
    payee_id: str
    max_bdt_per_payment: Decimal = Field(gt=0)
    max_bdt_per_period: Decimal = Field(gt=0)
    period_days: int = Field(default=30, ge=1, le=366)
    valid_days: int = Field(default=90, ge=1, le=366)


class AdvanceIn(BaseModel):
    days: int = Field(ge=0, le=365)


class InboxIn(BaseModel):
    source: str = "sms"
    sender: str = Field(default="unknown", max_length=60)
    text: str = Field(min_length=1, max_length=5000)


class WebhookIn(BaseModel):
    sender: str = Field(default="unknown", max_length=60)
    text: str = Field(min_length=1, max_length=5000)


class QuoteIn(BaseModel):
    bank: str = Field(min_length=2, max_length=40)
    bdt_per_cny: Decimal = Field(gt=0)
    fixed_fee_bdt: Decimal = Field(ge=0)


class RenewalStepIn(BaseModel):
    status: str


class RenewalDoneIn(BaseModel):
    new_expiry: date


class FreezeIn(BaseModel):
    reason: str = Field(default="", max_length=120)


class ChatTurn(BaseModel):
    role: str
    content: str = Field(max_length=4000)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    lang: str = "en"


_AUTO = object()


def create_app(audit_path: Path | None = AUDIT_PATH, llm=_AUTO) -> FastAPI:
    app = FastAPI(title="Sathi API", version="0.2.0",
                  description="Cross-border student finance agent (sandbox). No real money moves.")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    settings = load_settings()
    app.state.svc = AppState(audit_path=audit_path, llm=make_llm(settings) if llm is _AUTO else llm, settings=settings)

    def svc() -> AppState:
        return app.state.svc

    def actor(authorization: str = Header(default="")) -> Actor:
        token = authorization.removeprefix("Bearer ").strip()
        if token not in DEMO_TOKENS:
            raise HTTPException(status_code=401, detail="unknown or missing token")
        return DEMO_TOKENS[token]

    def guard(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except KeyError as e:
            raise HTTPException(status_code=404, detail=f"not found: {e}")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # ---- routes -----------------------------------------------------------
    @app.get("/health")
    def health():
        return {"ok": True, "sandbox": True}

    @app.get("/corridor")
    def corridor(s: AppState = Depends(svc)):
        c = s.corridor
        return {"id": c.id, "name": c.name, "reviewed": c.reviewed, "params": {k: c.meta(k) for k in c.params}}

    @app.get("/market")
    def market(s: AppState = Depends(svc)):
        m = s.market
        return {"mid": {"bdt_per_usd": str(m.mid.bdt_per_usd), "cny_per_usd": str(m.mid.cny_per_usd),
                        "bdt_per_cny": str(round(m.mid.bdt_per_cny, 4)), "as_of": m.mid.as_of, "source": m.mid.source,
                        "sample": m.mid.sample},
                "quotes": [{"quote_id": q.quote_id, "bank": q.bank, "bdt_per_cny": str(q.bdt_per_cny),
                            "fixed_fee_bdt": str(q.fixed_fee_bdt), "markup_pct": str(q.markup_pct),
                            "as_of": q.as_of, "estimate": q.sample, "source": q.source} for q in m.quotes],
                "data_quality": s.data_quality}

    @app.post("/market/quotes")
    def add_quote(body: QuoteIn, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.add_real_quote, who, body.bank, body.bdt_per_cny, body.fixed_fee_bdt)

    @app.get("/fx")
    def fx(s: AppState = Depends(svc)):
        return s.fx_overview()

    @app.get("/fx/history")
    def fx_history(days: int = 180, s: AppState = Depends(svc)):
        return s.fx_history(days)

    # ---- renewals (T3) ----------------------------------------------------------
    @app.post("/renewals/{item}")
    def renewal_start(item: str, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.start_renewal, who, item)

    @app.get("/renewals/{item}")
    def renewal_get(item: str, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        case = s.renewal_for(item)
        if case is None:
            raise HTTPException(status_code=404, detail="no renewal plan yet")
        return case

    @app.post("/renewals/case/{case_id}/steps/{step_id}")
    def renewal_step(case_id: str, step_id: str, body: RenewalStepIn, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.update_renewal_step, who, case_id, step_id, body.status)

    @app.post("/renewals/case/{case_id}/complete")
    def renewal_done(case_id: str, body: RenewalDoneIn, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.complete_renewal, who, case_id, body.new_expiry)

    # ---- card controls --------------------------------------------------------
    @app.get("/cards")
    def cards(s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return [c.to_dict() for c in s.bank.cards.values()]

    @app.post("/cards/{last4}/freeze")
    def freeze(last4: str, body: FreezeIn | None = None, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.freeze_card, who, last4, body.reason if body else "")

    @app.post("/cards/{last4}/unfreeze")
    def unfreeze(last4: str, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.unfreeze_card, who, last4)

    @app.post("/cards/{last4}/report-lost")
    def report_lost(last4: str, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.report_card_lost, who, last4)

    @app.get("/profile")
    def profile(s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return {k: (v.isoformat() if isinstance(v, date) else str(v)) for k, v in s.profile.items()}

    @app.get("/timeline")
    def timeline(s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return s.timeline()

    @app.get("/accounts")
    def accounts(s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return {"now": s.now.isoformat(), "accounts": [a.to_dict() for a in s.bank.accounts.values()],
                "pending": [{"id": t.id, "draft_id": t.draft_id, "to": t.to_account_id, "amount_cny": str(t.amount),
                             "arrives_at": t.arrives_at.isoformat()} for t in s.bank.pending]}

    @app.post("/plan/tuition")
    def plan_tuition(body: TuitionIn, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.plan_tuition, who, body.amount_cny, body.deadline, body.current_quote_id)

    @app.post("/plan/living")
    def plan_living(body: LivingIn, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.plan_living, who, body.need_cny, body.bridge_cny, body.reserved_card_tx, body.days_available)

    @app.post("/check/message")
    def check_message(body: MessageIn, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.check_message, who, body.text)

    @app.post("/drafts")
    def create_draft(body: DraftIn, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.create_draft, who, body.kind, body.amount_cny, body.payee_id, body.quote_id, body.memo,
                     body.origin_message, body.withdrawals)

    @app.get("/drafts")
    def list_drafts(s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return [s.draft_view(i) for i in reversed(list(s.drafts))]

    @app.get("/drafts/{draft_id}")
    def get_draft(draft_id: str, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.draft_view, draft_id)

    @app.post("/drafts/{draft_id}/approve")
    def approve(draft_id: str, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.approve, who, draft_id)

    @app.post("/drafts/{draft_id}/execute")
    def execute(draft_id: str, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.execute, who, draft_id)

    @app.post("/drafts/{draft_id}/execute-under-mandate/{mandate_id}")
    def execute_mandate(draft_id: str, mandate_id: str, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.execute_under_mandate, who, draft_id, mandate_id)

    @app.post("/mandates")
    def create_mandate(body: MandateIn, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.create_mandate, who, body.payee_id, body.max_bdt_per_payment, body.max_bdt_per_period,
                     body.period_days, body.valid_days)

    @app.delete("/mandates/{mandate_id}")
    def revoke_mandate(mandate_id: str, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.revoke_mandate, who, mandate_id)

    @app.post("/sandbox/advance")
    def advance(body: AdvanceIn, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        events = guard(s.bank.advance, body.days, who.value)
        return {"now": s.now.isoformat(), "events": events}

    @app.get("/audit")
    def audit(limit: int = 100, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return {"verify": s.audit.verify(), "entries": s.audit.entries[-limit:][::-1]}

    # ---- inbox: shared / forwarded SMS and emails ----------------------------
    def user_only(who: Actor) -> Actor:
        if who == Actor.AGENT:
            raise HTTPException(status_code=403, detail="only the student or parent can add or sync messages")
        return who

    @app.post("/inbox/messages")
    def inbox_add(body: InboxIn, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.inbox.ingest, user_only(who).value, body.source, body.sender, body.text)

    @app.post("/inbox/webhook")
    def inbox_webhook(body: WebhookIn, s: AppState = Depends(svc), x_ingest_token: str = Header(default="")):
        # For SMS-forwarding apps / iOS Shortcuts. A shared secret, compared in constant time.
        if not hmac.compare_digest(x_ingest_token, s.settings.ingest_token):
            raise HTTPException(status_code=401, detail="bad ingest token")
        return guard(s.inbox.ingest, "forwarder", "webhook", body.sender, body.text)

    @app.post("/inbox/demo/seed")
    def inbox_seed(s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return guard(s.inbox.seed_demo, user_only(who).value)

    @app.post("/inbox/email/sync")
    def inbox_email_sync(s: AppState = Depends(svc), who: Actor = Depends(actor)):
        user_only(who)
        st = s.settings
        if not st.imap_configured:
            raise HTTPException(status_code=400, detail="email is not connected: set SATHI_IMAP_HOST, SATHI_IMAP_USER and SATHI_IMAP_PASSWORD (an app password)")
        try:
            emails = fetch_recent(st.imap_host, st.imap_user, st.imap_password)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"could not read the mailbox ({type(e).__name__})")
        results = [s.inbox.ingest(who.value, "email", e.sender, e.text) for e in emails]
        return {"fetched": len(emails), "kept": sum(1 for r in results if r["kept"])}

    @app.get("/inbox/messages")
    def inbox_messages(limit: int = 50, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return [m.to_dict() for m in s.inbox.messages[-limit:][::-1]]

    @app.get("/inbox/transactions")
    def inbox_transactions(limit: int = 50, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return [t.to_dict() for t in s.inbox.txns[-limit:][::-1]]

    @app.get("/inbox/summary")
    def inbox_summary(s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return s.inbox.summary()

    @app.get("/inbox/sources")
    def inbox_sources(s: AppState = Depends(svc), who: Actor = Depends(actor)):
        return {
            "share_paste": {"available": True, "note": "Share or paste any bank SMS or email into Sathi."},
            "webhook": {"available": True, "path": "/inbox/webhook", "header": "X-Ingest-Token",
                        "note": "For SMS-forwarding apps (Android) or iOS Shortcuts automations."},
            "email": {"available": s.settings.imap_configured, "note": "Read-only IMAP with an app password."},
            "sms_auto_read": {"available": False, "note": "Google Play allows automatic SMS reading only for default SMS apps; we use share/forward instead."},
            "privacy": ["Non-money messages are dropped and never stored.", "One-time codes are removed before storage.",
                        "Account, card and phone numbers are masked to the last 4 digits.",
                        "Only redacted text is ever sent to the AI model.", "Reading messages can never move money."],
        }

    @app.get("/insights")
    def insights(lang: str = "en", s: AppState = Depends(svc), who: Actor = Depends(actor)):
        items = s.inbox.insights()
        return {"insights": s.translator.translate(items, lang), "summary": s.inbox.summary()}

    # ---- agent chat -----------------------------------------------------------
    @app.get("/agent/status")
    def agent_status(s: AppState = Depends(svc)):
        return {"llm": s.llm is not None, "provider": "DeepSeek" if s.llm else None,
                "model": s.llm.model if s.llm else None, "fallback": "rule-based answers when the AI is unavailable"}

    @app.post("/agent/chat")
    def agent_chat(body: ChatIn, s: AppState = Depends(svc), who: Actor = Depends(actor)):
        history = [t.model_dump() for t in body.history]
        return guard(s.agent.chat, user_only(who), body.message, history, body.lang)

    @app.get("/audit/export", response_class=PlainTextResponse)
    def audit_export(s: AppState = Depends(svc), who: Actor = Depends(actor)):
        import json
        return "\n".join(json.dumps(e, ensure_ascii=False, sort_keys=True) for e in s.audit.entries)

    return app


app = create_app()
