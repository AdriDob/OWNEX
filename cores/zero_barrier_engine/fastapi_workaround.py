"""Workaround for FastAPI 0.141.1 include_router bug.

FastAPI 0.141.1 has a bug where include_router doesn't properly
register routes. This module provides a workaround.
"""

from fastapi import FastAPI
from fastapi.routing import APIRouter


def include_router_workaround(app: "FastAPI", router: "APIRouter") -> None:
    """
    Workaround for FastAPI 0.141.1 include_router bug.

    FastAPI 0.141.1 has a bug where include_router doesn't properly
    register routes. This function manually adds routes to
    app.router.routes (which is the source of truth for routing).
    """
    for route in router.routes:
        app.router.routes.append(route)


def include_routers_workaround(app: "FastAPI", routers: list) -> None:
    """Include multiple routers with the workaround."""
    for router in routers:
        for route in router.routes:
            app.router.routes.append(route)
