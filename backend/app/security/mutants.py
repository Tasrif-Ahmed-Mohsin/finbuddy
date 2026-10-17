"""Deliberate bugs ("mutants") for checking that the safety fuzzer has teeth.

A fuzzer that reports "0 violations" proves little unless it would have reported the bug. Each mutant below breaks
one safety rule on purpose, only inside a `with` block; the fuzzer must catch every one (tests/test_fuzzer.py and
the evidence report run them).
"""
from __future__ import annotations

from contextlib import contextmanager
from unittest import mock


@contextmanager
def plain_approvals_allowed():
    """Bug: people can approve without a passkey signature (the server stops checking)."""
    from app.service import AppState

    real = AppState.approve

    def approve(self, actor, draft_id):
        saved = self.settings
        self.settings = type(saved)(**{**saved.__dict__, "passkey_required": False})
        try:
            return real(self, actor, draft_id)
        finally:
            self.settings = saved
    with mock.patch.object(AppState, "approve", approve):
        yield


@contextmanager
def taint_check_off():
    """Bug: the payment sink stops looking at where the amount came from."""
    from app.security.taint import TaintLedger, TaintVerdict

    with mock.patch.object(TaintLedger, "check_sink", lambda self, sink_name, **kw: TaintVerdict(True, sink_name)):
        yield


@contextmanager
def double_booking():
    """Bug: the bank forgets which drafts it already booked, and a retried send of a paid draft books it again."""
    from app.sandbox.bank import SandboxBank
    from app.service import AppState

    real = AppState.execute

    def execute(self, actor, draft_id):
        d = self.drafts[draft_id]
        if d.status == "executed" and actor != actor.AGENT:  # the retry goes straight to the bank again
            return {"draft": self.draft_view(draft_id), "bank_event": self._run(d, self.specs[draft_id], actor.value, "EXECUTE")}
        return real(self, actor, draft_id)
    with mock.patch.object(SandboxBank, "booked", lambda self, draft_id: False), mock.patch.object(AppState, "execute", execute):
        yield


MUTANTS = {
    "plain_approvals_allowed": (plain_approvals_allowed, "INV_NO_UNAUTHORIZED_TRANSFER"),
    "taint_check_off": (taint_check_off, "INV_TAINTED_AMOUNT_BLOCKED"),
    "double_booking": (double_booking, "INV_EXACTLY_ONCE"),
}
