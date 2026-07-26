from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from core.recon.fingerprint import FingerprintResult

logger = logging.getLogger("cateye.recon.strategies")


@dataclass
class ReconStrategy:
    name: str
    description: str
    tech_targets: list[str]
    probes: list[dict[str, Any]] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    priority: int = 5

    def matches(self, fingerprint: FingerprintResult, min_confidence: float = 0.3) -> bool:
        return any(fingerprint.get_confidence(tech) >= min_confidence for tech in self.tech_targets)


def react_strategy() -> ReconStrategy:
    return ReconStrategy(
        name="react_spa",
        description="React/Next.js SPA — JS route enumeration, GraphQL discovery, API endpoint patterns",
        tech_targets=["react"],
        priority=10,
        tools=["katana", "gau"],
        probes=[
            {"path": "/_next/data/", "reason": "Next.js static data routes"},
            {"path": "/api/", "reason": "Next.js API routes"},
            {"path": "/graphql", "reason": "GraphQL introspection"},
            {
                "method": "POST",
                "path": "/api/graphql",
                "body": '{"query":"{__schema{types{name}}}"}',
                "reason": "GraphQL schema probe",
            },
        ],
    )


def vue_strategy() -> ReconStrategy:
    return ReconStrategy(
        name="vue_spa",
        description="Vue/Nuxt SPA — SSR routes, API endpoints, component discovery",
        tech_targets=["vue"],
        priority=9,
        tools=["katana", "gau"],
        probes=[
            {"path": "/_nuxt/", "reason": "Nuxt static assets"},
            {"path": "/api/", "reason": "Nuxt API routes"},
        ],
    )


def laravel_strategy() -> ReconStrategy:
    return ReconStrategy(
        name="laravel",
        description="Laravel — route listing, Sanctum auth, storage misconfigs, debug endpoints",
        tech_targets=["laravel"],
        priority=9,
        tools=["katana", "ffuf"],
        probes=[
            {"path": "/routes", "reason": "Laravel route list (debug)"},
            {"path": "/sanctum/csrf-cookie", "reason": "Sanctum CSRF token endpoint"},
            {"path": "/storage/logs/laravel.log", "reason": "Log exposure"},
            {"path": "/_debugbar/", "reason": "Laravel Debugbar"},
            {"path": "/telescope", "reason": "Laravel Telescope"},
            {"path": "/horizon", "reason": "Laravel Horizon"},
        ],
    )


def django_strategy() -> ReconStrategy:
    return ReconStrategy(
        name="django",
        description="Django — admin panel, REST framework, debug endpoints",
        tech_targets=["django"],
        priority=8,
        tools=["katana", "ffuf"],
        probes=[
            {"path": "/admin/", "reason": "Django admin panel"},
            {"path": "/api/", "reason": "Django REST API"},
            {"path": "/api-auth/", "reason": "DRF authentication"},
            {"path": "/__debug__/", "reason": "Django Debug Toolbar"},
        ],
    )


def graphql_strategy() -> ReconStrategy:
    return ReconStrategy(
        name="graphql",
        description="GraphQL — introspection, schema extraction, mutation discovery",
        tech_targets=["graphql"],
        priority=10,
        tools=[],
        probes=[
            {
                "method": "POST",
                "path": "/graphql",
                "body": '{"query":"query{__schema{types{name fields{name}}}}"}',
                "reason": "Full schema introspection",
            },
            {
                "method": "POST",
                "path": "/graphql",
                "body": '{"query":"{__schema{queryType{name}}}"}',
                "reason": "Schema query type",
            },
            {
                "method": "POST",
                "path": "/api/graphql",
                "body": '{"query":"{__schema{types{name}}}"}',
                "reason": "API GraphQL introspection",
            },
            {"path": "/graphql?query={__typename}", "reason": "GET-based GraphQL probe"},
            {"path": "/graphql/explorer", "reason": "GraphQL explorer UI"},
            {"path": "/graphiql", "reason": "GraphiQL IDE"},
            {"path": "/voyager", "reason": "GraphQL Voyager"},
        ],
    )


