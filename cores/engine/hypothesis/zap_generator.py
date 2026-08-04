"""
hypothesis.zap_generator — Convert ZAP passive alerts into Hypothesis objects
with full didactic fields for beginner-friendly validation guidance.

Each ZAP passive alert maps to a VulnerabilityType and includes:
  - what_is_this: plain-language explanation
  - how_to_verify: ordered concrete steps the user must follow manually
  - estimated_difficulty / estimated_time_minutes
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from cores.engine.hypothesis.models import (
    Hypothesis,
    HypothesisSource,
    VulnerabilityType,
)

# ── Didactic knowledge base ─────────────────────────────────────────────

DIDACTIC_INFO: dict[str, dict[str, Any]] = {
    "missing_csp": {
        "what_is_this": "Content Security Policy (CSP) es un header de seguridad que le dice al navegador qué contenido puede cargar. Si falta, un atacante podría inyectar scripts maliciosos (XSS) y el navegador los ejecutaría sin restricción.",
        "real_world_impact": "Un atacante podría robar cookies de sesión, redirigir a páginas de phishing, o instalar malware en los visitantes del sitio. Es la puerta de entrada a ataques XSS masivos.",
        "difficulty": "fácil",
        "time_minutes": 10,
        "reward_range": "$50-$300",
    },
    "missing_hsts": {
        "what_is_this": "HSTS (HTTP Strict Transport Security) fuerza al navegador a usar siempre HTTPS. Sin este header, un atacante en la misma red (ej: WiFi público) puede interceptar la conexión y leer todo el tráfico.",
        "real_world_impact": "Ataque Man-in-the-Middle (MITM): un atacante en tu misma red puede ver contraseñas, tokens, y datos personales. El usuario no nota nada porque la página se ve igual.",
        "difficulty": "fácil",
        "time_minutes": 5,
        "reward_range": "$50-$200",
    },
    "missing_xfo": {
        "what_is_this": "X-Frame-Options previene que tu sitio sea cargado dentro de un iframe en otro dominio. Sin esto, un atacante puede poner tu página dentro de un iframe en su sitio malicioso (clickjacking).",
        "real_world_impact": "El usuario cree que está haciendo clic en tu sitio, pero en realidad está autorizando acciones sin saberlo: transferencias, cambios de email, publicación de contenido.",
        "difficulty": "fácil",
        "time_minutes": 5,
        "reward_range": "$50-$200",
    },
    "cookie_no_flags": {
        "what_is_this": "Las cookies sin flags Secure/HttpOnly pueden ser robadas por scripts maliciosos o enviadas por HTTP plano. Secure hace que solo se envíen por HTTPS; HttpOnly las protege de ser leídas por JavaScript.",
        "real_world_impact": "Un XSS en cualquier parte del sitio puede robar la cookie de sesión y secuestrar la cuenta del usuario. Sin Secure, además se filtran en redes no cifradas.",
        "difficulty": "fácil",
        "time_minutes": 10,
        "reward_range": "$100-$500",
    },
    "tls_weak": {
        "what_is_this": "El servidor acepta configuraciones TLS antiguas o débiles (TLS 1.0/1.1, cifrados inseguros). Esto permite a un atacante degradar la conexión y leer o modificar datos.",
        "real_world_impact": "Un atacante puede forzar la conexión a usar cifrado débil, descifrar el tráfico, e interceptar credenciales y datos sensibles como si no hubiera HTTPS.",
        "difficulty": "media",
        "time_minutes": 20,
        "reward_range": "$100-$500",
    },
    "cacheable_https": {
        "what_is_this": "Respuestas HTTPS que contienen información sensible (tokens, datos personales) están siendo almacenadas en la caché del navegador. Otro usuario del mismo equipo podría verlas.",
        "real_world_impact": "En un ordenador compartido, cualquier persona puede abrir las herramientas de desarrollo y leer respuestas cacheadas con datos sensibles como tokens API o información personal.",
        "difficulty": "fácil",
        "time_minutes": 5,
        "reward_range": "$50-$150",
    },
    "autofill_sensitive": {
        "what_is_this": "Campos sensibles (contraseñas, datos bancarios) permiten autocompletado en el navegador. Un atacante con acceso físico o remoto al equipo puede extraer estas credenciales almacenadas.",
        "real_world_impact": "Un malware o un atacante con acceso al navegador puede robar todas las contraseñas guardadas automáticamente mediante un simple script.",
        "difficulty": "fácil",
        "time_minutes": 5,
        "reward_range": "$50-$200",
    },
}

DEFAULT_DIDACTIC: dict[str, Any] = {
    "what_is_this": "ZAP detectó una configuración de seguridad anómala en las respuestas HTTP del servidor. Revisa la alerta para más detalles.",
    "real_world_impact": "Dependiendo del contexto, esta configuración podría permitir a un atacante interceptar, modificar o extraer información del sitio o sus usuarios.",
    "difficulty": "media",
    "time_minutes": 15,
    "reward_range": "$50-$500",
}

# ── Alert text → VulnerabilityType mapping ─────────────────────────────

ALERT_PATTERNS: list[tuple[re.Pattern, str, VulnerabilityType]] = [
    (
        re.compile(r"(?i)content.security.policy|missing.*csp|content.security"),
        "missing_csp",
        VulnerabilityType.MISSING_CSP,
    ),
    (re.compile(r"(?i)strict.transport.security|hsts|missing.*hsts"), "missing_hsts", VulnerabilityType.MISSING_HSTS),
    (re.compile(r"(?i)x.frame.options|clickjack|missing.*xfo|x.frame"), "missing_xfo", VulnerabilityType.MISSING_XFO),
    (
        re.compile(r"(?i)cookie.*secure|cookie.*httponly|cookie.*flag|cookie.*without"),
        "cookie_no_flags",
        VulnerabilityType.COOKIE_NO_FLAGS,
    ),
    (re.compile(r"(?i)tls.*weak|ssl.*weak|weak.*cipher|protocol.*old"), "tls_weak", VulnerabilityType.TLS_WEAK),
    (
        re.compile(r"(?i)cacheable|information.*leak.*cache|cache.*https"),
        "cacheable_https",
        VulnerabilityType.CACHEABLE_HTTPS,
    ),
    (
        re.compile(r"(?i)autocomplete|autofill|password.*autocomplete"),
        "autofill_sensitive",
        VulnerabilityType.AUTOFILL_SENSITIVE,
    ),
    (re.compile(r"(?i)x.xss.protection|missing.*xss"), "misconfiguration", VulnerabilityType.MISCONFIGURATION),
    (
        re.compile(r"(?i)info.*leak|information.*disclosure|directory.*listing|server.*leak"),
        "info_leak",
        VulnerabilityType.INFO_LEAK,
    ),
    (
        re.compile(r"(?i)x.content.type.options|nosniff|mime.*sniff"),
        "misconfiguration",
        VulnerabilityType.MISCONFIGURATION,
    ),
    (re.compile(r"(?i)permissions.policy|feature.policy"), "misconfiguration", VulnerabilityType.MISCONFIGURATION),
    (re.compile(r"(?i)referrer.*policy|referer.*leak"), "info_leak", VulnerabilityType.INFO_LEAK),
    (re.compile(r"(?i)open.*redirect|redirect.*unvalidated"), "misconfiguration", VulnerabilityType.MISCONFIGURATION),
    (re.compile(r"(?i)csrf|x.*csrf|cross.site.request"), "misconfiguration", VulnerabilityType.MISCONFIGURATION),
]


def classify_zap_alert(alert_name: str) -> tuple[VulnerabilityType, str]:
    """Map a ZAP alert name to a VulnerabilityType and a canonical key."""
    for pattern, key, vt in ALERT_PATTERNS:
        if pattern.search(alert_name):
            return vt, key
    if any(w in alert_name.lower() for w in ("header", "missing", "security", "x-", "x ")):
        return VulnerabilityType.MISCONFIGURATION, "misconfiguration"
    return VulnerabilityType.INFO_LEAK, "info_leak"


def generate_from_zap_alerts(
    target_id: int,
    target_name: str,
    zap_alerts: list[dict[str, Any]],
    endpoint_map: dict[str, int] | None = None,
) -> list[Hypothesis]:
    """Convert ZAP passive scan alerts into Hypothesis objects.

    Each alert becomes a Hypothesis with full didactic metadata so that
    even an inexperienced user understands the vulnerability, its impact,
    and exactly how to verify it step by step.
    """
    hypotheses: list[Hypothesis] = []
    seen: set[str] = set()

    for alert in zap_alerts:
        alert_name = alert.get("alert", "")
        url = alert.get("url", "")
        risk_score = alert.get("risk_score", 1)
        description = alert.get("description", "")
        solution = alert.get("solution", "")
        evidence_text = alert.get("evidence", "")
        confidence = alert.get("confidence", "Medium")
        plugin_id = str(alert.get("plugin_id", alert.get("pluginid", "")))
        param = alert.get("param", "")

        vt, canonical_key = classify_zap_alert(alert_name)
        dedup_key = f"{vt.value}:{url}:{param}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        didactic = DIDACTIC_INFO.get(canonical_key, DEFAULT_DIDACTIC)

        how_to_verify = _build_verification_steps(vt, url, param, alert_name, evidence_text)
        reasoning_parts = [f"ZAP passive scan detectó: {alert_name}"]
        if description:
            reasoning_parts.append(description)
        if url:
            reasoning_parts.append(f"URL afectada: {url}")
        if evidence_text:
            reasoning_parts.append(f"Evidencia: {evidence_text}")

        suggested = _build_suggested_actions(vt, solution, url)

        hyp_id = hashlib.sha256(f"zap:{target_id}:{plugin_id}:{url}:{param}".encode()).hexdigest()[:12]

        endpoint_id = None
        if endpoint_map:
            endpoint_id = endpoint_map.get(url.rstrip("/"), endpoint_map.get(url, None))

        conf_map = {"low": 0.3, "medium": 0.5, "high": 0.75, "true": 0.9}
        conf_value = conf_map.get(confidence.lower(), 0.5)
        likelihood = min(1.0, risk_score / 5.0 + conf_value)
        impact = min(1.0, risk_score / 4.0)

        hypotheses.append(
            Hypothesis(
                id=hyp_id,
                vulnerability_type=vt,
                target_id=target_id,
                target_name=target_name,
                endpoint={
                    "path": url,
                    "method": "GET",
                    "risk_score": float(risk_score),
                    "id": endpoint_id,
                    "alert_plugin": plugin_id,
                    "evidence": evidence_text,
                },
                likelihood=likelihood,
                impact=impact,
                exploitability=max(0.3, 1.0 - impact),
                confidence=conf_value,
                priority_score=risk_score * 10.0,
                evidence=[evidence_text] if evidence_text else [f"ZAP alert: {alert_name}"],
                reasoning="\n".join(reasoning_parts),
                suggested_actions=suggested,
                source=HypothesisSource.ZAP,
                vector=canonical_key,
                attack_surface_labels=["passive_recon", canonical_key],
                what_is_this=didactic["what_is_this"],
                why_suspected=f"ZAP analizó pasivamente el tráfico HTTP y detectó: {alert_name}"
                + (f" en {url}" if url else ""),
                real_world_impact=didactic["real_world_impact"],
                how_to_verify=tuple(how_to_verify),
                estimated_difficulty=didactic["difficulty"],
                estimated_time_minutes=didactic["time_minutes"],
                estimated_reward_range=didactic["reward_range"],
            )
        )

    return hypotheses


def _build_verification_steps(
    vt: VulnerabilityType,
    url: str,
    param: str,
    alert_name: str,
    evidence: str,
) -> list[str]:
    """Generate concrete step-by-step verification instructions."""
    steps = ["Abre las herramientas de desarrollador de tu navegador (F12 → Red o Network)."]

    if vt == VulnerabilityType.MISSING_CSP:
        steps += [
            f"Carga la URL: {url}",
            "Busca el header `Content-Security-Policy` en la respuesta HTTP (cabeceras de respuesta).",
            "Si no aparece, confirma que falta totalmente.",
            "Toma un screenshot con las DevTools abiertas mostrando los response headers.",
            "Verifica si hay un header similar con nombre distinto (X-Content-Security-Policy, etc.) — algunos son legacy.",
        ]
    elif vt == VulnerabilityType.MISSING_HSTS:
        steps += [
            f"Carga la URL: {url}",
            "Busca el header `Strict-Transport-Security` en la respuesta.",
            "Si no aparece, anota que falta.",
            "Revisa si hay una redirección HTTP→HTTPS antes de la respuesta final (la cabecera debe estar en la respuesta HTTPS final).",
        ]
    elif vt == VulnerabilityType.MISSING_XFO:
        steps += [
            f"Carga la URL: {url}",
            "Busca el header `X-Frame-Options` (DENY/SAMEORIGIN) o `Content-Security-Policy: frame-ancestors`.",
            "Si no aparece ninguno, confirma que falta.",
            "Como prueba de concepto: crea un HTML local con <iframe src='{url}'>, ábrelo en el navegador y haz screenshot.",
        ]
    elif vt == VulnerabilityType.COOKIE_NO_FLAGS:
        steps += [
            f"Carga la URL: {url}",
            "En la pestaña Red (Network), selecciona la respuesta y busca el header `Set-Cookie`.",
            "Verifica si la cookie tiene `Secure` y `HttpOnly` flags.",
            "Si la cookie de sesión no tiene HttpOnly, un script malicioso podría robarla vía document.cookie.",
            "Si no tiene Secure, se enviaría también por HTTP no cifrado.",
        ]
    elif vt == VulnerabilityType.TLS_WEAK:
        steps += [
            "Usa la herramienta online https://www.ssllabs.com/ssltest/ o el comando:",
            f"  openssl s_client -connect {_extract_host(url)}:443 -tls1_1",
            "Si el comando se conecta exitosamente, el servidor acepta TLS 1.1 o inferior (obsoleto/inseguro).",
            "Toma screenshot del resultado.",
        ]
    elif vt == VulnerabilityType.CACHEABLE_HTTPS:
        steps += [
            f"Carga la URL: {url}",
            "Busca el header `Cache-Control` en la respuesta. Si dice `public`, `max-age`, o no aparece, la respuesta es cacheable.",
            "Revisa si la respuesta contiene datos sensibles (tokens, emails, datos personales).",
            "Como prueba: abre la URL en una pestaña de incógnito, luego en otra normal — si se ve sin autenticación, está cacheada inadecuadamente.",
        ]
    elif vt == VulnerabilityType.AUTOFILL_SENSITIVE:
        steps += [
            f"Navega a: {url}",
            "Identifica campos de contraseña o datos sensibles.",
            'Inspecciona el HTML (clic derecho → Inspeccionar) y busca `autocomplete="on"` o ausencia de `autocomplete="off"`.',
            "Toma screenshot del código HTML del campo sensible.",
        ]
    else:
        steps += [
            f"Carga la URL: {url}",
            "Revisa las cabeceras de respuesta HTTP en la pestaña Red (Network) de las DevTools.",
            f"Busca evidencia relacionada con: {alert_name}",
            "Toma screenshot del panel de Red con la respuesta seleccionada.",
        ]

    steps.append("Documenta el hallazgo con screenshots y la URL exacta para agregarlo al reporte final.")
    return steps


def _build_suggested_actions(vt: VulnerabilityType, solution: str, url: str) -> list[str]:
    actions = ["Verificar manualmente esta hipótesis — sigue los pasos de 'how_to_verify'"]
    if solution:
        actions.append(f"Solución sugerida por ZAP: {solution}")
    actions.append(f"Si confirmas, documenta con screenshots de las DevTools para {url}")
    actions.append("Si es falso positivo, márcalo como tal para que el sistema aprenda")
    return actions


def _extract_host(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).hostname or url
