"""Seed v2 — premium demo data for ORION.
Safe to run multiple times (always cleans first).
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from database import db, models
from database.db import SessionLocal
from database.models_economic import (
    BountyTier, FinancialMetric, MemoryPattern, Program, ProgramIntel,
    ReportPriority, ScopeDocument,
)
from sqlalchemy import text

# ─── helpers ───────────────────────────────────────────────
def _hash_password(password: str) -> str:
    salt = os.urandom(32)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return salt.hex() + ":" + dk.hex()

def _ts(days: int = 0, hours_ago: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days, hours=hours_ago)

# ─── TARGET DEFINITIONS ────────────────────────────────────
TARGETS = [
    {
        "name": "Shopify",
        "domain": "api.shopify.com",
        "endpoints": [
            ("GET",  "/admin/api/2024-01/products.json",         '{"risk":"low","auth":"required"}'),
            ("GET",  "/admin/api/2024-01/orders.json",           '{"risk":"medium","auth":"required"}'),
            ("POST", "/admin/api/2024-01/products.json",         '{"risk":"high","auth":"required"}'),
            ("GET",  "/admin/api/2024-01/customers/{id}.json",   '{"risk":"critical","auth":"required","id_type":"uuid"}'),
            ("PUT",  "/admin/api/2024-01/orders/{id}/cancel.json", '{"risk":"high","auth":"required","id_type":"numeric"}'),
            ("GET",  "/admin/oauth/authorize",                   '{"risk":"low","auth":"none"}'),
            ("POST", "/admin/oauth/access_token",                '{"risk":"medium","auth":"none"}'),
            ("GET",  "/api/graphql.json",                        '{"risk":"high","auth":"required","is_graphql":true}'),
            ("POST", "/api/graphql.json",                        '{"risk":"critical","auth":"required","is_graphql":true}'),
            ("GET",  "/admin/api/2024-01/webhooks.json",         '{"risk":"medium","auth":"required"}'),
            ("POST", "/admin/api/2024-01/fulfillments.json",     '{"risk":"high","auth":"required"}'),
            ("GET",  "/admin/api/2024-01/discounts/{id}.json",   '{"risk":"medium","auth":"required","id_type":"numeric"}'),
            ("POST", "/admin/api/2024-01/price_rules.json",      '{"risk":"high","auth":"admin"}'),
            ("GET",  "/admin/api/2024-01/collects.json",         '{"risk":"low","auth":"required"}'),
        ],
        "findings": [
            {"ep_idx": 3,  "title": "IDOR en customer details — datos de cualquier tienda",
             "severity": "critical",
             "desc": "GET /admin/api/2024-01/customers/{id}.json permite iterar UUIDs de clientes de otras tiendas del mismo host compartido. Sin rate limiting efectivo."},
            {"ep_idx": 4,  "title": "Cancelación de pedidos sin ownership check",
             "severity": "high",
             "desc": "PUT /orders/{id}/cancel.json acepta IDs numéricos sin verificar que el pedido pertenezca al comercio autenticado."},
            {"ep_idx": 8,  "title": "GraphQL mutations sin rate limiting por usuario",
             "severity": "high",
             "desc": "POST /api/graphql.json permite ejecutar mutations costosas sin límite de consultas por token de acceso."},
            {"ep_idx": 12, "title": "Price rules modificables por usuarios no admin",
             "severity": "medium",
             "desc": "POST /admin/api/2024-01/price_rules.json acepta tokens de usuarios sin rol admin."},
            {"ep_idx": 6,  "title": "OAuth token leakage en referer header",
             "severity": "low",
             "desc": "El flujo OAuth no sanitiza el Referer header, potencial leakage del authorization code."},
        ],
    },
    {
        "name": "Discord",
        "domain": "discord.com",
        "endpoints": [
            ("GET",  "/api/v9/users/@me",                       '{"risk":"low","auth":"required"}'),
            ("GET",  "/api/v9/users/{id}/profile",               '{"risk":"medium","auth":"required","id_type":"snowflake"}'),
            ("POST", "/api/v9/channels/{id}/messages",           '{"risk":"medium","auth":"required","id_type":"snowflake"}'),
            ("GET",  "/api/v9/guilds/{id}/members",              '{"risk":"high","auth":"required","id_type":"snowflake"}'),
            ("PUT",  "/api/v9/guilds/{id}/members/{uid}/roles",  '{"risk":"critical","auth":"admin","id_type":"snowflake"}'),
            ("GET",  "/api/v9/users/@me/connections",            '{"risk":"low","auth":"required"}'),
            ("POST", "/api/v9/webhooks/{id}/{token}",            '{"risk":"high","auth":"none"}'),
            ("GET",  "/api/v9/guilds/{id}/audit-logs",           '{"risk":"medium","auth":"required","id_type":"snowflake"}'),
            ("GET",  "/api/v9/applications/{id}/commands",       '{"risk":"low","auth":"required"}'),
            ("POST", "/api/v9/interactions",                     '{"risk":"critical","auth":"none"}'),
            ("GET",  "/api/v9/guilds/{id}/emojis",               '{"risk":"low","auth":"required"}'),
            ("DELETE","/api/v9/channels/{id}/messages/{mid}",    '{"risk":"medium","auth":"required"}'),
        ],
        "findings": [
            {"ep_idx": 4,  "title": "Role assignment via guild member endpoint sin validación cross-server",
             "severity": "critical",
             "desc": "PUT /guilds/{id}/members/{uid}/roles permite asignar roles admin si el token pertenece a un miembro con permisos en el servidor, pero sin verificar el scope real del token."},
            {"ep_idx": 6,  "title": "Webhook execution público — sin autenticación",
             "severity": "high",
             "desc": "POST /api/v9/webhooks/{id}/{token} no requiere autenticación. Si el webhook ID/token se filtra, cualquiera puede enviar mensajes."},
            {"ep_idx": 9,  "title": "Interactions endpoint sin rate limit ni auth",
             "severity": "high",
             "desc": "POST /api/v9/interactions acepta solicitudes sin autenticación. Posible abuso para spam masivo."},
            {"ep_idx": 1,  "title": "Profile enumeration via snowflake ID",
             "severity": "medium",
             "desc": "GET /users/{id}/profile permite enumerar perfiles de usuarios mediante IDs snowflake secuenciales."},
        ],
    },
    {
        "name": "GitLab",
        "domain": "gitlab.com",
        "endpoints": [
            ("GET",  "/api/v4/projects",                         '{"risk":"low","auth":"required"}'),
            ("GET",  "/api/v4/projects/{id}",                     '{"risk":"medium","auth":"required","id_type":"numeric"}'),
            ("POST", "/api/v4/projects",                          '{"risk":"medium","auth":"required"}'),
            ("GET",  "/api/v4/projects/{id}/merge_requests",      '{"risk":"low","auth":"required"}'),
            ("POST", "/api/v4/projects/{id}/merge_requests",      '{"risk":"high","auth":"required"}'),
            ("GET",  "/api/v4/projects/{id}/repository/files",    '{"risk":"medium","auth":"required"}'),
            ("PUT",  "/api/v4/projects/{id}/members/{uid}",       '{"risk":"critical","auth":"admin"}'),
            ("GET",  "/api/v4/projects/{id}/variables",           '{"risk":"high","auth":"maintainer"}'),
            ("POST", "/api/v4/projects/{id}/deploy_keys",         '{"risk":"high","auth":"maintainer"}'),
            ("GET",  "/api/v4/projects/{id}/jobs",                '{"risk":"low","auth":"required"}'),
            ("POST", "/api/v4/projects/{id}/pipeline",            '{"risk":"medium","auth":"developer"}'),
            ("GET",  "/api/v4/projects/{id}/registry/repositories", '{"risk":"low","auth":"required"}'),
            ("DELETE","/api/v4/projects/{id}",                    '{"risk":"critical","auth":"owner"}'),
        ],
        "findings": [
            {"ep_idx": 6,  "title": "Member escalation — maintainer puede añadirse como owner",
             "severity": "critical",
             "desc": "PUT /projects/{id}/members/{uid} no valida correctamente el nivel del token. Un maintainer puede promoverse a owner manipulando el UID."},
            {"ep_idx": 7,  "title": "CI/CD variables expuestas en project forks",
             "severity": "high",
             "desc": "GET /projects/{id}/variables expone variables de CI/CD incluso en forks del proyecto si no se configuró correctamente la máscara."},
            {"ep_idx": 8,  "title": "Deploy keys accesibles por reporters",
             "severity": "medium",
             "desc": "POST /projects/{id}/deploy_keys acepta tokens de reporter como si fueran maintainer en ciertas configuraciones de proyecto."},
            {"ep_idx": 5,  "title": "Repository file content accesible sin permisos de lectura",
             "severity": "medium",
             "desc": "GET /projects/{id}/repository/files devuelve contenido de archivos incluso cuando el token no tiene scope de lectura."},
        ],
    },
    {
        "name": "Slack",
        "domain": "api.slack.com",
        "endpoints": [
            ("GET",  "/api/auth.test",                            '{"risk":"low","auth":"required"}'),
            ("POST", "/api/chat.postMessage",                     '{"risk":"medium","auth":"required"}'),
            ("POST", "/api/conversations.invite",                 '{"risk":"high","auth":"required"}'),
            ("GET",  "/api/conversations.history",                '{"risk":"medium","auth":"required"}'),
            ("GET",  "/api/users.list",                           '{"risk":"low","auth":"required"}'),
            ("POST", "/api/oauth.v2.access",                      '{"risk":"critical","auth":"none"}'),
            ("GET",  "/api/team.info",                            '{"risk":"low","auth":"required"}'),
            ("POST", "/api/files.upload",                         '{"risk":"medium","auth":"required"}'),
            ("GET",  "/api/admin.users.list",                     '{"risk":"high","auth":"admin"}'),
            ("POST", "/api/admin.users.setAdmin",                 '{"risk":"critical","auth":"admin"}'),
            ("GET",  "/api/conversations.list",                   '{"risk":"low","auth":"required"}'),
            ("POST", "/api/conversations.kick",                   '{"risk":"high","auth":"required"}'),
        ],
        "findings": [
            {"ep_idx": 9,  "title": "Admin user escalation — setAdmin sin ownership check",
             "severity": "critical",
             "desc": "POST /api/admin.users.setAdmin permite a un admin de workspace A promover usuarios en workspace B si el token tiene scope admin, sin verificar el workspace target."},
            {"ep_idx": 5,  "title": "OAuth token exchange sin state parameter validation",
             "severity": "high",
             "desc": "POST /api/oauth.v2.access no valida correctamente el parámetro state, permitiendo CSRF en el flujo OAuth."},
            {"ep_idx": 2,  "title": "Conversation invite a canales privados sin autorización",
             "severity": "high",
             "desc": "POST /api/conversations.invite permite invitar bots a canales privados si el token tiene scope de conversaciones."},
            {"ep_idx": 11, "title": "Conversation kick sin verificar pertenencia",
             "severity": "medium",
             "desc": "POST /api/conversations.kick acepta IDs de canales sin verificar que el usuario autenticado sea miembro."},
        ],
    },
    {
        "name": "WordPress",
        "domain": "wordpress.com",
        "endpoints": [
            ("GET",  "/wp-json/wp/v2/users",                     '{"risk":"low","auth":"none"}'),
            ("GET",  "/wp-json/wp/v2/users/{id}",                '{"risk":"medium","auth":"none","id_type":"numeric"}'),
            ("POST", "/wp-json/wp/v2/posts",                     '{"risk":"medium","auth":"required"}'),
            ("GET",  "/wp-json/wp/v2/posts/{id}",                '{"risk":"low","auth":"none"}'),
            ("POST", "/wp-json/wp/v2/media",                     '{"risk":"medium","auth":"required"}'),
            ("GET",  "/wp-json/wp/v2/options",                   '{"risk":"high","auth":"admin"}'),
            ("POST", "/wp-json/wp/v2/users/{id}/application-passwords", '{"risk":"critical","auth":"admin"}'),
            ("GET",  "/xmlrpc.php",                               '{"risk":"medium","auth":"none"}'),
            ("POST", "/xmlrpc.php",                               '{"risk":"high","auth":"none"}'),
            ("GET",  "/wp-json/wp/v2/plugins",                   '{"risk":"high","auth":"admin"}'),
            ("GET",  "/wp-admin/admin-ajax.php",                  '{"risk":"low","auth":"none"}'),
            ("GET",  "/.well-known/security.txt",                 '{"risk":"low","auth":"none"}'),
        ],
        "findings": [
            {"ep_idx": 6,  "title": "Application passwords sin límite de creación por usuario",
             "severity": "critical",
             "desc": "POST /users/{id}/application-passwords permite a un admin crear tokens de aplicación sin límite. Si el token admin se compromete, el atacante puede crear credenciales persistentes."},
            {"ep_idx": 8,  "title": "XML-RPC sin rate limiting — brute force de credenciales",
             "severity": "high",
             "desc": "POST /xmlrpc.php permite autenticación mediante system.multicall, evadiendo límites de login estándar."},
            {"ep_idx": 5,  "title": "Options endpoint expone configuración sensible",
             "severity": "medium",
             "desc": "GET /wp-json/wp/v2/options expone rutas de plugins activos, versiones, y config de sitio."},
            {"ep_idx": 9,  "title": "Plugin listing sin autenticación en configuraciones por defecto",
             "severity": "medium",
             "desc": "GET /wp-json/wp/v2/plugins lista todos los plugins instalados con sus versiones."},
        ],
    },
    {
        "name": "HackerOne",
        "domain": "api.hackerone.com",
        "endpoints": [
            ("GET",  "/v1/hackers/programs",                      '{"risk":"low","auth":"none"}'),
            ("GET",  "/v1/hackers/programs/{handle}",             '{"risk":"low","auth":"none"}'),
            ("GET",  "/v1/hackers/reports",                       '{"risk":"medium","auth":"required"}'),
            ("GET",  "/v1/hackers/reports/{id}",                  '{"risk":"medium","auth":"required","id_type":"numeric"}'),
            ("POST", "/v1/hackers/reports/{id}/comments",         '{"risk":"medium","auth":"required"}'),
            ("GET",  "/v1/hackers/me",                            '{"risk":"low","auth":"required"}'),
            ("POST", "/v1/hackers/reports",                       '{"risk":"high","auth":"required"}'),
            ("GET",  "/v1/hackers/bounties",                      '{"risk":"low","auth":"required"}'),
            ("GET",  "/v1/hackers/reports/{id}/attachments",      '{"risk":"low","auth":"required"}'),
            ("GET",  "/v1/hackers/programs/{handle}/scope",       '{"risk":"low","auth":"none"}'),
        ],
        "findings": [
            {"ep_idx": 6,  "title": "Report submission sin validación de duplicate en endpoint",
             "severity": "medium",
             "desc": "POST /v1/hackers/reports permite enviar reports duplicados sin validación server-side del contenido."},
            {"ep_idx": 3,  "title": "IDOR en report details — acceso a reports de otros hackers",
             "severity": "high",
             "desc": "GET /v1/hackers/reports/{id} con ID numérico permite acceder a metadata de reports de otros hackers cuando el report está en estado triaged."},
            {"ep_idx": 4,  "title": "Comment injection en reports cerrados",
             "severity": "low",
             "desc": "POST /v1/hackers/reports/{id}/comments permite agregar comentarios en reports cerrados sin verificar estado."},
        ],
    },
]

# ─── REPORT DATA ───────────────────────────────────────────
REPORTS = [
    {"target": 0, "status": "paid",      "vuln": "idor",      "severity": "critical", "est": 3000.0, "reward": 2500.0, "days": 45},
    {"target": 0, "status": "paid",      "vuln": "idor",      "severity": "high",     "est": 1500.0, "reward": 1000.0, "days": 38},
    {"target": 1, "status": "submitted", "vuln": "privilege_escalation", "severity": "critical", "est": 5000.0, "reward": 0.0, "days": 18},
    {"target": 1, "status": "paid",      "vuln": "idor",      "severity": "high",     "est": 2000.0, "reward": 1500.0, "days": 55},
    {"target": 2, "status": "paid",      "vuln": "privilege_escalation", "severity": "critical", "est": 4000.0, "reward": 3500.0, "days": 30},
    {"target": 2, "status": "submitted", "vuln": "idor",      "severity": "high",     "est": 2500.0, "reward": 0.0, "days": 12},
    {"target": 3, "status": "paid",      "vuln": "privilege_escalation", "severity": "critical", "est": 3500.0, "reward": 3000.0, "days": 60},
    {"target": 3, "status": "draft",     "vuln": "idor",      "severity": "high",     "est": 2000.0, "reward": 0.0, "days": 5},
    {"target": 4, "status": "paid",      "vuln": "authorization_bypass", "severity": "critical", "est": 2500.0, "reward": 2000.0, "days": 25},
    {"target": 4, "status": "draft",     "vuln": "idor",      "severity": "medium",  "est": 500.0,  "reward": 0.0, "days": 3},
    {"target": 5, "status": "submitted", "vuln": "idor",      "severity": "high",     "est": 1500.0, "reward": 0.0, "days": 10},
    {"target": 5, "status": "draft",     "vuln": "info_disclosure", "severity": "medium", "est": 500.0, "reward": 0.0, "days": 2},
]

# ─── MAIN ──────────────────────────────────────────────────
def main():
    db.init_db()
    session = SessionLocal()

    # Speed up SQLite
    session.execute(text("PRAGMA synchronous = OFF"))
    session.execute(text("PRAGMA journal_mode = MEMORY"))
    session.execute(text("PRAGMA cache_size = 100000"))
    session.execute(text("PRAGMA foreign_keys = OFF"))

    # Ensure all model columns exist in the database schema
    schema_fixes = [
        "ALTER TABLE program_intel ADD COLUMN difficulty VARCHAR DEFAULT 'medium'",
        "ALTER TABLE program_intel ADD COLUMN estimated_competition FLOAT DEFAULT 0.5",
        "ALTER TABLE program_intel ADD COLUMN related_findings TEXT",
        "ALTER TABLE program_intel ADD COLUMN past_reports TEXT",
        "ALTER TABLE program_intel ADD COLUMN speed_rating VARCHAR DEFAULT 'average'",
        "ALTER TABLE program_intel ADD COLUMN best_vuln_types TEXT",
        "ALTER TABLE program_intel ADD COLUMN probability_of_success FLOAT DEFAULT 0.3",
        "ALTER TABLE program_intel ADD COLUMN recommended_approach TEXT",
    ]
    for fix in schema_fixes:
        try:
            session.execute(text(fix))
            print(f"  ✓ Schema: {fix}")
        except Exception:
            pass  # column already exists
    session.commit()

    print("🧹 Cleaning existing data…")
    tables = [
        "submission_records", "report_versions", "report_priorities",
        "delivery_records", "evidence", "validation_results", "validation_runs",
        "scan_runs", "pipeline_runs",
        "verdicts", "findings", "endpoints",
        "tasks", "quick_wins", "investigations",
        "notifications", "favorites", "sessions",
        "target_sessions", "target_identities",
        "financial_metrics", "scope_documents", "program_intel", "bounty_tiers",
        "memory_patterns", "memory_records",
        "reports",
        "programs",
        "target_scopes", "targets_intel",
        "devices", "learning_events", "investigator_profiles",
        "targets",
        "users",
    ]
    for t in tables:
        try:
            session.execute(text(f"DELETE FROM {t}"))
        except Exception as e:
            print(f"  ⚠  {t}: {e}")
    session.commit()
    print("  ✓ All tables cleaned.")

    # ── User ────────────────────────────────────────────
    print("\n👤 Creating user…")
    session.execute(text("DELETE FROM users WHERE email = 'admin@orion.io'"))
    session.commit()
    user = models.User(
        username="admin",
        email="admin@orion.io",
        password_hash=_hash_password("orion2024"),
        is_active=True,
    )
    session.add(user)
    session.flush()
    print(f"  ✓ admin@orion.io / orion2024  (user id={user.id})")

    # ── Targets + Endpoints + Findings ─────────────────
    print("\n🎯 Creating targets…")
    target_map = {}
    finding_map = {}

    for ti, td in enumerate(TARGETS):
        t = models.Target(name=td["name"], domain=td["domain"], created_at=_ts(days=90 - ti * 10))
        session.add(t)
        session.flush()
        target_map[ti] = t

        for ei, (method, path, params) in enumerate(td["endpoints"]):
            ep = models.Endpoint(
                target_id=t.id,
                method=method,
                path=path,
                params=params,
                discovered_at=_ts(days=85 - ti * 10 + ei),
            )
            session.add(ep)
            session.flush()

        found_count = 0
        for fi, fd in enumerate(td["findings"]):
            ep = session.query(models.Endpoint).filter(
                models.Endpoint.target_id == t.id,
            ).all()
            finding = models.Finding(
                target_id=t.id,
                endpoint_id=ep[fd["ep_idx"]].id if fd["ep_idx"] < len(ep) else None,
                title=fd["title"],
                severity=fd["severity"],
                description=fd["desc"],
                created_at=_ts(days=80 - ti * 10 - fi * 5),
            )
            session.add(finding)
            session.flush()
            finding_map[(ti, fi)] = finding
            found_count += 1

        print(f"  ✓ {td['name']:12s}  {len(td['endpoints']):3d} endpoints, {found_count} findings")

    session.commit()

    # ── Verdicts (one per finding) ─────────────────────
    print("\n⚖️  Creating verdicts…")
    verdict_count = 0
    for ti, td in enumerate(TARGETS):
        for fi, fd in enumerate(td["findings"]):
            finding = finding_map.get((ti, fi))
            if not finding:
                continue
            status = "confirmed" if fd["severity"] in ("critical", "high") else "inconclusive"
            v = models.Verdict(
                hot_path_id=f"hp-{finding.id}",
                endpoint_id=finding.endpoint_id,
                status=status,
                confidence=json.dumps({"overall": 0.85 if status == "confirmed" else 0.45}),
                reproducibility_score=json.dumps({"attempts": 3, "consistent": True}),
                validation_report=json.dumps({
                    "passed_rules": ["privilege_boundary_break", "sensitive_data_exposure"] if status == "confirmed" else [],
                    "failed_rules": [] if status == "confirmed" else ["auth_bypass"],
                    "details": "Found 3/3 consistent responses indicating authorization bypass",
                }),
                reason="Access control verification confirmed" if status == "confirmed" else "Insufficient evidence for conclusive verdict",
                retry_count=3,
                created_at=_ts(days=75 - ti * 10 - fi * 5),
            )
            session.add(v)
            session.flush()

            # Evidence for confirmed verdicts
            if status == "confirmed":
                evidence = models.Evidence(
                    verdict_id=v.id,
                    endpoint_id=finding.endpoint_id,
                    attempt_label="attempt_1",
                    request_url=f"https://{td['domain']}{td['endpoints'][fd['ep_idx']][1]}" if fd["ep_idx"] < len(td["endpoints"]) else "/",
                    request_method=td["endpoints"][fd["ep_idx"]][0] if fd["ep_idx"] < len(td["endpoints"]) else "GET",
                    request_headers=json.dumps({"Authorization": "Bearer eyJ...", "Content-Type": "application/json"}),
                    auth_label="user_a",
                    response_status=200,
                    response_headers=json.dumps({"content-type": "application/json", "x-request-id": "abc123"}),
                    response_body=json.dumps({"id": 12345, "email": "victim@example.com", "role": "admin", "sensitive": "***"}),
                    status_match="true",
                    body_diff_ratio="0.12",
                    sensitive_fields=json.dumps(["email", "role", "sensitive"]),
                    consistent="true",
                    curl_command=f"curl -H 'Authorization: Bearer TOKEN' https://{td['domain']}{td['endpoints'][fd['ep_idx']][1]}",
                )
                session.add(evidence)
            verdict_count += 1

    session.commit()
    print(f"  ✓ {verdict_count} verdicts ({sum(1 for td in TARGETS for fd in td['findings'] if fd['severity'] in ('critical','high'))} confirmed)")

    # ── Reports ─────────────────────────────────────────
    print("\n📄 Creating reports…")
    report_count = 0
    for rd in REPORTS:
        tname = TARGETS[rd["target"]]["name"]
        target = target_map[rd["target"]]

        rep = models.Report(
            program=tname,
            target=tname,
            vulnerability=rd["vuln"],
            severity=rd["severity"],
            status=rd["status"],
            format="markdown",
            estimated_reward=rd["est"],
            confirmed_reward=rd["reward"],
            evidence_count=2 if rd["status"] == "paid" else 1 if rd["status"] == "submitted" else 0,
            finding_ids=json.dumps([f.id for f in session.query(models.Finding).filter(models.Finding.target_id == target.id).limit(3).all()]),
            content=json.dumps({
                "summary": f"{rd['severity'].upper()}: {rd['vuln'].replace('_', ' ').title()} in {tname}",
                "reproduction": "1. Authenticate to the target\n2. Send crafted request to vulnerable endpoint\n3. Observe unauthorized access",
                "impact": "An attacker could exploit this vulnerability to access unauthorized resources",
                "remediation": "Implement proper access control checks on the affected endpoint",
            }),
            notes="",
            timeline=json.dumps([
                {"event": "created", "date": _ts(days=rd["days"] + 5).isoformat()},
                {"event": "validated", "date": _ts(days=rd["days"] + 3).isoformat()},
            ]),
            created_at=_ts(days=rd["days"]),
        )
        session.add(rep)
        session.flush()

        if rd["status"] == "paid":
            sub = models.SubmissionRecord(
                report_id=rep.id,
                platform="hackerone",
                external_id=f"H1-{100000 + rep.id}",
                status="resolved",
                submitted_at=_ts(days=rd["days"] - 2),
                last_update=_ts(days=1),
            )
            session.add(sub)

        if rd["status"] in ("submitted", "paid"):
            rp = ReportPriority(
                report_id=rep.id,
                estimated_reward=rd["est"],
                confidence_score=0.85,
                acceptance_probability=0.75 if rd["status"] == "submitted" else 1.0,
                expected_value=rd["est"] * 0.75,
                priority_score=85.0,
                priority_rank=report_count + 1,
                reasoning=f"High confidence IDOR with reproducible PoC on {tname}",
            )
            session.add(rp)

        report_count += 1

    session.commit()
    print(f"  ✓ {report_count} reports ({sum(1 for r in REPORTS if r['status']=='paid')} paid, {sum(1 for r in REPORTS if r['status']=='submitted')} submitted)")

    # ── Programs (Economic Intelligence) ───────────────
    print("\n📊 Creating programs (economic intelligence)…")
    platform_map = {
        0: "hackerone", 1: "hackerone", 2: "hackerone",
        3: "bugcrowd", 4: "hackerone", 5: "hackerone",
    }
    for ti, td in enumerate(TARGETS):
        prog = Program(
            name=td["name"],
            platform=platform_map.get(ti, "hackerone"),
            program_url=f"https://{'hackerone.com' if platform_map.get(ti) == 'hackerone' else 'bugcrowd.com'}/{td['name'].lower()}",
            private=False,
            status="active",
            technologies=json.dumps(["Ruby on Rails", "React", "GraphQL", "PostgreSQL", "Redis", "Kubernetes"]),
            assets=json.dumps([f"*.{td['domain'].replace('api.', '')}", td["domain"]]),
            orion_score=round(95 - ti * 5 + hash(td["name"]) % 10, 1),
            total_reports=sum(1 for r in REPORTS if TARGETS[r["target"]]["name"] == td["name"]),
            confirmed_reports=sum(1 for r in REPORTS if TARGETS[r["target"]]["name"] == td["name"] and r["status"] == "paid"),
            total_earned=round(sum(r["reward"] for r in REPORTS if TARGETS[r["target"]]["name"] == td["name"] and r["status"] == "paid"), 2),
            total_hours_spent=round(40 - ti * 5 + hash(td["name"]) % 10, 1),
            last_scope_fetch=_ts(days=30 - ti * 5),
            last_scope_hash=hashlib.sha256(td["name"].encode()).hexdigest()[:16],
        )
        session.add(prog)
        session.flush()

        # Bounty tiers
        tiers = [
            ("critical", 2000, 10000),
            ("high", 500, 2000),
            ("medium", 200, 500),
            ("low", 50, 200),
        ]
        for tier_name, mn, mx in tiers:
            bt = BountyTier(
                program_id=prog.id,
                tier_name=tier_name,
                min_reward=mn,
                max_reward=mx,
                requirements=f"Reproducible PoC with clear impact demonstrated for {tier_name} issues",
            )
            session.add(bt)

        # Program intel
        pi = ProgramIntel(
            program_id=prog.id,
            ai_summary=f"A high-value {td['name']} bug bounty program with extensive attack surface. Known for good response times and fair payouts.",
            technologies_list=json.dumps(["Ruby on Rails", "React", "GraphQL"]),
            recent_changes=json.dumps([
                {"date": _ts(days=15).isoformat(), "description": "Added new API v2 endpoints for customer management"},
                {"date": _ts(days=45).isoformat(), "description": "Updated scope to include mobile API endpoints"},
            ]),
            historical_bugs=json.dumps([
                {"type": "IDOR", "count": 12, "top_payout": 5000},
                {"type": "SSRF", "count": 5, "top_payout": 3500},
            ]),
            interesting_endpoints=json.dumps(td["endpoints"][:5]),
            notes="High potential for IDOR and GraphQL introspection vulnerabilities.",
            score=88.0 - ti * 5,
        )
        session.add(pi)

        # Scope document
        sd = ScopeDocument(
            program_id=prog.id,
            original_url=f"https://{platform_map.get(ti, 'hackerone')}.com/{td['name'].lower()}/scope",
            content_type="html",
            raw_text=f"In-scope assets for {td['name']}: *.{td['domain'].replace('api.', '')}, {td['domain']}, mobile app (Android + iOS).",
            summary=f"Scope includes web application at {td['domain']} and associated subdomains. Mobile API also in scope.",
            hash=hashlib.sha256(f"{td['name']}-scope-v3".encode()).hexdigest(),
            assets_extracted=json.dumps({"wildcards": [f"*.{td['domain'].replace('api.', '')}"], "domains": [td['domain']]}),
            changes_from_previous=json.dumps({"added": [], "removed": []}),
            fetched_at=_ts(days=30 - ti * 5),
        )
        session.add(sd)

    session.commit()
    print(f"  ✓ {len(TARGETS)} programs with intel, scope documents, and bounty tiers")

    # ── Financial Metrics ──────────────────────────────
    print("\n💰 Creating financial metrics…")
    fm_data = [
        ("usd_per_hour", None, 185.0, "all_time"),
        ("usd_per_hour", None, 220.0, "monthly"),
        ("usd_per_hour", None, 95.0, "weekly"),
        ("total_earned", None, 13500.0, "all_time"),
        ("total_earned", None, 4200.0, "monthly"),
        ("total_earned", None, 1200.0, "weekly"),
        ("total_pending", None, 8500.0, "all_time"),
        ("reports_submitted", None, 12.0, "all_time"),
        ("reports_paid", None, 7.0, "all_time"),
        ("acceptance_rate", None, 0.58, "all_time"),
    ]
    for mt, dim, val, period in fm_data:
        fm = FinancialMetric(metric_type=mt, dimension=dim, value=val, period=period)
        session.add(fm)
    # Weekly time series (last 12 weeks)
    for w in range(12):
        base = [800, 1200, 950, 1500, 1100, 1800, 900, 1300, 1000, 1600, 1200, 1400]
        fm = FinancialMetric(
            metric_type="weekly_earnings",
            dimension=None,
            value=base[w] + hash(str(w)) % 200,
            period="weekly",
            recorded_at=_ts(days=w * 7),
        )
        session.add(fm)
    session.commit()
    print(f"  ✓ Financial metrics seeded")

    # ── Notifications ──────────────────────────────────
    print("\n🔔 Creating notifications…")
    notif_templates = [
        ("finding_discovered", "Nuevo hallazgo crítico", "Se detectó un IDOR crítico en Shopify"),
        ("verdict_confirmed", "Veredicto confirmado", "IDOR en Discord confirmado tras 3 intentos"),
        ("report_submitted", "Reporte enviado", "Reporte de GitLab enviado a HackerOne"),
        ("report_paid", "💰 Recompensa recibida", "Reporte de Shopify pagado: $2,500 USD"),
        ("report_paid", "💰 Recompensa recibida", "Reporte de Slack pagado: $3,000 USD"),
        ("report_paid", "💰 Recompensa recibida", "Reporte de GitLab pagado: $3,500 USD"),
        ("scan_completed", "Escaneo completado", "Escaneo de WordPress finalizado - 35 endpoints descubiertos"),
        ("scan_completed", "Escaneo completado", "Escaneo de Shopify finalizado - 42 endpoints descubiertos"),
        ("scope_changed", "Cambio en scope detectado", "Se detectaron cambios en el scope de HackerOne"),
        ("opportunity_found", "Nueva oportunidad", "Alta probabilidad de SSRF en endpoint de Slack"),
        ("system_ready", "Sistema listo", "Pipeline autónomo inicializado correctamente"),
        ("daily_briefing", "Briefing diario", "5 programas activos, 3 reports pendientes de revisión"),
    ]
    n_count = 0
    for i, (ntype, title, msg) in enumerate(notif_templates):
        n = models.Notification(
            notification_type=ntype,
            title=title,
            message=msg,
            severity="info" if ntype != "report_paid" else "success",
            is_read="false" if i < 6 else "true",
            created_at=_ts(days=5 * i + 1, hours_ago=i * 3),
        )
        session.add(n)
        n_count += 1
    session.commit()
    print(f"  ✓ {n_count} notifications")

    # ── Pipeline Runs ──────────────────────────────────
    print("\n🔄 Creating pipeline runs…")
    stages = ["discovery", "recon", "analysis", "hypothesis", "validation", "reporting"]
    pipeline_count = 0
    for ti in range(3):
        for s in stages[:random_len(ti + 2)]:
            pr = models.PipelineRun(
                target_id=target_map[ti].id,
                correlation_id=f"pipe-{ti}-{s}-{hash(str(ti)+s) % 10000}",
                current_state="completed",
                state_history=json.dumps([{"state": s, "ts": _ts(days=60 - ti * 15).isoformat()}]),
                quality_score=round(0.7 + (hash(str(ti)) % 30) / 100, 2),
                retry_count=0,
                created_at=_ts(days=60 - ti * 15),
                completed_at=_ts(days=58 - ti * 15),
            )
            session.add(pr)
            pipeline_count += 1
    session.commit()
    print(f"  ✓ {pipeline_count} pipeline runs")

    # ── Investigations ─────────────────────────────────
    print("\n🔍 Creating investigations…")
    inv_names = [
        ("Shopify API Deep Dive", "active", 0),
        ("Discord Privilege Escalation Chain", "active", 1),
        ("GitLab CI/CD Security Audit", "completed", 2),
        ("Slack OAuth & Admin API Review", "paused", 3),
    ]
    inv_count = 0
    for name, status, ti in inv_names:
        inv = models.Investigation(
            target_id=target_map[ti].id,
            name=name,
            status=status,
            pipeline_state=json.dumps({"recon": True, "hypotheses": True, "validation": status == "completed", "reporting": status == "completed"}),
            notes=f"Focused investigation on {TARGETS[ti]['name']} for access control vulnerabilities.",
            tags=json.dumps(["IDOR", "privilege-escalation", "api-audit"]),
            created_at=_ts(days=40 - ti * 10),
        )
        session.add(inv)
        inv_count += 1
    session.commit()
    print(f"  ✓ {inv_count} investigations")

    # ── Tasks ──────────────────────────────────────────
    print("\n📋 Creating tasks…")
    tasks_data = [
        ("Review Shopify customer IDOR finding", "high", "pending", "finding", 1),
        ("Prepare Discord report for submission", "high", "in_progress", "report", 1),
        ("Validate Slack conversation.invite PoC", "medium", "pending", "finding", 2),
        ("Review GitLab CI/CD variables exposure", "medium", "waiting", "finding", 2),
        ("Test WordPress XML-RPC credential brute force", "low", "pending", "finding", 3),
    ]
    for title, priority, status, ltype, lid in tasks_data:
        t = models.Task(
            title=title,
            description=f"Task: {title}",
            status=status,
            priority=priority,
            linked_type=ltype,
            linked_id=lid,
            created_at=_ts(days=20),
        )
        session.add(t)
    session.commit()
    print(f"  ✓ {len(tasks_data)} tasks")

    # ── Quick Wins ─────────────────────────────────────
    print("\n⚡ Creating quick wins…")
    qw_data = [
        (0, "IDOR en customer endpoint", "high", "Endpoint de clientes expone datos de otros comercios vía UUID iterable"),
        (1, "Webhook sin autenticación", "high", "Webhook endpoint permite envío de mensajes sin token válido"),
        (2, "CI/CD variables exposure", "medium", "Variables de entorno expuestas en forks del proyecto"),
        (3, "OAuth CSRF sin state", "high", "Flujo OAuth v2 sin validación de state parameter"),
        (4, "XML-RPC brute force", "medium", "xmlrpc.php permite autenticación masiva sin rate limit"),
    ]
    for ti, title, impact, desc in qw_data:
        qw = models.QuickWin(
            target_id=target_map[ti].id,
            title=title,
            impact=impact,
            description=desc,
            created_at=_ts(days=25 - ti * 3),
        )
        session.add(qw)
    session.commit()
    print(f"  ✓ {len(qw_data)} quick wins")

    # ── Memory Patterns ────────────────────────────────
    print("\n🧠 Creating memory patterns…")
    patterns = [
        ("vuln_type", "IDOR en APIs REST con UUIDs predecibles tiene alta tasa de aceptación", json.dumps({"programs": ["Shopify", "Discord"], "success_rate": 0.82}), 0.85, 12),
        ("vuln_type", "GraphQL introspection combinado con field suggestions revela schema completo", json.dumps({"programs": ["Shopify", "GitLab"], "success_rate": 0.91}), 0.90, 8),
        ("platform", "HackerOne responde más rápido que Bugcrowd en reports críticos", json.dumps({"avg_hours": {"hackerone": 24, "bugcrowd": 72}}), 0.78, 15),
        ("tech", "Aplicaciones Ruby on Rails suelen tener IDOR en nested resources", json.dumps({"technologies": ["Rails"], "hit_rate": 0.73}), 0.72, 9),
        ("company_type", "Fintechs tienen mejores bounties en critical severity", json.dumps({"avg_payout": 4500, "sample": 22}), 0.80, 7),
    ]
    for cat, obs, ctx, conf, ev_count in patterns:
        mp = MemoryPattern(
            category=cat,
            observation=obs,
            context=ctx,
            confidence=conf,
            evidence_count=ev_count,
            created_at=_ts(days=60),
        )
        session.add(mp)
    session.commit()
    print(f"  ✓ {len(patterns)} memory patterns")

    # ── Session ────────────────────────────────────────
    print("\n💼 Creating default session…")
    sess = models.Session(
        name="Investigación activa",
        current_target_id=target_map[0].id,
        current_investigation=json.dumps({"id": 1, "name": "Shopify API Deep Dive"}),
        open_evidence_ids=json.dumps([1, 2]),
    )
    session.add(sess)
    session.commit()
    print("  ✓ Default session")

    # ── Scan Runs ──────────────────────────────────────
    print("\n📡 Creating scan runs…")
    for ti in range(len(TARGETS)):
        sr = models.ScanRun(
            target_id=target_map[ti].id,
            mode="FAST",
            status="completed",
            endpoint_count=len(TARGETS[ti]["endpoints"]),
            outputs=json.dumps({"tools": ["subfinder", "httpx", "nuclei"], "findings": len(TARGETS[ti]["findings"])}),
            started_at=_ts(days=80 - ti * 10),
            finished_at=_ts(days=80 - ti * 10, hours_ago=2),
        )
        session.add(sr)
    session.commit()
    print(f"  ✓ {len(TARGETS)} scan runs")

    # ── Favorites ──────────────────────────────────────
    print("\n⭐ Creating favorites…")
    favs = [
        ("target", 1, "Shopify - primary target"),
        ("report", 1, "Shopify IDOR report - paid"),
        ("finding", 1, "Discord critical finding"),
        ("quick_win", 1, "High priority quick win"),
    ]
    for item_type, item_id, label in favs:
        f = models.Favorite(item_type=item_type, item_id=item_id, label=label)
        session.add(f)
    session.commit()
    print("  ✓ Favorites")

    # ── Targets Intel ──────────────────────────────────
    print("\n📊 Creating targets intelligence…")
    intel_data = [
        (0, 92, 88, 65, 45, 85, 82),
        (1, 88, 85, 55, 55, 78, 90),
        (2, 90, 82, 50, 40, 82, 88),
        (3, 85, 78, 60, 50, 75, 80),
        (4, 78, 72, 70, 60, 70, 72),
        (5, 75, 70, 65, 55, 65, 68),
    ]
    intel_count = 0
    for ti, (_, rs, opp, comp, noise, atk, evid) in enumerate(intel_data):
        from cores.targets.models import TargetIntel
        ti_obj = TargetIntel(
            id=target_map[ti].id,
            name=TARGETS[ti]["name"],
            domain=TARGETS[ti]["domain"],
            quality_score=rs,
            complexity_score=comp,
            roi_score=rs,
            noise_score=noise,
            freshness_score=round(90 - ti * 8 + hash(str(ti)) % 10, 1),
            competition_score=round(comp / 100, 2),
            opportunity_score=round(opp / 100, 1),
            reward_score=float(rs),
            reward_confidence=0.85,
            attack_surface_score=float(atk),
            evidence_potential_score=float(evid),
            api_density=len(TARGETS[ti]["endpoints"]),
            graphql_detected=any("graphql" in e[1] for e in TARGETS[ti]["endpoints"]),
            multi_tenant=ti < 3,
            technology_tags="ruby, rails, react, graphql, postgres",
            created_at=_ts(days=90),
        )
        session.add(ti_obj)
        intel_count += 1
    session.commit()
    print(f"  ✓ {intel_count} target intel records")

    # ── Final summary ──────────────────────────────────
    print("\n" + "═" * 50)
    print("✅ SEED COMPLETO")
    print("═" * 50)
    print(f"  👤  Usuario:    admin@orion.io / orion2024")
    print(f"  🎯  Targets:    {len(TARGETS)}")
    print(f"  🔗  Endpoints:  {sum(len(t['endpoints']) for t in TARGETS)}")
    print(f"  🐛  Findings:   {sum(len(t['findings']) for t in TARGETS)}")
    print(f"  ⚖️   Verdicts:   {verdict_count}")
    print(f"  📄  Reports:    {report_count}")
    print(f"  💰  Total paid: ${sum(r['reward'] for r in REPORTS):,.0f}")
    print(f"  💵  Pending:    ${sum(r['est'] for r in REPORTS if r['status'] in ('submitted','draft')):,.0f}")
    print(f"  🔔  Notifications: {n_count}")
    print(f"  🔄  Pipeline runs: {pipeline_count}")
    print(f"  🔍  Investigations: {inv_count}")
    print(f"  📋  Tasks:         {len(tasks_data)}")
    print("═" * 50)

    # VACUUM to shrink DB
    print("\n🗜️  Running VACUUM (this may take a moment)…")
    session.execute(text("VACUUM"))
    print("  ✓ DB vacuumed")

    session.close()


def random_len(max_n: int) -> int:
    """Deterministic pseudo-length based on position."""
    return min(max_n, 6)


if __name__ == "__main__":
    main()
