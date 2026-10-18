"""WhatsApp alerts for the family (Meta WhatsApp Cloud API).

Parents in Bangladesh live on WhatsApp, not in a new app. Bluefin sends them the same family-feed notes they
would see on the Today screen, in Bengali: what Bluefin did, what needs them, what is coming.

Safety design (also in the security self-assessment):
  * Notifications only. Nothing can be approved, signed or changed by replying on WhatsApp: approvals stay in
    the app behind fingerprint/PIN, so a stolen WhatsApp account cannot move money.
  * Only to the family's own registered number, set by a user (never by the agent). The agent has no
    WhatsApp tool.
  * Modes: `off` · `dry_run` (log only, the default once configured) · `live`. Only the server environment can
    switch to live: neither the app nor the agent can.
  * The text is Bluefin's templated note (amounts, dates), never message contents, OTPs or account numbers.
    The audit log records that a message was sent (note key, status, last 4 digits of the number), not the text.
  * Rate-limited, and simulated-time fast-forwards send one summary instead of one message per note.
  * Business-initiated messages outside WhatsApp's 24-hour window need an approved template: if Meta refuses
    the text for that reason, Bluefin sends the approved template instead and says so.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime

import httpx

E164 = re.compile(r"^\+[1-9][0-9]{7,14}$")
REENGAGEMENT_CODES = {131047}  # more than 24 hours since the recipient last wrote: only templates are delivered
NOT_ALLOWED_RECIPIENT = 131030  # a test number may only message the recipients added in Meta's dashboard
MAX_PER_HOUR = 20


def normalise_number(raw: str) -> str:
    """'+880 1712-345678' → '+8801712345678'. Raises ValueError if it is not an international number."""
    s = re.sub(r"[\s()-]", "", (raw or "").strip())
    if s.startswith("00"):
        s = "+" + s[2:]
    if not E164.match(s):
        raise ValueError("enter the WhatsApp number in international format, e.g. +8801712345678")
    return s


def mask(number: str | None) -> str | None:
    return f"••••{number[-4:]}" if number else None


@dataclass
class OutboxEntry:
    at: str
    to: str  # masked
    kind: str  # note | digest | test
    key: str
    mode: str
    status: str  # logged | sent | sent_template | failed | rate_limited
    detail: str = ""
    message_id: str | None = None

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class WhatsAppNotifier:
    mode: str = "off"
    token: str | None = None
    phone_number_id: str | None = None
    graph_version: str = "v21.0"
    transport: httpx.BaseTransport | None = None
    outbox: list[OutboxEntry] = field(default_factory=list)
    _sent_times: list[float] = field(default_factory=list)

    @classmethod
    def from_settings(cls, s, transport: httpx.BaseTransport | None = None) -> "WhatsAppNotifier":
        mode = s.whatsapp_mode if s.whatsapp_mode in ("off", "dry_run", "live") else "off"
        if mode != "off" and not s.whatsapp_configured:
            mode = "off"
        return cls(mode, s.whatsapp_token, s.whatsapp_phone_number_id, s.whatsapp_graph_version, transport)

    @property
    def enabled(self) -> bool:
        return self.mode in ("dry_run", "live")

    def status(self) -> dict:
        return {"mode": self.mode, "provider": "meta", "configured": bool(self.token and self.phone_number_id),
                "outbox": [e.to_dict() for e in reversed(self.outbox[-15:])]}

    # ---- sending ------------------------------------------------------------------------------
    def _post(self, payload: dict) -> httpx.Response:
        url = f"https://graph.facebook.com/{self.graph_version}/{self.phone_number_id}/messages"
        with httpx.Client(timeout=15, transport=self.transport) as c:
            return c.post(url, json=payload, headers={"Authorization": f"Bearer {self.token}"})

    def _rate_ok(self) -> bool:
        now = time.time()
        self._sent_times = [t for t in self._sent_times if now - t < 3600]
        return len(self._sent_times) < MAX_PER_HOUR

    def send(self, to: str, text: str, kind: str, key: str, at: datetime) -> OutboxEntry:
        entry = OutboxEntry(at.isoformat(), mask(to), kind, key, self.mode, "logged")
        if self.mode == "dry_run":
            entry.detail = text[:1500]  # dry run: shown in the app so the family can see exactly what WOULD be sent
        elif self.mode == "live":
            if not self._rate_ok():
                entry.status = "rate_limited"
            else:
                self._sent_times.append(time.time())
                entry.status, entry.detail, entry.message_id = self._send_live(to, text)
        self.outbox.append(entry)
        return entry

    def _send_live(self, to: str, text: str) -> tuple[str, str, str | None]:
        digits = to.lstrip("+")
        try:
            r = self._post({"messaging_product": "whatsapp", "to": digits, "type": "text",
                            "text": {"body": text[:4000], "preview_url": False}})
            body = r.json() if r.content else {}
            if r.status_code == 200:
                return "sent", "", (body.get("messages") or [{}])[0].get("id")
            code = (body.get("error") or {}).get("code")
            if code == NOT_ALLOWED_RECIPIENT:
                return "failed", "this number is not on the test number's allowed list: add it in Meta's WhatsApp dashboard (API Setup → To)", None
            if code in REENGAGEMENT_CODES:
                # Outside the 24-hour window, Meta only delivers approved templates.
                t = self._post({"messaging_product": "whatsapp", "to": digits, "type": "template",
                                "template": {"name": "hello_world", "language": {"code": "en_US"}}})
                tb = t.json() if t.content else {}
                if t.status_code == 200:
                    return "sent_template", "text needs an open 24-hour window; sent the approved template instead", \
                        (tb.get("messages") or [{}])[0].get("id")
                return "failed", _error(tb, t.status_code), None
            return "failed", _error(body, r.status_code), None
        except httpx.HTTPError as e:
            return "failed", f"network: {type(e).__name__}", None


def _error(body: dict, status: int) -> str:
    e = body.get("error") or {}
    return f"HTTP {status} {e.get('code', '')}: {str(e.get('message', ''))[:140]}"
