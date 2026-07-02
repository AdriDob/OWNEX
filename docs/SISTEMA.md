# CATEYE — Documentación del Sistema

## Arquitectura General

CATEYE es un sistema de inteligência para bug bounty compuesto por tres capas principales:

- **Frontend**: Vue 3 + TypeScript + Vite + Tailwind CSS v4 + Pinia
- **API**: FastAPI con 57+ routers
- **Cores**: 48 módulos de lógica de dominio

## Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Frontend | Vue 3, TypeScript, Vite, Tailwind v4, Pinia |
| Backend | Python 3.12+, FastAPI 0.115+ |
| Base de datos | SQLAlchemy + SQLite/PostgreSQL |
| IA | Ollama (local), OpenRouter, OpenAI, Gemini |
| Escritorio | PyWebView + PyInstaller |
| Cifrado | AES-256-GCM, Fernet (PBKDF2-HMAC-SHA256) |

## Puerto de inicio

```
Frontend: http://localhost:5173
API:      http://localhost:8000
Docs API: http://localhost:8000/docs
```

## Variables de Entorno

| Variable | Default | Descripción |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Host del servicio Ollama |
| `OLLAMA_MODEL` | `qwen3:14b` | Modelo por defecto |
| `DATABASE_URL` | `sqlite:///data/cateye.db` | Conexión a base de datos |
| `CATEYE_AUTH_TOKEN` | — | Token de sesión (generado automáticamente) |

## Screenshots

Ver [docs/screenshots/README.md](screenshots/README.md) para la galería completa de capturas del sistema.
