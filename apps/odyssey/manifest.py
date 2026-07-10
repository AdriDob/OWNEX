"""ODYSSEY — Gambling Analytics (ORION Platform app).

Analytical only — no automated betting.
Provides bankroll tracking, ROI analysis, EV calculation, and market data.
"""

from __future__ import annotations

from apps.odyssey.api.routers import router as odyssey_router
from apps.odyssey.models import Bankroll, Bet, Strategy
from core.interfaces.app import IAppPlugin

from .providers import PROVIDERS

manifest = IAppPlugin(
    id="odyssey",
    name="ODYSSEY",
    version="0.1.0",
    description="Gambling Analytics — bankroll, ROI, EV, prediction markets, and sports betting intelligence",
    icon="Dices",
    order=3,
    db_path="odyssey.db",
    models=[Bankroll, Bet, Strategy],
    routers=[odyssey_router],
    router_prefix="odyssey",
    scheduler_jobs=[
        {
            "job_id": "odyssey_sync_bets",
            "app_id": "odyssey",
            "handler": "apps.odyssey.scheduler.sync_bets",
            "trigger": "interval",
            "seconds": 3600,
        },
        {
            "job_id": "odyssey_calc_analytics",
            "app_id": "odyssey",
            "handler": "apps.odyssey.scheduler.calculate_analytics",
            "trigger": "interval",
            "seconds": 21600,
        },
    ],
    agent_class=None,
    frontend_routes=[
        {"path": "/odyssey/", "name": "odyssey-dashboard", "component": "DashboardOdyssey"},
        {"path": "/odyssey/settings", "name": "odyssey-settings", "component": "SettingsOdyssey"},
    ],
    widgets=[
        {"id": "odyssey-bankroll-total", "label": "Bankroll", "icon": "Wallet", "query": "odyssey/bankroll/total"},
        {"id": "odyssey-roi", "label": "ROI", "icon": "TrendingUp", "query": "odyssey/analytics/roi"},
        {"id": "odyssey-active-bets", "label": "Active Bets", "icon": "ListChecks", "query": "odyssey/bets/active"},
    ],
    providers=PROVIDERS,
)
