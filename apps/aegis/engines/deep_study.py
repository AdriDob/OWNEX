"""Deep Study Engine — target intelligence analysis like a security researcher.

Combines tech fingerprinting, endpoint classification, hypothesis generation,
COPILOT planning, and technology-specific playbooks into a unified deep study.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from cores.engine.hypothesis.generators import generate_from_technology

logger = logging.getLogger("orion.aegis.engines.deep_study")

# ── Technology-specific playbooks ──────────────────────────────────

TECH_PLAYBOOKS: dict[str, list[dict[str, Any]]] = {
    "react": [
        {
            "action": "check_api_authorization",
            "description": "React SPA often trusts client-side routing — check API auth headers and CORS preflight",
            "tool": "http",
            "risk": 0.3,
            "params": {"method": "OPTIONS", "check": "cors"},
        },
        {
            "action": "check_env_exposure",
            "description": "Create React App exposes .env variables in JS bundles",
            "tool": "scan",
            "risk": 0.2,
            "params": {"method": "GET", "check": "source_map", "target": "/static/js/*.map"},
        },
    ],
    "vue.js": [
        {
            "action": "check_api_authorization",
            "description": "Vue.js apps rely on API gateways — verify auth enforcement server-side",
            "tool": "http",
            "risk": 0.3,
            "params": {"method": "GET", "check": "ownership"},
        },
    ],
    "laravel": [
        {
            "action": "check_debug_mode",
            "description": "Laravel debug mode leaks env vars and DB credentials via /debugbar",
            "tool": "scan",
            "risk": 0.4,
            "params": {"method": "GET", "target": "/_debugbar/open", "check": "response"},
        },
        {
            "action": "check_serialization",
            "description": "Laravel unserialize() on cookie values may allow RCE",
            "tool": "scan",
            "risk": 0.8,
            "params": {"method": "GET", "check": "deserialization", "target": "cookie"},
        },
    ],
    "django": [
        {
            "action": "check_admin_panel",
            "description": "Django admin panel at /admin/ — test for default creds and bruteforce",
            "tool": "scan",
            "risk": 0.5,
            "params": {"method": "GET", "target": "/admin/", "check": "auth_bypass"},
        },
        {
            "action": "check_session_handling",
            "description": "Django session handling — test CSRF token generation and reuse",
            "tool": "http",
            "risk": 0.3,
            "params": {"method": "POST", "check": "csrf"},
        },
    ],
    "spring boot": [
        {
            "action": "check_actuator",
            "description": "Spring Boot Actuator leaks /actuator/env, /actuator/health, /actuator/beans",
            "tool": "scan",
            "risk": 0.6,
            "params": {"method": "GET", "target": "/actuator/", "check": "info_leak"},
        },
        {
            "action": "check_spel_injection",
            "description": "Spring Boot SpEL injection via /actuator/env — test with malicious env vars",
            "tool": "scan",
            "risk": 0.9,
            "params": {"method": "POST", "check": "spel_injection", "target": "/actuator/env"},
        },
    ],
    "express": [
        {
            "action": "check_cors",
            "description": "Express.js CORS misconfiguration allows cross-origin requests",
            "tool": "http",
            "risk": 0.4,
            "params": {"method": "OPTIONS", "check": "cors"},
        },
        {
            "action": "check_error_handling",
            "description": "Express error handling may leak stack traces via default error handler",
            "tool": "scan",
            "risk": 0.3,
            "params": {"method": "GET", "target": "/error", "check": "response"},
        },
    ],
    "graphql": [
        {
            "action": "check_introspection",
            "description": "GraphQL introspection exposes full schema — query for __schema",
            "tool": "http",
            "risk": 0.5,
            "params": {"method": "POST", "check": "graphql_introspection"},
        },
        {
            "action": "check_batch_queries",
            "description": "GraphQL batch queries may enable bruteforce or DoS without proper rate limiting",
            "tool": "http",
            "risk": 0.6,
            "params": {"method": "POST", "check": "graphql_batch"},
        },
        {
            "action": "check_auth_bypass",
            "description": "GraphQL resolvers may not enforce auth for all queries",
            "tool": "http",
            "risk": 0.7,
            "params": {"method": "POST", "check": "ownership"},
        },
    ],
    "stripe": [
        {
            "action": "check_webhook_auth",
            "description": "Stripe webhooks without signature verification allow fake events",
            "tool": "scan",
            "risk": 0.8,
            "params": {"check": "webhook_signature"},
        },
    ],
    "firebase": [
        {
            "action": "check_firestore_rules",
            "description": "Firestore open read/write rules expose all data — test common collection names",
            "tool": "http",
            "risk": 0.9,
            "params": {"method": "GET", "check": "firebase_db"},
        },
    ],
    "oauth": [
        {
            "action": "check_csrf_state",
            "description": "OAuth2 flow without state parameter is vulnerable to CSRF",
            "tool": "http",
            "risk": 0.6,
            "params": {"method": "GET", "check": "oauth_state"},
        },
    ],
}


@dataclass
class DeepStudyResult:
    """Structured result of a deep study analysis."""

    target_name: str
    domain: str
    score: float
    endpoints_analyzed: int
    technologies: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    playbook_actions: list[dict[str, Any]]
    attack_surfaces: list[str]
    recommendations: list[str]
    summary: str
    raw: dict[str, Any] = field(default_factory=dict)


class TechAnalyzer:
    """Analyze technologies from httpx probe results and classify their risk."""

    HIGH_TECH_RISK = {
        "spring boot": 0.85,
        "firebase": 0.90,
        "graphql": 0.75,
        "stripe": 0.70,
        "oauth": 0.65,
    }
    MEDIUM_TECH_RISK = {
        "laravel": 0.55,
        "django": 0.50,
        "express": 0.45,
        "php": 0.50,
        "asp.net": 0.40,
        "nginx": 0.35,
    }

    @staticmethod
    def classify_tech_risk(tech_name: str) -> float:
        name = tech_name.lower()
        if name in TechAnalyzer.HIGH_TECH_RISK:
            return TechAnalyzer.HIGH_TECH_RISK[name]
        if name in TechAnalyzer.MEDIUM_TECH_RISK:
            return TechAnalyzer.MEDIUM_TECH_RISK[name]
        return 0.20

    @staticmethod
    def aggregate_from_httpx(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract unique technologies from httpx probe results."""
        seen: set[str] = set()
        technologies: list[dict[str, Any]] = []
        for r in results:
            techs = r.get("evidence", {}).get("technologies", []) if isinstance(r.get("evidence"), dict) else []
            for t in techs:
                name = t if isinstance(t, str) else t.get("name", str(t))
                if name.lower() not in seen:
                    seen.add(name.lower())
                    technologies.append(
                        {
                            "name": name,
                            "risk": TechAnalyzer.classify_tech_risk(name),
                            "source": "httpx",
                        }
                    )
        return technologies

    @staticmethod
    def aggregate_risk(technologies: list[dict[str, Any]]) -> float:
        """Compute aggregate risk score from detected technologies."""
        if not technologies:
            return 0.0
        max_risk = max(t.get("risk", 0.0) for t in technologies)
        avg_risk = sum(t.get("risk", 0.0) for t in technologies) / len(technologies)
        return min(1.0, max_risk * 0.6 + avg_risk * 0.4)


