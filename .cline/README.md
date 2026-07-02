# Cline — Configuración para Orion

Este directorio contiene la configuración de Cline para el proyecto Orion.

## Estructura
```
.cline/
├── README.md           ← Esta documentación
├── rules/
│   ├── core.md         ← Reglas de desarrollo (código, stack, flujo)
│   ├── context.md      ← Contexto del proyecto (estado, módulos, URLs)
│   └── orion-rules.md  ← Reglas completas con referencia rápida
└── scripts/
    └── switch-profile.sh ← Script para cambiar entre perfiles local/cloud/emergency
```

## Perfiles disponibles
| Perfil | Proveedor | Modelo | Costo |
|---|---|---|---|
| Local | Ollama | `freehuntx/qwen3-coder:8b` | $0 |
| Cloud | OpenRouter | `google/gemini-2.0-flash-exp:free` | $0 |
| Emergency | OpenRouter | `google/gemini-2.5-flash` | ~$0.30/M tok |

## Quick switch
```bash
.cline/scripts/switch-profile.sh local
.cline/scripts/switch-profile.sh cloud
.cline/scripts/switch-profile.sh emergency
```

## Reglas
Cline carga automáticamente todos los archivos `.md` dentro de `.cline/rules/`. Las reglas actúan como system prompt: guían al agente sobre cómo comportarse, qué patrones seguir y qué evitar.

Ver `CLINE_SETUP.md` en la raíz del proyecto para la guía completa de configuración.