def wordpress_strategy() -> ReconStrategy:
    return ReconStrategy(
        name="wordpress",
        description="WordPress — REST API, plugin detection, auth endpoints, user enumeration",
        tech_targets=["wordpress"],
        priority=8,
        tools=["katana"],
        probes=[
            {"path": "/wp-json/wp/v2/", "reason": "WP REST API root"},
            {"path": "/wp-json/wp/v2/users", "reason": "User enumeration"},
            {"path": "/wp-json/wp/v2/posts", "reason": "Post listing"},
            {"path": "/wp-content/plugins/", "reason": "Plugin listing"},
            {"path": "/xmlrpc.php", "reason": "XML-RPC (SSRF, auth bypass)"},
            {"path": "/wp-login.php", "reason": "Login page"},
        ],
    )


def spring_strategy() -> ReconStrategy:
    return ReconStrategy(
        name="spring",
        description="Spring Boot — actuator endpoints, env leak, heap dump, route mappings",
        tech_targets=["spring"],
        priority=9,
        tools=[],
        probes=[
            {"path": "/actuator", "reason": "Spring Actuator root"},
            {"path": "/actuator/env", "reason": "Environment variables leak"},
            {"path": "/actuator/health", "reason": "Health info"},
            {"path": "/actuator/beans", "reason": "Bean definitions"},
            {"path": "/actuator/mappings", "reason": "Route mappings"},
            {"path": "/actuator/heapdump", "reason": "Heap dump (memory leak)"},
            {"path": "/actuator/threaddump", "reason": "Thread dump"},
            {"path": "/actuator/loggers", "reason": "Log level config"},
        ],
    )


def fastapi_strategy() -> ReconStrategy:
    return ReconStrategy(
        name="fastapi",
        description="FastAPI — OpenAPI schema, docs, route discovery",
        tech_targets=["fastapi"],
        priority=9,
        tools=[],
        probes=[
            {"path": "/openapi.json", "reason": "OpenAPI schema"},
            {"path": "/docs", "reason": "Swagger UI"},
            {"path": "/redoc", "reason": "ReDoc"},
        ],
    )


def express_strategy() -> ReconStrategy:
    return ReconStrategy(
        name="express",
        description="Express/Node.js — route patterns, static files, debug endpoints",
        tech_targets=["express"],
        priority=7,
        tools=["katana", "ffuf"],
        probes=[
            {"path": "/.env", "reason": "Environment leak"},
            {"path": "/package.json", "reason": "Dependency info"},
            {"path": "/debug", "reason": "Debug endpoint"},
            {"path": "/api/", "reason": "API routes"},
        ],
    )


def api_generic_strategy() -> ReconStrategy:
    return ReconStrategy(
        name="api_generic",
        description="Generic API — versioned routes, REST patterns, auth endpoints, parameter fuzzing",
        tech_targets=["api"],
        priority=6,
        tools=["gau", "waybackurls"],
        probes=[
            {"path": "/api/", "reason": "API root"},
            {"path": "/api/v1/", "reason": "API v1"},
            {"path": "/api/v2/", "reason": "API v2"},
            {"path": "/api/v3/", "reason": "API v3"},
            {"path": "/swagger.json", "reason": "Swagger spec"},
            {"path": "/swagger/v1/swagger.json", "reason": "Swagger v1"},
            {"path": "/health", "reason": "Health check"},
            {"path": "/status", "reason": "Status page"},
            {"path": "/version", "reason": "Version info"},
        ],
    )


_STRATEGY_REGISTRY: list[ReconStrategy] = [
    react_strategy(),
    vue_strategy(),
    laravel_strategy(),
    django_strategy(),
    graphql_strategy(),
    wordpress_strategy(),
    spring_strategy(),
    fastapi_strategy(),
    express_strategy(),
    api_generic_strategy(),
]


def get_strategy(name: str) -> ReconStrategy | None:
    for s in _STRATEGY_REGISTRY:
        if s.name == name:
            return s
    return None


def list_strategies() -> list[ReconStrategy]:
    return list(_STRATEGY_REGISTRY)


def select_strategies(fingerprint: FingerprintResult) -> list[ReconStrategy]:
    matched: list[ReconStrategy] = []
    for strategy in _STRATEGY_REGISTRY:
        if strategy.matches(fingerprint):
            matched.append(strategy)
    matched.sort(key=lambda s: (-s.priority, s.name))
    return matched
