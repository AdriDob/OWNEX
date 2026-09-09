"""Validation Planner — diseña estrategias de validación mínimas.

No "probar todo". Pensar:

  1. ¿Qué señal diferencia una vulnerabilidad real de un falso positivo?
  2. ¿Cuál es la prueba más barata que produce esa señal?
  3. ¿Necesito baseline? (casi siempre sí)
  4. ¿Cuántas requests son aceptables?

Para cada tipo de vulnerabilidad, genera un plan específico:
  - IDOR: baseline → swap ID → comparar respuesta
  - Auth Bypass: con auth → sin auth → comparar
  - SSRF: URL parametrizada → callback detect
  - XSS: payload injectado → reflection check
  - SQLi: sleep payload → timing check
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from core.validation.models import (
    AttackCandidate,
    ProbeInstruction,
    ProbeType,
    ValidationPlan,
    VulnType,
)

logger = logging.getLogger("orion.core.validation.planner")

# ── Máquinas de estados por tipo de vulnerabilidad ────────────

# Cada entrada define:
#   probes: lista de ProbeInstruction templates
#   strategy_summary: texto explicativo
#   signals_to_check: qué buscar en la respuesta


def _plan_idor(candidate: AttackCandidate) -> ValidationPlan:
    """Plan para IDOR: baseline → ID swap → comparar."""
    probes: list[ProbeInstruction] = []
    path = candidate.endpoint_path
    method = candidate.method.upper()
    headers = dict(candidate.headers_template)
    params = dict(candidate.param_values)

    # Señales a buscar
    signals = [
        "different user data returned",
        "missing authorization check",
        "object owned by different user accessible",
        "sequential ID enumeration possible",
    ]

    # Baseline: request normal
    probes.append(
        ProbeInstruction(
            probe_type=ProbeType.BASELINE,
            description="Request normal con ID propio — establece línea de base",
            method=method,
            path=path,
            headers=headers,
            params=dict(params),
            body=candidate.body_template,
            expected_signal="200 OK con datos del usuario legítimo",
            comparison_with="",
        )
    )

    # Probe 1: swap primer ID parameter
    if candidate.parameters_of_interest:
        param = candidate.parameters_of_interest[0]
        orig_val = candidate.param_values.get(param, "1")
        # Probar con un valor diferente (secuencial)
        swapped_params = dict(params)
        if orig_val.isdigit():
            swapped_val = str(int(orig_val) + 1)
        else:
            swapped_val = "00000000-0000-0000-0000-000000000000" if "-" in orig_val else f"{orig_val}_other"
        swapped_params[param] = swapped_val

        probes.append(
            ProbeInstruction(
                probe_type=ProbeType.ID_SWAP,
                description=f"Swap {param}={orig_val} → {swapped_val} — ¿responde con datos de otro usuario?",
                method=method,
                path=path,
                headers=headers,
                params=swapped_params,
                body=candidate.body_template,
                expected_signal="200 OK con datos de otro usuario (cambio en response)",
                comparison_with="baseline",
            )
        )

    # Probe 2: sin auth (si aplica)
    if candidate.requires_auth:
        no_auth_headers = {k: v for k, v in headers.items() if k.lower() not in ("authorization", "cookie")}
        probes.append(
            ProbeInstruction(
                probe_type=ProbeType.AUTH_BYPASS,
                description="Request sin auth headers — ¿responde igual que con auth?",
                method=method,
                path=path,
                headers=no_auth_headers,
                params=dict(params),
                body=candidate.body_template,
                expected_signal="401/403 si hay auth, 200 si no hay control",
                comparison_with="baseline",
            )
        )

    return ValidationPlan(
        attack_candidate_id=candidate.id,
        vulnerability_type=VulnType.IDOR,
        probes=probes,
        strategy_summary="Comparar respuesta con ID propio vs ID ajeno. Si difieren sin auth check → IDOR.",
        max_probes=3,
        requires_baseline=True,
        signals_to_check=signals,
    )


def _plan_auth_bypass(candidate: AttackCandidate) -> ValidationPlan:
    """Plan para Auth Bypass: con auth → sin auth → diferentes roles."""
    probes: list[ProbeInstruction] = []
    path = candidate.endpoint_path
    method = candidate.method.upper()
    headers = dict(candidate.headers_template)

    signals = [
        "endpoint accessible without authentication",
        "no redirect to login",
        "sensitive data exposed without auth",
        "403 bypass via header manipulation",
    ]

    # Baseline: con auth
    probes.append(
        ProbeInstruction(
            probe_type=ProbeType.BASELINE,
            description="Request con auth — línea de base",
            method=method,
            path=path,
            headers=headers,
            body=candidate.body_template,
            expected_signal="200 OK",
            comparison_with="",
        )
    )

    # Sin auth
    no_auth_headers = {k: v for k, v in headers.items() if k.lower() not in ("authorization", "cookie", "x-api-key")}
    probes.append(
        ProbeInstruction(
            probe_type=ProbeType.AUTH_BYPASS,
            description="Request completamente sin auth",
            method=method,
            path=path,
            headers=no_auth_headers,
            body=candidate.body_template,
            expected_signal="401/403 si hay control de acceso",
            comparison_with="baseline",
        )
    )

    # Auth header vacío
    empty_auth_headers = dict(headers)
    token_keys = [k for k in headers if k.lower() in ("authorization", "cookie", "x-api-key", "token")]
    for k in token_keys:
        empty_auth_headers[k] = ""
    probes.append(
        ProbeInstruction(
            probe_type=ProbeType.AUTH_BYPASS,
            description="Auth header vacío — ¿el servidor valida tokens vacíos?",
            method=method,
            path=path,
            headers=empty_auth_headers,
            body=candidate.body_template,
            expected_signal="401/403 esperado, 200 = bypass",
            comparison_with="baseline",
        )
    )

    return ValidationPlan(
        attack_candidate_id=candidate.id,
        vulnerability_type=VulnType.AUTH_BYPASS,
        probes=probes,
        strategy_summary="Comparar endpoint con y sin auth. Si responde igual → no hay control de acceso.",
        max_probes=3,
        requires_baseline=True,
        signals_to_check=signals,
    )


def _plan_ssrf(candidate: AttackCandidate) -> ValidationPlan:
    """Plan para SSRF: inyectar URL en parámetros."""
    probes: list[ProbeInstruction] = []
    method = candidate.method.upper()
    headers = dict(candidate.headers_template)
    params = dict(candidate.param_values)

    signals = [
        "URL parameter accepted as-is",
        "internal hostname resolved",
        "response contains fetched content",
        "request to attacker-controlled server",
    ]

    payload_url = "http://burpcollaborator.net/test"  # placeholder — reemplazar con server real

    # Baseline
    probes.append(
        ProbeInstruction(
            probe_type=ProbeType.BASELINE,
            description="Request normal — línea de base",
            method=method,
            path=candidate.endpoint_path,
            headers=headers,
            params=dict(params),
            body=candidate.body_template,
            expected_signal="200 OK normal",
            comparison_with="",
        )
    )

    # SSRF probe: reemplazar primer parámetro con URL
    if candidate.parameters_of_interest:
        param = candidate.parameters_of_interest[0]
        ssrf_params = dict(params)
        ssrf_params[param] = payload_url
        probes.append(
            ProbeInstruction(
                probe_type=ProbeType.PARAM_INJECTION,
                description=f"Inyectar URL en parámetro {param}: {payload_url}",
                method=method,
                path=candidate.endpoint_path,
                headers=headers,
                params=ssrf_params,
                body=candidate.body_template,
                expected_signal=f"Server conecta a {payload_url} o timeout",
                comparison_with="baseline",
            )
        )

    # URL en path
    probes.append(
        ProbeInstruction(
            probe_type=ProbeType.PARAM_INJECTION,
            description=f"Inyectar URL en path: append /{payload_url}",
            method=method,
            path=f"{candidate.endpoint_path}/{payload_url}",
            headers=headers,
            body=candidate.body_template,
            expected_signal="Diferencia contra baseline sugiere SSRF",
            comparison_with="baseline",
        )
    )

    return ValidationPlan(
        attack_candidate_id=candidate.id,
        vulnerability_type=VulnType.SSRF,
        probes=probes,
        strategy_summary="Reemplazar parámetros con URLs externas. Si el server las resuelve → SSRF.",
        max_probes=3,
        requires_baseline=True,
        signals_to_check=signals,
    )


def _plan_xss(candidate: AttackCandidate) -> ValidationPlan:
    """Plan para XSS: inyectar payload y verificar reflection."""
    probes: list[ProbeInstruction] = []
    method = candidate.method.upper()
    headers = dict(candidate.headers_template)
    params = dict(candidate.param_values)

    signals = [
        "payload reflected in response body",
        "no encoding/escaping of input",
        "HTML context injection possible",
        "script execution context present",
    ]

    test_payload = "<script>alert(1)</script>"

    # Baseline
    probes.append(
        ProbeInstruction(
            probe_type=ProbeType.BASELINE,
            description="Request normal — baseline",
            method=method,
            path=candidate.endpoint_path,
            headers=headers,
            params=dict(params),
            body=candidate.body_template,
            expected_signal="200 OK, payload NO reflejado",
            comparison_with="",
        )
    )

    # XSS probe
    if candidate.parameters_of_interest:
        param = candidate.parameters_of_interest[0]
        xss_params = dict(params)
        xss_params[param] = test_payload
        probes.append(
            ProbeInstruction(
                probe_type=ProbeType.PARAM_INJECTION,
                description=f"Inyectar '<script>alert(1)</script>' en {param}",
                method=method,
                path=candidate.endpoint_path,
                headers=headers,
                params=xss_params,
                body=candidate.body_template,
                expected_signal="Payload reflejado sin escapar en response",
                comparison_with="baseline",
            )
        )

    return ValidationPlan(
        attack_candidate_id=candidate.id,
        vulnerability_type=VulnType.XSS,
        probes=probes,
        strategy_summary="Inyectar HTML/JS en parámetros. Si se refleja sin escapar → XSS.",
        max_probes=2,
        requires_baseline=True,
        signals_to_check=signals,
    )


def _plan_sqli(candidate: AttackCandidate) -> ValidationPlan:
    """Plan para SQLi: sleep injection para time-based detection."""
    probes: list[ProbeInstruction] = []
    method = candidate.method.upper()
    headers = dict(candidate.headers_template)
    params = dict(candidate.param_values)

    signals = [
        "response time anomaly",
        "error message contains SQL syntax",
        "quote character causes error",
    ]

    # Baseline
    probes.append(
        ProbeInstruction(
            probe_type=ProbeType.BASELINE,
            description="Request normal — medir tiempo de respuesta",
            method=method,
            path=candidate.endpoint_path,
            headers=headers,
            params=dict(params),
            body=candidate.body_template,
            expected_signal="Tiempo de respuesta normal (baseline)",
            comparison_with="",
        )
    )

    # Sleep probe
    if candidate.parameters_of_interest:
        param = candidate.parameters_of_interest[0]
        sleep_params = dict(params)
        sleep_params[param] = "1' OR SLEEP(3)--"
        probes.append(
            ProbeInstruction(
                probe_type=ProbeType.SLEEP_DETECT,
                description=f"SQLi sleep: 1' OR SLEEP(3)-- en {param}",
                method=method,
                path=candidate.endpoint_path,
                headers=headers,
                params=sleep_params,
                body=candidate.body_template,
                expected_signal="Si response_time_ms >> baseline → SQLi probable",
                comparison_with="baseline",
            )
        )

        # Single quote error analysis
        error_params = dict(params)
        error_params[param] = "'"
        probes.append(
            ProbeInstruction(
                probe_type=ProbeType.ERROR_ANALYSIS,
                description="Single quote en parámetro — ¿error SQL revelado?",
                method=method,
                path=candidate.endpoint_path,
                headers=headers,
                params=error_params,
                body=candidate.body_template,
                expected_signal="Error 500 con mensaje SQL en response",
                comparison_with="baseline",
            )
        )

    return ValidationPlan(
        attack_candidate_id=candidate.id,
        vulnerability_type=VulnType.SQLI,
        probes=probes,
        strategy_summary="Inyectar SLEEP(3) y medir tiempo. Si response > 3s → SQLi probable.",
        max_probes=3,
        requires_baseline=True,
        signals_to_check=signals,
    )


# ── Registry ───────────────────────────────────────────────────

PLANNER_REGISTRY: dict[VulnType, Callable[[AttackCandidate], ValidationPlan]] = {
    VulnType.IDOR: _plan_idor,
    VulnType.AUTH_BYPASS: _plan_auth_bypass,
    VulnType.SSRF: _plan_ssrf,
    VulnType.XSS: _plan_xss,
    VulnType.SQLI: _plan_sqli,
}


class ValidationPlanner:
    """Diseña planes de validación estratégicos para AttackCandidates.

    Para cada tipo de vulnerabilidad, usa la estrategia más eficiente:
    máxima señal con mínima cantidad de requests.
    """

    def plan(self, candidate: AttackCandidate) -> ValidationPlan:
        """Genera un ValidationPlan para un AttackCandidate."""
        planner_fn = PLANNER_REGISTRY.get(candidate.vulnerability_type)
        if planner_fn:
            plan = planner_fn(candidate)
            logger.info(
                "[PLANNER] Plan generado: %s → %d probes (costo %d requests)",
                candidate.vulnerability_type.value,
                len(plan.probes),
                plan.estimated_cost,
            )
            return plan

        # Fallback: plan genérico
        logger.warning(
            "[PLANNER] No hay planner para %s — usando fallback genérico",
            candidate.vulnerability_type.value,
        )
        return self._generic_plan(candidate)

    def _generic_plan(self, candidate: AttackCandidate) -> ValidationPlan:
        """Plan genérico cuando no hay planner específico."""
        method = candidate.method.upper()
        headers = dict(candidate.headers_template)
        params = dict(candidate.param_values)

        probes = [
            ProbeInstruction(
                probe_type=ProbeType.BASELINE,
                description="Request baseline",
                method=method,
                path=candidate.endpoint_path,
                headers=headers,
                params=params,
                body=candidate.body_template,
                expected_signal="200 OK",
                comparison_with="",
            )
        ]

        if candidate.parameters_of_interest:
            param = candidate.parameters_of_interest[0]
            injected = dict(params)
            injected[param] = f"{params.get(param, '')}_test"
            probes.append(
                ProbeInstruction(
                    probe_type=ProbeType.CUSTOM,
                    description=f"Valor alterado en {param}",
                    method=method,
                    path=candidate.endpoint_path,
                    headers=headers,
                    params=injected,
                    body=candidate.body_template,
                    expected_signal="Diferencia contra baseline",
                    comparison_with="baseline",
                )
            )

        return ValidationPlan(
            attack_candidate_id=candidate.id,
            vulnerability_type=candidate.vulnerability_type,
            probes=probes,
            strategy_summary="Plan genérico: baseline + parámetro alterado",
            max_probes=2,
            requires_baseline=True,
            signals_to_check=["response differs from baseline"],
        )
