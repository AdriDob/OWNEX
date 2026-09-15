# SETUP BLOCKERS — Checklist de las 3 acciones que bloquean todo el ingreso

> **SSOT de lo que falta para que OWNEX cobre.** Nada de código resuelve estas 3 — son cuentas tuyas + tokens. El resto del sistema está listo y verde (69 jobs, trabajando).
> Orden = impacto. Cada item tiene el "Done cuando" verificable.

---

## 🔒 BLOQUEADOR 1 — GITHUB_TOKEN (desbloquea $2,700 Algora + todo dev bounty)

**Qué falta**: `github_token` vacío en vault (`cores/credentials/vault.py:30` — lee `GITHUB_TOKEN`).

**Por qué bloquea**: `AlgoraExecutor` (`algora_executor.py:385`) usa el token para claim → clone → commit → PR. Sin token, no hay claim, no hay PR, no hay merge, no hay payout. También bloquea GitHub Bounty Search, Opire/IssueHunt con auth, y el CoderAgent que genera PRs.

**Pasos (copy-paste, ~3 min):**
1. Crear token: https://github.com/settings/tokens → **Generate new token (classic)**
   - Scope mínimo: `repo` (read+write commits/PRs) — para claim+branch+PR
   - Expiración: 90 días (rotación, ver DECISIONS "auto-rotación 90d")
2. Exportar en el entorno del backend (persistir en `~/.bashrc`):
   ```bash
   export GITHUB_TOKEN="ghp_XXXXXXXX"
   ```
3. (Alternativa) Meterlo en IdentityVault vía API:
   ```bash
   curl -X POST http://localhost:8000/api/credentials/github \
     -H "Authorization: Bearer <token>" \
     -d '{"token": "ghp_XXXXXXXX"}'
   ```

**✅ Done cuando** (verificable):
```bash
.venv/bin/python -c "from cores.credentials.vault import get_credentials; print('SET' if get_credentials(force_refresh=True).github_token else 'MISSING')"
# → SET
```

**Impacto desbloqueado**: claim real en `algora_rudderstack_go` ($2,000) + `algora_appflowy_flutter` ($500) + `algora_trigger_dev` ($200) — paquetes YA preparados en `~/ownex/submissions/algora/`. PR → merge → payout.

---

## 🧠 BLOQUEADOR 2 — Assessments Mercor + Outlier + Alignerr (desbloquea canal $15-55/h recurrente)

**Qué falta**: cuentas creadas + assessment aprobado en las 3 plataformas (no hay API pública de trabajo sin assessment — es el mecanismo de entrada).

**Por qué es el mejor canal post-Algora**: paga por HORA desde día 1 aprobado, sin merge ni espera de PR. $20-55/h Mercor, $15-30/h Outlier/Alignerr. Recurrente.

**Pasos (3-6 hs total, en paralelo):**

| Plataforma | URL | Assessment (2-3h cada uno) | Paga |
|---|---|---|---|
| **Mercor** | work.mercor.com | Coding/reasoning (el más largo) | $20-55/h, expert $80-250/h |
| **Outlier** | outlier.ai | Rating/ranking/writing | $15-30/h |
| **Alignerr** | alignerr.com | Especialidad (coding/math) | $15-30/h |

Tips (del `MASTER_DAILY_EXECUTION_PLAN`):
- Mis cosas en inglés, perfil técnico real (Python, Go, Unity, TS, APIs, automation)
- No dejar a medias: 1 assessment fallido bloquea esa plataforma 30-90 días
- Si falla 1, reforzar las otras 2 — no reintentar inmediato

**✅ Done cuando**: 3/3 assessments submitted (el email de cada plataforma lo confirma; OWNEX no puede auto-verificar esto — es externo).

---

## 💸 BLOQUEADOR 3 — Rails de pago reales (desbloquea COBRAR, no solo trabajar)

**Qué falta**: solo `mercadopago` configurado (`~/.config/ownex/payment_network.json`). El ledger exige rail real para marcar PAID (Rule §39: P(CASH) real = rail configurado).

**Por qué bloquea**: un payout de Algora viaja por Stripe Express → cuenta bancaria/Payoneer/Wise. Si tu rail no está configurado, `P(CASH)` = UNKNOWN y el score de oportunidad dice "sin rail configurado no es cobrable". El dinero no aparece en Income Home.

**Rails prioritarios para AR (elegí los que tengas, mínimo 3):**

| Rail | Para qué | ID en el catálogo |
|---|---|---|
| **GrabrFi** | Cuenta US que recibe Stripe/ACH para LatAm | `grabrfi` |
| **Wise** | Transferencias internacionales → ARS barato | `wise` |
| **Airtm** | Retiro USD virtual, P2P, cripto | `airtm` |
| **Payoneer** | Fiverr/plataformas lo usan directo | `payoneer` |
| **MercadoPago** | Ya configurado (local ARS) | `mercadopago` |

**Pasos:**
```bash
curl -X POST http://localhost:8000/api/payment-compat/configured \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"account_ids": ["grabrfi","wise","airtm","mercadopago"]}'
```
O en UI: Income Home → `/operations/payment-compat` → marcar las que tenés.

**✅ Done cuando**:
```bash
.venv/bin/python -c "from cores.payment_compat.engine import get_payment_engine; print(get_payment_engine().get_configured_accounts())"
# → ≥ 3 cuentas
```

---

## ⚡ Flujo completo luego de los 3 bloqueadores

```
GITHUB_TOKEN ──→ AlgoraExecutor claim 3 bounties ($2,700)
                        │
                        ├─→ CoderAgent clona→analiza→genera fix→tests→PR
                        │                                   │
                        └─────────────── PR → HUMAN APPROVE → merge
                                                                  │
Rails ─────────────────→ Stripe Express → GrabrFi/Wise → PAID en ledger
                                                                  │
Assessments ──→ Mercor/Outlier/Alignerr → $15-55/h recurrente ──→ channel_economy MEASURED
```

---

## Tabla resumen

| # | Bloqueador | Tiempo | Desbloquea | Done cuando |
|---|---|---|---|---|
| 1 | GITHUB_TOKEN | 3 min | $2,700 Algora + todo dev bounty | `github_token` = SET |
| 2 | Assessments ×3 | 3-6 hs | Canal $15-55/h recurrente | 3/3 submitted |
| 3 | Rails ≥3 | 15 min | Cobrar (ledger PAID real) | `configured_accounts` ≥ 3 |

**Regla**: nada de esto se inventa — cada "Done cuando" es verificable por comando o email de la plataforma. Hasta que no estén los 3, `P(CASH)` se queda en UNKNOWN y el ledger en $0 honesto.