class PlaybookEngine:
    """Match detected technologies to attack playbooks."""

    @staticmethod
    def get_actions(technologies: list[dict[str, Any]]) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        seen_actions: set[str] = set()
        for tech in technologies:
            name = str(tech.get("name", "")).lower()
            playbook = TECH_PLAYBOOKS.get(name)
            if not playbook:
                continue
            for step in playbook:
                aid = step["action"]
                if aid not in seen_actions:
                    seen_actions.add(aid)
                    actions.append(
                        {
                            **step,
                            "tech": name,
                            "description": step["description"],
                        }
                    )
        return sorted(actions, key=lambda a: a.get("risk", 0), reverse=True)


class DeepStudyEngine:
    """Orchestrate deep study analysis for a target."""

    def __init__(
        self,
        httpx_tool: Any = None,
        copilot_agent: Any = None,
    ) -> None:
        self._httpx = httpx_tool
        self._copilot = copilot_agent

    async def run(self, target_id: int) -> DeepStudyResult:
        """Run full deep study on a target."""
        from api.services.data_service import get_target as svc_get_target
        from api.services.data_service import list_endpoints

        target = svc_get_target(target_id)
        if not target:
            return DeepStudyResult(
                target_name="unknown",
                domain="",
                score=0.0,
                endpoints_analyzed=0,
                technologies=[],
                hypotheses=[],
                playbook_actions=[],
                attack_surfaces=[],
                recommendations=[],
                summary="Target not found",
            )

        target_name = target.get("name", "unknown")
        domain = target.get("domain", "") or target_name

        # 1. Load and classify endpoints
        endpoints = list_endpoints(target_id, limit=200)[0] if callable(list_endpoints) else []
        classified: list[dict[str, Any]] = []
        for ep in endpoints:
            try:
                from cores.engine.unified_classifier import classify

                raw_params = getattr(ep, "parsed_params", "{}") if hasattr(ep, "parsed_params") else "{}"
                if isinstance(raw_params, str):
                    import json

                    params = json.loads(raw_params) if raw_params.strip() else {}
                else:
                    params = raw_params or {}
                ep_dict = {"path": ep.get("path", ""), "method": ep.get("method", "GET"), "parsed_params": params}
                cl = classify(ep_dict["path"], ep_dict["method"], params)
                classified.append({**ep_dict, **cl})
            except Exception:
                classified.append({"path": ep.get("path", ""), "method": ep.get("method", "GET"), "labels": []})

        # 2. Tech detection via httpx
        technologies: list[dict[str, Any]] = []
        if self._httpx is not None and classified:
            try:
                urls = [f"https://{domain}{ep.get('path', '')}" for ep in classified[:50]]
                httpx_results = self._httpx.probe(urls, tech_detect=True, timeout=60)
                technologies = TechAnalyzer.aggregate_from_httpx(
                    [r.to_dict() if hasattr(r, "to_dict") else r for r in httpx_results]
                )
            except Exception as exc:
                logger.debug("httpx probe failed: %s", exc)
        if not technologies:
            technologies = [{"name": "unknown", "risk": 0.20, "source": "inferred"}]

        # 3. Generate tech hypotheses
        tech_hypotheses: list[dict[str, Any]] = []
        try:
            from dataclasses import asdict

            raw_h = generate_from_technology(technologies, target_id, target_name)
            tech_hypotheses = [asdict(h) for h in raw_h]
        except Exception as exc:
            logger.debug("tech hypothesis generation failed: %s", exc)

        # 4. Match playbooks
        playbook_actions = PlaybookEngine.get_actions(technologies)

        # 5. Compute aggregate score
        tech_risk = TechAnalyzer.aggregate_risk(technologies)
        target_score = target.get("opportunity_score", 0) or target.get("roi", 0) or 0
        final_score = min(10.0, (target_score * 0.3 + tech_risk * 7.0) if target_score else tech_risk * 7.0)

        # 6. Build attack surfaces summary
        all_labels: set[str] = set()
        for ep in classified:
            for lb in ep.get("labels", []):
                all_labels.add(str(lb))
        attack_surfaces = sorted(all_labels)

        # 7. Generate recommendations
        recommendations = self._build_recommendations(technologies, tech_hypotheses, playbook_actions)

        # 8. COPILOT plan
        copilot_plan = None
        if self._copilot is not None:
            try:
                plan = self._copilot.create_plan(
                    finding={"vulnerability_type": "generic", "title": f"Deep study: {target_name}"}
                )
                if plan:
                    copilot_plan = plan.to_dict() if hasattr(plan, "to_dict") else {"id": str(plan.id)}
            except Exception:
                pass

        summary = self._compose_summary(
            target_name, domain, final_score, technologies, len(classified), len(tech_hypotheses)
        )

        return DeepStudyResult(
            target_name=target_name,
            domain=domain,
            score=round(final_score, 2),
            endpoints_analyzed=len(classified),
            technologies=technologies,
            hypotheses=tech_hypotheses,
            playbook_actions=playbook_actions,
            attack_surfaces=attack_surfaces,
            recommendations=recommendations,
            summary=summary,
            raw={
                "target": target,
                "endpoints": classified,
                "aggregate_tech_risk": round(tech_risk, 3),
                "copilot_plan": copilot_plan,
            },
        )

    def _build_recommendations(
        self,
        technologies: list[dict[str, Any]],
        hypotheses: list[dict[str, Any]],
        playbook_actions: list[dict[str, Any]],
    ) -> list[str]:
        recs: list[str] = []
        for tech in technologies:
            name = str(tech.get("name", ""))
            risk = tech.get("risk", 0.0)
            if risk >= 0.7:
                recs.append(f"HIGH PRIORITY: {name} detected (risk={risk:.0%}) — prioritize review")
            elif risk >= 0.4:
                recs.append(f"MEDIUM: {name} detected — investigate configuration")
        for h in hypotheses[:3]:
            reason = h.get("reasoning", "") or h.get("evidence", [""])[0] if isinstance(h.get("evidence"), list) else ""
            if reason:
                recs.append(f"Hypothesis: {reason[:120]}")
        for action in playbook_actions[:3]:
            recs.append(f"Playbook: {action['description'][:120]}")
        if not recs:
            recs.append("Basic: Run recon and endpoint discovery")
        return recs[:8]

    def _compose_summary(
        self,
        name: str,
        domain: str,
        score: float,
        technologies: list[dict[str, Any]],
        total_endpoints: int,
        total_hypotheses: int,
    ) -> str:
        tech_names = ", ".join(t.get("name", "?") for t in technologies[:5])
        return (
            f"Deep study for {name} ({domain}): "
            f"score={score:.1f}/10, "
            f"{total_endpoints} endpoints, "
            f"{total_hypotheses} tech hypotheses, "
            f"technologies=[{tech_names}]"
        )
