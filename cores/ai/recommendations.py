"""
Recommendation Engine — CATEYE

Generates actionable recommendations from real system data.
Each recommendation answers: what to do, why, and what's the expected value.

## `estimated_payout` se calcula SÓLO sobre verdicts confirmados

Medido 2026-10-08, antes del fix:

```
hackerone_api : 0 confirmed · 100 endpoints "críticos" · 99 IDOR → $498.000
hackerone_docs: 0 confirmed · 150 endpoints "críticos" · 20 IDOR → $490.000
```

La fórmula era `confirmed*5000 + len(critical_eps)*3000 + len(idor_eps)*2000`.
`critical_eps` son endpoints cuyo **score heurístico** pasa 50, y
`idor_eps` son candidatos a IDOR: **vulnerabilidades que nadie verificó**. El
sistema anunciaba casi medio millón de dólares por trabajo que no se había
hecho, y eso terminaba en el resumen diario como
*"Payout estimado: $498.000"*.

Un payout depende de verdicts confirmados —trabajo que existe y se
validó—, no de candidatos. Ahora:

- `estimated_payout` sale **sólo** de `confirmed_findings`.
- Los candidatos se reportan aparte como `candidate_index`, con su unidad
  declarada: es un índice de priorización, **no USD**.
"""

from __future__ import annotations

from typing import Any

from cores.engine.unified_scoring import generate_suggestions
from cores.engine.unified_scoring import score as unified_score
from cores.engine.unified_scoring import score_target as unified_score_target
from database import db, models

#: Valor de planificación por finding confirmado. **Sin fuente**: es un
#: placeholder, no una cotización de mercado. El repo no tiene todavía ni un
#: payout real (`RevenuePayout` no existe; `verdicts.total == 0` medido el
#: 2026-10-08), así que no hay de dónde sacarlo. Se reemplaza cuando exista
#: el primer pago. Lo que NO se hace es inventar el número en silencio: el
#: campo lleva `estimated_payout_status` al lado.
_CONFIRMED_FINDING_USD = 5000.0

#: Peso del índice de priorización por endpoint candidato. **No son dólares.**
_CANDIDATE_INDEX_CRITICAL = 3000
_CANDIDATE_INDEX_IDOR = 2000


def generate_recommendations() -> list[dict[str, Any]]:
    session = db.SessionLocal()
    try:
        recs: list[dict[str, Any]] = []
        targets = session.query(models.Target).all()
        endpoints = session.query(models.Endpoint).all()
        findings = session.query(models.Finding).all()
        verdicts = session.query(models.Verdict).all()

        for t in targets:
            t_eps = [ep for ep in endpoints if ep.target_id == t.id]
            if not t_eps:
                continue

            [f for f in findings if f.target_id == t.id]
            t_verdicts = [v for v in verdicts if v.endpoint_id and v.endpoint_id in {ep.id for ep in t_eps}]

            roi = unified_score_target(
                {
                    "api_count": len(t_eps),
                    "has_graphql": any("/graphql" in (ep.path or "").lower() for ep in t_eps),
                    "has_admin": any("admin" in (ep.path or "").lower() for ep in t_eps),
                    "has_api": any("/api/" in (ep.path or "") for ep in t_eps),
                    "has_exports": any("export" in (ep.path or "").lower() for ep in t_eps),
                    "source": (t.name or "").lower(),
                }
            )

            critical_eps = []
            idor_eps = []
            graphql_eps = []
            actionable_eps = []
            for ep in t_eps:
                s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                rs = s.get("risk_score", 0)
                if rs >= 50:
                    critical_eps.append({"path": ep.path, "method": ep.method, "score": rs})
                if s.get("potential_idor"):
                    idor_eps.append({"path": ep.path, "method": ep.method, "score": rs})
                if "graphql" in (ep.path or "").lower():
                    graphql_eps.append({"path": ep.path, "method": ep.method})
                if s.get("actionable"):
                    actionable_eps.append(
                        {
                            "path": ep.path,
                            "method": ep.method,
                            "score": rs,
                            "suggestions": generate_suggestions(ep.path, ep.method or "GET", ep.parsed_params),
                        }
                    )

            confirmed = sum(1 for v in t_verdicts if v.status == "confirmed")

            # Lo que se PAGA depende de verdicts confirmados. Antes esta
            # fórmula sumaba también los endpoints candidatos
            # (`critical_eps`, `idor_eps`), que son vulnerabilidades que
            # nadie verificó: un target con 100 candidatos valía "$498.000"
            # con 0 findings confirmados. Ver la nota del módulo.
            estimated_payout = confirmed * _CONFIRMED_FINDING_USD
            candidate_index = len(critical_eps) * _CANDIDATE_INDEX_CRITICAL + len(idor_eps) * _CANDIDATE_INDEX_IDOR

            time_estimate = max(30, len(actionable_eps) * 15 + len(critical_eps) * 20)

            priority = roi.get("priority", 0)
            if priority >= 50 or len(critical_eps) > 0:
                recs.append(
                    {
                        "type": "attack",
                        "target_id": t.id,
                        "target_name": t.name,
                        "domain": t.domain,
                        "priority_score": priority,
                        "roi_score": roi.get("roi_score", 0),
                        "quality": roi.get("quality", 0),
                        "complexity": roi.get("complexity_score", 0),
                        "critical_endpoints": len(critical_eps),
                        "idor_candidates": len(idor_eps),
                        "graphql_surfaces": len(graphql_eps),
                        "actionable_endpoints": len(actionable_eps),
                        "estimated_time_minutes": time_estimate,
                        "estimated_payout": estimated_payout,
                        "estimated_payout_basis": (
                            f"{confirmed} finding(s) confirmado(s) x ${_CONFIRMED_FINDING_USD:,.0f} "
                            "(placeholder sin fuente: no hay payouts reales todavia)"
                            if confirmed
                            else "UNKNOWN: 0 findings confirmados. Los endpoints candidatos NO se pagan"
                        ),
                        "candidate_index": candidate_index,
                        "candidate_index_unit": "indice de priorizacion (no USD)",
                        "confirmed_findings": confirmed,
                        "top_critical": critical_eps[:3],
                        "top_idor": idor_eps[:3],
                        "top_actionable": actionable_eps[:3],
                        "reason": (
                            f"ROI {roi.get('roi_score', 0):.0f} · "
                            f"{len(critical_eps)} críticos · "
                            f"{len(idor_eps)} IDOR potenciales · "
                            f"{len(graphql_eps)} GraphQL"
                        ),
                    }
                )

        recs.sort(key=lambda r: r.get("priority_score", 0), reverse=True)
        return recs
    finally:
        session.close()


def get_best_recommendation() -> dict[str, Any]:
    recs = generate_recommendations()
    if recs:
        return recs[0]
    return {
        "type": "no_recommendations",
        "target_name": "",
        "priority_score": 0,
        "reason": "No hay datos suficientes para generar recomendaciones. Agrega targets primero.",
        "estimated_time_minutes": 0,
        "estimated_payout": 0,
    }
