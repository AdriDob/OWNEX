"""ATLAS — Investment Management (ORION Platform app)."""

from __future__ import annotations

from apps.atlas.api.routers import router as atlas_router
from apps.atlas.models import Asset, Portfolio, Transaction, Wallet
from core.interfaces.app import IAppPlugin

from .providers import PROVIDERS

manifest = IAppPlugin(
    id="atlas",
    name="ATLAS",
    version="0.1.0",
    description="Personal Investment Dashboard — stocks, crypto, ETFs, bonds, and DeFi",
    icon="TrendingUp",
    order=2,
    db_path="atlas.db",
    models=[Asset, Portfolio, Transaction, Wallet],
    routers=[atlas_router],
    router_prefix="atlas",
    scheduler_jobs=[
        {
            "job_id": "atlas_sync_prices",
            "app_id": "atlas",
            "handler": "apps.atlas.scheduler.sync_prices",
            "trigger": "interval",
            "seconds": 3600,
        },
        {
            "job_id": "atlas_rebalance_check",
            "app_id": "atlas",
            "handler": "apps.atlas.scheduler.check_rebalance",
            "trigger": "cron",
            "hour": 9,
        },
    ],
    agent_class=None,
    frontend_routes=[
        {"path": "/atlas/", "name": "atlas-dashboard", "component": "DashboardAtlas"},
        {"path": "/atlas/portfolio", "name": "atlas-portfolio", "component": "PortfolioView"},
        {"path": "/atlas/assets", "name": "atlas-assets", "component": "AssetsView"},
        {"path": "/atlas/transactions", "name": "atlas-transactions", "component": "TransactionsView"},
        {"path": "/atlas/providers", "name": "atlas-providers", "component": "ProviderSettings"},
        {"path": "/atlas/alerts", "name": "atlas-alerts", "component": "AlertSettings"},
    ],
    widgets=[
        {"id": "atlas-portfolio-value", "label": "Portfolio Value", "icon": "DollarSign", "query": "atlas/portfolio/value"},
        {"id": "atlas-daily-pnl", "label": "Daily P&L", "icon": "TrendingUp", "query": "atlas/performance/daily"},
        {"id": "atlas-asset-count", "label": "Assets Tracked", "icon": "PieChart", "query": "atlas/assets/count"},
    ],
    providers=PROVIDERS,
)
