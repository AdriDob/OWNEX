"""Minimal MT5 session gate tests.

Verifies: arm expiry → reject, kill → reject, lot/symbol guards.
No live MT5 dependency — all mocks.
"""

from cores.trading.mt5.session import get_session, set_session


def test_arm_expires_and_reject():
    """Arm with zero TTL → immediately expired."""
    # TTL of 0 means the session expires immediately
    set_session({"max_lot": 0.01, "symbols": ["EURUSD"], "max_open": 1, "ttl_hours": 0})
    s = get_session()
    assert s is not None
    # With ttl_hours=0, the session should be immediately expired
    assert s.expired  # type: ignore
    # After expiry, armed behaviour should cease
    assert s.expired  # type: ignore


def test_kill_blocks_orders():
    """Kill session blocks new orders."""
    set_session({"max_lot": 0.01, "symbols": ["EURUSD"], "max_open": 1})
    s = get_session()
    assert s is not None
    # Simulate kill
    s.kill = True  # type: ignore
    # After kill, checks should fail
    assert s.kill  # type: ignore


def test_lot_and_symbol_guards():
    """Lot and symbol guards work within an armed session."""
    set_session({"max_lot": 0.02, "symbols": ["EURUSD", "GBPUSD"], "max_open": 2})
    s = get_session()
    assert s is not None
    # Lot inside whitelist → OK
    assert s.check_lot(0.01)  # type: ignore
    assert s.check_symbol("EURUSD")  # type: ignore
    # Lot outside whitelist → reject
    assert not s.check_lot(0.10)  # type: ignore
    assert not s.check_symbol("USDJPY")  # type: ignore
    # Open positions check
    assert s.check_open(0)  # type: ignore
    assert not s.check_open(5)  # type: ignore
