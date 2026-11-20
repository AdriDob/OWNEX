# OWNEX V12 - User Guide (FASE 0)

**Generated:** 2026-11-09T19:49:52.356561

## Quick Start
1. **Arrancar el backend:** `cd api && uvicorn main:app --reload`
2. **Arrancar el frontend:** `cd frontend && npm run dev`
3. **Acceder:** http://localhost:5173

## Navegación Principal
- **Dashboard** - Visión general del sistema
- **Work Bank** - Oportunidades descubiertas y gestionadas
- **Descubrimiento** - Fuentes y plataformas de empleo
- **Remote Job Matcher** - Búsqueda de empleos remotos
- **Inversiones** - Brokers argentinos (consulta solo)
- **Finanzas** - Revenue Ledger y pagos
- **Configuración** - Conexiones y ajustes

## Work Bank Operations
### Discover Opportunities
1. Ve a Work Bank → Discover
2. El sistema auto-descubre desde 16+ adapters
3. Filtrar por: Argentina, español, sin experiencia obligatoria
4. Revisar elegibilidad por oportunidad
5. Aprobar/rechazar en human gate

### Opportunity Eligibility
Cada oportunidad muestra:
- Países admitidos
- Compatibilidad Argentina (bandera)
- Experiencia requerida (o "ninguna obligatoria")
- Entrevistas necesarias
- Pruebas técnicas
- Inglés requerido (ninguno para puestos junior)
- Tipo de trabajo
- Modalidad (remoto/hibrido/presencial)
- Remuneración (moneda + importe)
- Método de pago
- Retiro en Argentina
- Costos y comisiones
- KYC requirements
- Evidencia y fecha de verificación

## Remote Job Matcher
### Búsqueda Prioritaria
- Argentina ✓
- Trabajo remoto ✓
- Español ✓
- Sin experiencia profesional obligatoria ✓
- Capacitación incluida ✓
- Ingreso fijo ✓
- Soporte técnico N1 ✓
- Help desk ✓
- QA trainee ✓
- Operaciones ✓
- Administración ✓
- Atención al cliente en español ✓
- Puestos tecnológicos para perfiles junior ✓

### Filtros NO aplicados (a menos que sea inglés oral avanzado)
- Inglés básico o lectura técnica: NO se excluye
- Fluidez conversacional en inglés: NO se excluye automáticamente
- Cámara o grabaciones: Mostrar claramente si requiere

### Resultados
- Mostrar clearly: entrevistas, pruebas, cámara o grabaciones requeridas
- No inventar vacantes, salarios, requisitos ni empleadores
- Ordenar por compatibilidad y score

## Financial Management
### Revenue Ledger Categories
- **Potencial** - Opportunities with expected value
- **Aprobado** - Human-gate approved
- **Pagado** - Money received (separado del potencial)

### Movement Tracking
Each movement has: importe, moneda, fecha, origen, destino, tipo, estado, comisiones, evidencia, verificación.

⚠️ No confundir potencial con ingresos reales.

## Investment Operations (Argentina Only)
### Consultation Mode (Safe)
- Balanz: consulta de datos de mercado
- IOL: estado de cartera y análisis
- BYMA: datos de mercado (solo lectura)
- Mercado Pago: historial de transactions

### Real Operations (Requires Explicit Authorization)
- No se ejecutan operaciones automáticas
- Cada compra/venta/transfer requiere confirmación humana
- Sistema registra pero no ejecuta sin tu approval

⚠️ No ejecutes compras, ventas, transferencias, swaps, bridges, depósitos ni retiros sin mi autorización explícita.

## Security Checklist
- ✅ No secrets en texto plano
- ✅ MFA para acciones financieras
- ✅ Principio de mínimo privilegio
- ✅ MCP servers: 9 herramientas read-only auditadas
- ✅ API rate limiting activo
- ✅ Sin operaciones reales sin confirmación humana

## Known Issues
- Human gate → paid conversion: 0% (tracking needs activation)
- Some adapters: still using fallback data (real API pending)
- Revenue dashboard: not yet built
- 2-3 new adapter expansions: pending decision

## Next Steps
1. Explorar Work Bank y oportunidades
2. Probar Remote Job Matcher con filtros Argentina/Español
3. Revisar configuración de conexiones
4. Monitorear métricas de conversión
