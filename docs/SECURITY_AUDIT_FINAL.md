# SECURITY AUDIT — FASE 1 (2026-09-14)

> Estado: **RC verificado en Linux/WSL, NO "Stable"** — Stable requiere validación física W1–W12.
> Alcance: §5 Brave/PC · §6 admin · §7 navegador · §30 seguridad · §32 degraded (Fase 1).
> No se tocó: `cores/events/*`, `cores/validation/*`, `cognee`, criptografía del vault.

## 1. Modelo de permisos

```text
NORMAL USER por defecto (cores/platform/elevated.py:elevation_status)
ELEVATED solo para install/update/service/repair/driver/windows_config
  (cores/platform/elevated.py:needs_elevation — resto responde False)
Toda elevación: reason/what/scope/duration/workspace + audit JSONL
  (OWNEX_DATA_DIR/elevation_audit.jsonl, best-effort, nunca raisea)
OWNEX jamás se ejecuta permanentemente como administrador.
```

## 2. Identity Vault

- AES-256-GCM (`cores/vault_crypto.py`, `cryptography.hazmat AESGCM), key `~/.orion/identity_vault.key` chmod 600. **Criptografía no tocada.**
- Scopes por workspace: entries `ws::provider`; lookup estricto (scoped jamás ve otro namespace ni legacy) — `cores/identity_vault.py:_lookup`.
- En disco: secretos cifrados, archivo 0600 (`tests/test_identity_vault_scopes.py` 7/7).
- Resolución: `resolve_credential(explícito → vault → "")`, jamás loguea ni raisea (`cores/automation/browser_agent.py`).

## 3. Human Gate

- Tokens HMAC-SHA256 `v2:expiry:nonce:workspace:sig`, TTL ≤600s, single-use, `compare_digest` (`cores/automation/safety.py`).
- El HMAC liga action+target+workspace: token de otro workspace/acción/target = deny.
- Formato v1 legacy rechazado (nunca grandfathered).
- Gate en 4 métodos browser consequential + PR/push + opencode execute; sweep del scheduler **nunca** self-aprueba (testeado).
- `tests/test_execution_safety.py` 16/16, `tests/test_cycle_task_handlers.py` 10/10.

## 4. Restricciones

- `BLOCKED_COMMAND_PATTERNS` (rm -rf /, mkfs, dd, fork-bomb, shutdown, curl|sh…), `redact_secrets()` (api keys/tokens/passwords/private keys), `is_path_allowed()` containment.
- Credenciales jamás en: logs, prompts IA (`redact_secrets` en code_generator), Git, screenshots.

## 5. Brave / navegador

- Detección (`cores/browsing/brave.py:detect_brave`), apertura controlada (`open_in_brave`, valida `http(s)`, endpoint 400 si no).
- State machine honesta (`browser_state()`): sin sesión viva solo NOT_DETECTED/DETECTED; READY+ exige evidencia.
- Reglas duras: sin extracción de passwords/cookies/tokens/sesiones/seed phrases; sin bypass CAPTCHA/MFA/KYC/anti-bot; automatización solo legítima+permitida (Playwright fallback).
- `tests/test_phase1_brave_elevated_health.py` 20/20.

## 6. PC Health

- `cores/health/system_health.py:collect_pc_health()` — CPU/RAM/DISK (psutil opcional), GPU (nvidia-smi best-effort), red (puerto 8000), data-dir, Brave, elevation. Nunca raisea, nunca expone secretos.
- Niveles HEALTHY/WARNING/DEGRADED/BLOCKED/CRITICAL + `health_level_text()` accionable.
- Endpoints: `GET /api/system/pc-health`, `/api/system/brave`, `POST /api/system/brave/open` (nunca 500).

## 7. Degraded

- OAR: unhealthy → fallback chain; AI-down → degradado, core operativo (`tests/test_llm_fault_injection.py` 8/8).
- Health global visible en toolbar (`AutonomyBadge` ← `/api/system/status`).

## 8. Límites conocidos (NO deuda escondida)

- Human Gate single-process (HMAC efímero; restart = re-aprobar). Suficiente desktop single-user.
- `cores/security/` no existe como paquete: la seguridad es transversal (safety + middleware + vaults), no un módulo.
- Playwright no instalado en CI/dev → paths browser testeados con mocks; E2E con navegador real = W11 físico.
- Legacy unscoped vault entries visibles solo para callers unscoped (migración = re-store con workspace).
- `test_credentials_vault.py::test_empty_by_default` falla si el entorno exporta keys reales (NVIDIA_API_KEY) — ambiental, preexistente, fuera de alcance.
