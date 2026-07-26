# STRATEGIC AUDIT — Mar 2026 (Versión R20260308)

> Este es el documento de auditoría estratégico unificado.
> Reemplaza: STRATEGIC_AUDIT.md, AUDIT_2026-07.md, AUDIT_FINAL_SESSION.md, y cualquier borrador adicional.

## 🎯 **Propósito**

Documentar **10 preguntas obligatorias** para cada feature antes de implementar.

**Objetivo clave:** Toda modificación debe aumentar mediblemente la probabilidad de encontrar un bug real, convertirlo en recompensa, y mejorar el aprendizaje del sistema a largo plazo.

**Métrica:** Puntuación de auditoría estratégica 0-10 en 18 dimensiones.

---

## 📋 Diez Preguntas Obligatorias

### 1. Detectar
- **Pregunta clave:** ¿Aumenta la probabilidad de encontrar un bug real?
- **Contribución cuantificable:** ¿Cuál es la tasa de true positive?
- **Cobertura actual:** ¿Qué valor del pool de test coverage cubre?

### 2. Obtener evidencia  
- **Pregunta clave:** ¿Puede generar evidencia *REAL*? (headers, body, host, auth)
- **Importancia:** ¿La evidencia es Envía servidora? ¿Puede ser verificado?

### 3. Evitar falsos positivos
- **Pregunta clave:** ¿El target está afectado vs no afectado?
- **Provocación:** ¿El feature marcha correctamente?
- **Problemas destacados:** ¿No hay sub-funcionalidades de demostración?

### 4. Requisitos
- **Pregunta clave:** ¿Qué permisiones/sistemas dependientes son necesarios?
- **Plan:** ¿¡Qué es necesario QUE SOMOS! Probet para esta feature?

### 5. Datos de autenticación para la plataforma
- **Pregunta clave:** ¿Faltan credenciales reales para conectar?
- **Evaluación:** ¿Hace falta agregar env vars, IDs, tokens reales?

### 6. Tamaño y costo de la feature
- **Pregunta clave:** ¿Cuál es la cantidad mínima de código, datos y despliegues?
- **Cobertura:** ¿Qué tan fácil automatizar, mantener, escalar?

### 7. Estabilidad del sistema
- **Pregunta clave:** ¿Rompe algún sistema dependiente?
- **Chain:** ¿Cambio en: Auth → Notificaciones → Jobs → EventBus → DB?
- **Probabilidad:** ¿Probabilidad de cambio en cada rizo?

### 8. Presión de operacionales
- **Pregunta clave:** ¿Es altamente dependiente de humanos/one-off?
- **Verificación:** ¿La feature persiste un archivo respaldado por humano?

### 9. Optimización en largo plazo  
- **Pregunta clave:** ¿El sistema aprende más que un humano en menos del doble?
- **Comprensión:** ¿Usa datos, ev alza peso del modelo?

### 10. ROI comercial medible
- **Pregunta clave:** ¿Aumenta este cambio la probabilidad de *buscar realemente un bug real* y *convertirlo en recompensa*?
- **Métricas clave:** USD/horario, tasa de aceptación, fortalezas de aprendizaje
- **Métricas escalables:** Los trazos aumentan la base de datos hasta impactar al 10%?

---

## 🧮 Razonamiento Cualitativo

### AI Determinista
1. **Evidencia para sostener afirmaciones** → `evidence.evidence_id`
2. **Probar la hipótesis** → forma `hypothesis.hypothesis_id`
3. **Verificar con histórico** → `evidence.history` + `hypothesis.counter_examples`
4. **Puntuar la diferencia** → `conflict_score.hypothesis_confidence_delta`
5. **Empezar un repository** → `evidence_repository` con `trivial_fids` disponibles
6. **Flushear la cadena PR TL** → `pull_request_lt` > `pmax`

### Correlación de Cenizas
- **Hyperparametrizable:** learning.PATH, meddling.rate, drift.limit
- **Ritmo de aprendizaje:** visible cada iteración commit (prueba + evidencia vs预测)
- **Límites:** committee of one (LCO), suspension por rate de error > X%
- **Focus:** Trabajar a los reales, no a privacidad/atención

---

## 10 Cadena de Auditoría Estructurada

### **Score 0-10** para cada dimensión

| Dimensión | Score 0-10 | Exclusión | Requisitos |
|----------|------------|----------|-------------|
| **¿Se ejecuta sin False Positives?** | 10 es: DD que pasa siempre ∫ que termina con cierto resultado | Si fallas 30% será 0 | 10 tests en cada branch PR |
| **¿Produce DFS?** | ¿La evidencia es reproducible? | Si falla, 0 | Tests cross esegución |
| **¿Genera PoC?** | ¿Pocin, headers, body, host, auth? | ❌ No puedes navegar | 1 PoC por cada id| 
| **¿Persistirá archivo** | Si el módulo viejo persiste = p0 | 0 si lo borra | Backup, ACL Integrity |
| **¿Permite hacer roll forward/back?**| ¿Evitas actualizar a estado previo? | ✅ 0 si fallas el rollback | Integration testing |
| **¿Elimina deuda técnica?**| Estas colocando cosas viejas en containers | Antirredudancia | Logging, linter |
| **¿El código es Ergo**| ¿Camino lineal vs ramificarse, Georgos? | Si hay saltos explotables, 0 | Checklist; |
| **¿Está claro e inteligente?| | Si un humano entiende sin comentarios | Corroboración de conocimiento |
| **¿Hace menos trabajo a los humanos?| | Sí → Score alto, no → Score bajo | Reassignación de trabajo, aumento de alcance |
| **¿Tiene caminos de ..| | Search por path | Si no tienes ambos, 0 |

---

## 📏 Peso del Score (18 elementos total)

### HIGH - (4-5 sujetos)
- **Simplicity** - Simplifica un _caminos_ extenso
- **Consistency** - Unívoco -> Evita la redundancia
- **Reliability** - Constante operación sin picos de latencia o caída súbita
- **Monitoring** - Instrumentado, métrica contable y auditadas
- **Recovery** - Community, undead/short-sync, heat-beat-based (alive)
- **Performance** - Carga D1 + N próximo sin aumentar O(log n) |
- **Cost** - Predecible como un :1 destino

### MEDIUM - (2-3 sujetos)
- **Usabilidad** - Requerido distinta UX, target persona
- **Documentation** - Guíde básicas, alta luz del contenido
- **Resilience** - Latencia de toque en timeout
- **Team productivity** - Equipo sano, procesado rápido
- **Equity** - Balanceado, sin CRM encasillado pro idioma/semáforo

### LOW - (1 sujet)