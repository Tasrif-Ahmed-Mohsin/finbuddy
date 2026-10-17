"""The safety fuzzer: zero violations on the real code, and it catches each deliberate bug (mutant)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.security.fuzzer import INVARIANTS, SafetyInvariantFuzzer, run_invariant_fuzzer
from app.security.mutants import MUTANTS


def test_fuzzing_the_real_code_finds_no_violation_and_money_still_moves():
    m = run_invariant_fuzzer(iterations=2500, seed=1337)
    assert m.total_attacks == 2500 and m.hostile_steps > 1000
    assert m.violations_detected == 0, m.first_violations
    assert set(m.invariant_status) == set(INVARIANTS)
    assert m.payments_completed > 5  # liveness: honest payments go through, it is not just refusing everything
    assert m.payments_completed > m.payments_under_mandate  # some by passkey approvals, some by the autopilot


@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_the_fuzzer_catches_a_deliberate_bug(name: str):
    mutant, expected = MUTANTS[name]
    with mutant():
        m = run_invariant_fuzzer(iterations=2500, seed=1337)
    caught = {v["invariant"] for v in m.first_violations} | {k for k, v in m.invariant_status.items() if v["violations"]}
    assert expected in caught, (name, m.first_violations)


def test_a_balance_changed_behind_the_books_is_a_violation():
    f = SafetyInvariantFuzzer(seed=99)
    f.svc.bank.accounts["parent_bd"].balance -= Decimal("100")
    f.check(1)
    assert any(v["invariant"] == "INV_BOOKS_BALANCED" for v in f.violations)
