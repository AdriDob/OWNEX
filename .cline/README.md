# Cline — Mejor Agente Alternativo a OpenCode

Cline es el **agente de respaldo** para cuando OpenCode agote tokens. Está configurado con el mejor modelo gratis posible para seguir el proyecto sin poner un centavo.

## Perfiles disponibles

| Perfil | Proveedor | Modelo | Costo | Límites | Rating |
|---|---|---|---|---|---|
| `github` | GitHub Models | **GPT-4o** | $0 | 10 RPM, 50 RPD | ⭐ Mejor calidad |
| `google` | Google AI Studio | **Gemini 2.5 Flash** | $0 | 15 RPM, 500 RPD | ⭐ Más requests |
| `openrouter-free` | OpenRouter | Router automático (27+ models) | $0 | 20 RPM, 50 RPD | ⭐ Más variedad |
| `local` | Ollama | Qwen3 Coder 32B | $0 | Ilimitado (local) | ⭐ Sin internet |
| `emergency` | OpenRouter | Gemini 2.5 Flash | ~$0.30/M tok | Según crédito | Solo si seagotaron los gratis |

## Cómo activar

```bash
# Elegí el perfil que quieras:
.cline/scripts/switch-profile.sh github       # GPT-4o gratis (mejor calidad)
.cline/scripts/switch-profile.sh google        # Gemini 2.5 Flash (más requests)
.cline/scripts/switch-profile.sh openrouter-free # 27+ modelos gratis
.cline/scripts/switch-profile.sh local         # Offline
```

Después de ejecutar el script, **abrí Cline → ⚙️ → pegá tu API Key** en el campo correspondiente.

## API Keys gratis (sin tarjeta de crédito)

### GitHub Models (recomendado)
1. Ve a https://github.com/settings/tokens
2. Creá un token clásico con scope `read:user`
3. En Cline → ⚙️ → pegá el token en **OpenAI API Key** (aunque sea GitHub)
4. Modelo: `gpt-4o` — el mejor modelo de código gratis disponible

### Google AI Studio
1. Ve a https://aistudio.google.com/apikey
2. Creá una API Key (no pide tarjeta)
3. En Cline → ⚙️ → pegala en **Google Gemini API Key**
4. Modelo: `gemini-2.5-flash` — 500 requests/día, 1M contexto

### OpenRouter
1. Ve a https://openrouter.ai/keys
2. Creá una API Key (no pide tarjeta)
3. En Cline → ⚙️ → pegala en **OpenRouter API Key**
4. Modelo: `openrouter/free` — router automático

## Recomendación

```
┌──────────────────────────────────────────────────────────┐
│  🏆 GitHub Models → GPT-4o (mejor calidad, 50 req/día) │
│                                                          │
│  ¿Se acabaron las requests? → Google (500 req/día)       │
│  ¿No hay internet? → Ollama local                        │
│  ¿Todo lo gratis falló? → Emergency (pago mínimo)         │
└──────────────────────────────────────────────────────────┘
```

## Estructura

```
.cline/
├── README.md                          ← Esta documentación
├── rules/
│   ├── core.md                        ← Reglas de desarrollo + Abejita
│   └── context.md                     ← Contexto del proyecto
└── scripts/
    └── switch-profile.sh              ← Switch entre perfiles
```

## Reglas de desarrollo

Cline carga automáticamente todos los archivos `.md` dentro de `.cline/rules/`. Las reglas incluyen la sección **La Abejita** que le indica a Cline monitorear activamente el sistema como un panal de abejas.
