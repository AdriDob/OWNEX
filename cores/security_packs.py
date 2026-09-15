"""Security Audit Packs — checklists/templates vendibles ($0, Gumroad/Notion).

Packs deterministas desde el conocimiento OWNEX (OWASP Top 10, API, Mobile,
Cloud). Venta como producto digital ($29-99). Sin red, sin secretos.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("ownex.security_packs")

_PACKS: dict[str, dict[str, object]] = {
    "owasp_top10_checklist": {
        "title": "OWASP Top 10 — Checklist de auditoría",
        "price_usd": 29.0,
        "items": [
            "A01 Broken Access Control: IDOR en cada object-id, tests cross-user",
            "A02 Cryptographic Failures: TLS, secrets en respuestas, hashing",
            "A03 Injection: SQLi/NoSQL/SSTI/Command en cada input",
            "A04 Insecure Design: rate limits, flujos de negocio abusables",
            "A05 Misconfiguration: headers, CORS, verbos, errores verbosos",
            "A06 Vulnerable Components: SBOM + versiones EOL",
            "A07 Auth Failures: MFA, lockout, reset poisoning, session",
            "A08 Integrity Failures: CI/CD, updates sin firma, deserialización",
            "A09 Logging Failures: quién hizo qué, alertas, retención",
            "A10 SSRF: metadata cloud, rangos privados, allowlist",
        ],
    },
    "api_security_audit": {
        "title": "API Security Audit Template",
        "price_usd": 49.0,
        "items": [
            "Inventario: todos los endpoints + métodos + auth por endpoint",
            "BOLA/IDOR: sustituir IDs de otro usuario en cada CRUD",
            "AuthN/AuthZ: JWT alg-confusion, none, kid/jku, expiración",
            "Rate limiting: bypass por headers/IP/método/versión",
            "Mass assignment: inyectar role/isAdmin/price en create/update",
            "Exposición excesiva: comparar respuesta cruda vs lo que renderiza la UI",
            "Inyección: SQLi/NoSQL/SSRF en params/headers/body",
            "CORS + GraphQL introspection + depth limit si aplica",
        ],
    },
    "mobile_appsec_checklist": {
        "title": "Mobile AppSec Checklist (Android/iOS)",
        "price_usd": 39.0,
        "items": [
            "Storage: SharedPreferences/plist sin cifrar, backups, logs",
            "Transporte: pinning, TLS, secretos en tráfico (Burp)",
            "Deeplinks: schemes custom, redirect, auth-code en links",
            "Data exposure: PII en query GET, flags debug, export/backup",
            "Auth: sesión en path/query, biometric bypass, token storage",
        ],
    },
    "cloud_config_review": {
        "title": "Cloud Config Review (AWS/GCP)",
        "price_usd": 79.0,
        "items": [
            "IAM: least-privilege, boundaries, Access Analyzer, rotación",
            "Storage: block public, policies, encryption, logging",
            "Network: security groups abiertos, firewall rules, flow logs",
            "Secrets: nada en código/CI logs, Vault/KMS, rotación",
            "Backups: 3-2-1-1-0, restore testeado, RTO/RPO",
        ],
    },
}


def pack_list() -> list[dict[str, object]]:
    return [{"id": pid, "title": p["title"], "price_usd": p["price_usd"]} for pid, p in _PACKS.items()]


def get_pack(pack_id: str) -> dict[str, object] | None:
    pack = _PACKS.get(pack_id)
    if not pack:
        return None
    return {"id": pack_id, "title": pack["title"], "price_usd": pack["price_usd"], "items": list(pack["items"])}  # type: ignore[arg-type]


def render_pack_md(pack_id: str) -> str | None:
    pack = get_pack(pack_id)
    if not pack:
        return None
    lines = [f"# {pack['title']}", "", f"Precio sugerido: USD {pack['price_usd']}", "", "## Checklist", ""]
    for item in pack["items"]:  # type: ignore[union-attr]
        lines.append(f"- [ ] {item}")
    lines += ["", "---", "*Pack generado por OWNEX — uso comercial permitido al comprador.*"]
    return "\n".join(lines)
