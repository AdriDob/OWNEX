"""Autopilot kill/scale — OWNEX decide sola dónde poner la próxima hora.

Reglas (codificadas de PERSONAL_CONTEXT §7 foco + kill 40h/$0 día 60):
- PAUSE canal: 40h+ O 8 intentos sin PAID.
- SCALE canal: verdict SCALE con net/h real.
- MATAR producto: 0 ventas ≥60d.
- Protect: trading (CAPITAL_ONLY) + backup (LAST_RESORT) jamás se auto-pausan.
- Toda decisión es reversible.
"""

from __future__ import annotations

from cores.automation.kill_scale import (
    KILL_MIN_ATTEMPTS,
    KILL_MIN_ATTEMPTS_NOHOURS,
    KILL_MIN_HUMAN_HOURS,
    MATAR_MIN_DAYS_LIVE,
    _protected_workspaces,
    _workspace_for_channel,
    decide_channel_actions,
)
from cores.economic_feedback.engine import ChannelEconomics


def _ch(**kw) -> ChannelEconomics:
    base = dict(
        channel="algora",
        attempted=0,
        accepted=0,
        paid=0,
        earned_gross=0.0,
        net_cash=0.0,
        human_hours=None,
        verdict="UNKNOWN",
        note="",
    )
    base.update(kw)
    return ChannelEconomics(**base)


def test_kill_rule_40h_pause():
    c = _ch(channel="algora", attempted=KILL_MIN_ATTEMPTS, human_hours=KILL_MIN_HUMAN_HOURS + 1)
    decs = decide_channel_actions([c])
    assert len(decs) == 1
    assert decs[0].action == "PAUSE"
    assert decs[0].workspace == "dev_bounty"
    assert decs[0].reversible is True


def test_kill_rule_8_intentos_sin_horas_pause():
    c = _ch(channel="outlier", attempted=KILL_MIN_ATTEMPTS_NOHOURS)
    decs = decide_channel_actions([c])
    assert decs and decs[0].action == "PAUSE"
    assert decs[0].workspace == "ai_training"


def test_no_pause_sin_evidencia():
    c = _ch(channel="mercor", attempted=3, human_hours=2.0)
    assert decide_channel_actions([c]) == []


def test_scale_con_net_h():
    c = _ch(
        channel="algora",
        attempted=5,
        paid=5,
        net_cash=500,
        human_hours=10,
        net_per_hour=50.0,
        verdict="SCALE",
        note="500 neto, 10h",
    )
    decs = decide_channel_actions([c])
    assert decs and decs[0].action == "SCALE"


def test_workspace_for_channel_mapping():
    assert _workspace_for_channel("algora") == "dev_bounty"
    assert _workspace_for_channel("hackerone") == "bug_bounty"
    assert _workspace_for_channel("mercor") == "ai_training"
    assert _workspace_for_channel("mercado_libre") == "mercado_libre"
    assert _workspace_for_channel("nope") is None


def test_protected_workspaces_incluyen_trading_y_backup():
    protected = _protected_workspaces(None)
    assert "trading" in protected
    assert "backup_income" in protected


def test_constants_alineadas():
    assert MATAR_MIN_DAYS_LIVE == 60
    assert KILL_MIN_HUMAN_HOURS == 40.0
