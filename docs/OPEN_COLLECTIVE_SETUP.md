# Open Collective / Polar.sh — Setup para Argentina

> OWNEX usa open-core: base gratis + features premium para sponsors.
> Este doc configura las plataformas de pago accesibles desde Argentina.

## Opción 1: Open Collective (recomendada)

**URL**: https://opencollective.com/ownex

```text
1. Crear cuenta en opencollective.com
2. "Create a Collective" → nombre: OWNEX
3. Verificar identidad (DNI + CUIT/monotributo)
4. Conectar cuenta bancaria argentina (transferencia)
5. Configurar tiers:
   - Supporter: $15/mes
   - Professional: $49/mes  
   - Enterprise: $149/mes
6. Open Collective maneja facturación e impuestos automáticamente
7. Payouts mensuales a tu banco AR
```

**Ventaja**: acepta Argentina como fiscal host, sin necesidad de entidad US/EU.
**Comisión**: 10% (5% plataforma + 5% fiscal host).

---

## Opción 2: Polar.sh (moderna, menor comisión)

**URL**: https://polar.sh/adridob

```text
1. Crear cuenta con GitHub OAuth
2. Conectar repo AdriDob/OWNEX
3. Configurar benefits:
   - Tier Supporter → acceso Discord premium
   - Tier Professional → license key automática
   - Tier Enterprise → consultoría mensual
4. Polar genera license keys automáticamente via API
5. Payouts: PayPal o transferencia internacional

Comisión: 4% + procesamiento de pago (~2.9%)
Total: ~7% (menor que Open Collective)
```

**Nota**: Polar requiere cuenta bancaria compatible con Wise/Payoneer para payouts fuera de US/EU.

---

## Integración con el sistema

El endpoint `/api/premium/status` lee `core/premium/gates.py` y devuelve:

```json
{
  "tier": "supporter",
  "available_features": ["discovery", "scanner", "..."],
  "locked_features": ["polymarket", "job_search"],
  "sponsor_url": "https://opencollective.com/ownex",
}
```

El frontend AiCenter muestra esto en la card de estado.

---

## Activar sponsors

```bash
# 1. Crear perfil en Open Collective o Polar.sh
# 2. Configurar tiers según este documento
# 3. Agregar links al README:
#    <a href="https://opencollective.com/ownex">Become a Sponsor</a>
# 4. Configurar webhook para generar license keys automáticas
# 5. Documentar cómo los sponsors configuran su key localmente
```
