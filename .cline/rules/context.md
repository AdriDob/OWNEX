# Orion — Contexto del proyecto

## Resumen
Orion es un sistema autónomo de bug bounty intelligence. Automatiza el ciclo completo: descubrimiento de objetivos, análisis de superficie, reconocimiento, generación de hipótesis, validación, reporte, y envío a plataformas.

## Estado actual
- Versión: 1.6.0 (Stable)
- Backend: ~87% completo, 48+ módulos en `cores/`
- Frontend: ~90% migrado de React a Vue 3, ~40 páginas
- Tests backend: ~40% cobertura
- Tests frontend: ~0% cobertura
- Desktop: PyInstaller + NSIS installer

## Módulos clave
| Módulo | Propósito |
|---|---|
| `cores/agents/` | Sistema multi-agente (8 agentes: Coordinator, Research, Validator, Exploit, Documentation, Strategy, Memory, Financial) |
| `cores/ai/` | Proveedores de IA (Ollama, OpenAI, OpenRouter), orion_agent con tool-calling |
| `cores/recon/` | Herramientas de reconocimiento (subfinder, amass, httpx, nuclei, ffuf, katana, gau, etc.) |
| `cores/validation/` | Pipeline de validación y veredicto |
| `cores/reporting/` | Generación de reportes |
| `cores/orion/` | Orion Context Engine, Next Action, Opportunity Analyzer |
| `api/routers/` | 50+ routers REST |

## Arquitectura
- Monolito modular. Todo corre en un solo proceso.
- EventBus para comunicación interna.
- Watchdog con auto-recovery y auto-healing.
- Pipeline state machine para el ciclo de bug bounty.

## URLs importantes
- API: `http://localhost:8000`
- Frontend dev: `http://localhost:5173`
- Ollama: `http://localhost:11434`
