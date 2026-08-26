# OWNEX — GitHub Sponsors Commercial Strategy

> **Estado**: Plan documentado. No implementado.
> **Objetivo**: Convertir OWNEX en open-core con monetización via GitHub Sponsors.
> **Modelo**: Base gratis open-source + features premium para sponsors.

---

## Estructura Open-Core

### GRATIS (público en GitHub)

```text
├── Discovery Engine (139 fuentes + crawling)
├── WorkBank básico (preparación de trabajos)
├── Profile Kit (generador de textos por plataforma)
├── Daily Digest (agregador de decisiones)
├── ZeroBarrierScorer + Availability Intelligence
├── Scanner de vulnerabilidades básico (nuclei + ZAP)
├── Payment Compatibility Engine (76 cuentas AR)
└── Frontend completo (Vue 3 + Tailwind)
```

### SPONSOR ($15/mes — Tier Supporter)

```text
├── Todo lo gratis +
├── Auto-submit pipeline completo (findings élite → plataforma)
├── CoderAgent autopilot (dev bounties ≤ $200 auto-resueltos)
├── Income Target Engine (planes EV/hora personalizados)
├── Economic Engine (risk-adjusted EV/hour scoring)
├── Competition Intelligence + Freshness decay
├── Priority issues en GitHub
└── Badge Sponsor en perfil
```

### SPONSOR ($49/mes — Tier Professional)

```text
├── Todo lo anterior +
├── Polymarket strategies (sweeper, smart_money, BTC arb)
├── Copy trading infrastructure
├── Payment Pipeline canónico (13 estados)
├── Job Search Integration (fit evaluation 5D)
├── Market Evolution Engine (learning loop persistente)
├── Calibration system (predicho vs real)
├── Acceso a Discord/Telegram privado
└── Roadmap voting
```

### SPONSOR ($149/mes — Tier Enterprise)

```text
├── Todo lo anterior +
├── Multi-tenant (múltiples targets simultáneos)
├── API access sin rate limits
├── Custom adapters para plataformas privadas
├── White-label del frontend
├── Soporte prioritario 24h response
└── Consultoría mensual incluida (1h)
```

---

## Setup técnico

### 1. Activar GitHub Sponsors

```bash
# Ir a: https://github.com/sponsors/accounts
# Requerimientos:
#   - Cuenta GitHub verificada
#   - Ubicación configurada en perfil
#   - Bio completa
#   - Payout method (Stripe Connect o banco internacional)

# Argentina: Stripe Connect no disponible directamente.
# Alternativas:
#   - Open Collective (acepta Argentina)
#   - Ko-fi (payouts vía PayPal/Stripe)
#   - Polar.sh (alternativa moderna a GH Sponsors)
```

### 2. Separar código free vs premium

```text
Estrategia recomendada: Feature Flags (no forks separados)

Todo el código vive en el mismo repo.
Las features premium se activan con license key Ed25519.

cores/license/validator.py ya valida licencias.
Solo falta:

├── core/premium/
│   ├── __init__.py          # check_license() middleware
│   ├── decorators.py        # @requires_tier("professional")
│   └── gates.py             # PremiumGate.check_feature("polymarket")

Cada módulo premium verifica:
    from core.premium import requires_tier

    @requires_tier("supporter")      # $15/mes+
    def auto_submit_pipeline(...):
        ...

    @requires_tier("professional")   # $49/mes+
    class SweeperStrategy:
        ...
```

### 3. Sistema de licencias

```text
Usuario se vuelve sponsor en GitHub
    ↓
GitHub envía webhook a tu endpoint
    ↓
Generás license key Ed25519 firmada
    ↓
Usuario configura key en ~/.ownex/license.json
    ↓
OWNEX valida y desbloquea features premium
```

La infraestructura de licencias Ed25519 ya existe en `cores/license/validator.py`.

---

## README changes

Agregar sección después de Installation:

```markdown
## Sponsor OWNEX 💙

OWNEX es libre y siempre lo será. Pero las features avanzadas
requieren mantenimiento continuo.

| | Free | Supporter | Professional | Enterprise |
|---|---|---|---|---|
| Discovery Engine (139 fuentes) | ✅ | ✅ | ✅ | ✅ |
| Vulnerability Scanner | ✅ | ✅ | ✅ | ✅ |
| Auto-submit élite findings | ❌ | ✅ | ✅ | ✅ |
| CoderAgent autopilot | ❌ | ✅ | ✅ | ✅ |
| Income Target Engine | ❌ | ✅ | ✅ | ✅ |
| Polymarket strategies | ❌ | ❌ | ✅ | ✅ |
| Job Search Integration | ❌ | ❌ | ✅ | ✅ |
| Multi-tenant + API sin límites | ❌ | ❌ | ❌ | ✅ |

[Become a Sponsor →](https://github.com/sponsors/AdriDob)
```

---

## Proyección ingresos Sponsors

| Escenario | Sponsors × tier | Ingreso/mes |
|---|---|---|
| Pesimista | 10 × $15 | $150 |
| Conservador | 20 × $15 + 5 × $49 | $545 |
| Moderado | 50 × $15 + 15 × $49 + 3 × $149 | $2,172 |
| Optimista | 200 × $15 + 50 × $49 + 10 × $149 | $6,440 |
| ai-job-search nivel (35k stars) | ~500 paid de 100k users | $15,000+ |

**Referencia real**: ai-job-search tiene 35.3k stars y el creador dijo que le consiguió trabajo pero NO que genere ingresos directos por sponsors. El modelo funciona mejor cuando la herramienta ahorra tiempo medible.

---

## Checklist de implementación

```text
[ ] Activar GitHub Sponsors profile
[ ] Crear FUTURE_FEATURES.md documentando qué es sponsor-only
[ ] Implementar core/premium/ con feature flags Ed25519
[ ] Marcar módulos premium con @requires_tier decorator
[ ] Agregar sección Sponsor al README
[ ] Configurar payout (Open Collective para Argentina)
[ ] Webhook endpoint para generar license keys automáticamente
[ ] Documentar setup para sponsors (cómo configuran su key)
[ ] Video demo mostrando features free vs premium
[ ] Primer post técnico generando inbound
```

---

## Riesgo principal

```text
Si liberás el código open-source SIN separar premium correctamente,
alguien puede hacer fork y quitar los paywalls.

MITIGACIÓN:
- Las features premium más valiosas (CoderAgent autopilot,
  auto-submit, Polymarket) requieren API keys Y license key
- El valor real no está solo en el código sino en:
    • Los 139 fuentes curadas (mantenimiento continuo)
    • Las estrategias calibradas con datos reales
    • Las actualizaciones cuando plataformas cambian APIs
    • El soporte directo
- Modelo ai-job-search probado: MIT license pero los usuarios
  pagan por conveniencia, updates y soporte
```

---

*Este documento define la estrategia. La implementación técnica de feature flags Ed25519 está pendiente.*
