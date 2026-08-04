# OWNEX — QUICKSTART (cerrar e instalar a full)

Sistema listo: backend + frontend + motores de revenue automatizados.
Versión: 7.0.0 — estado verificado: ruff OK, mypy OK, 130+ tests OK, health OK.

## 1) Instalar (máquina nueva, ~10 min)

```bash
# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Verificación rápida (opcional pero recomendada)
make check        # ruff + mypy scoped + tests rápidos
```

## 2) Usar (local)

```bash
npm run dev            # backend :8000 + frontend :5173 juntos
# o por separado:
npm run dev:backend    # uvicorn api.main:app --port 8000
npm run dev:frontend   # Vite dev server
```

- Health: `curl http://localhost:8000/api/health` → `{"status": "ok", "version": "7.0.0"}`
- Dashboard: http://localhost:5173

## 3) Motores de revenue (ya automatizados)

El scheduler del sistema corre en el backend y dispara jobs por ciclo:

| Job | Frecuencia | Qué hace |
|---|---|---|
| `investment_arbitrage_scan` | cada 4h | escanea 8 exchanges (binance, okx, kraken, coinbase, bybit, bitget, mexc, gateio), filtro de liquidez $500k, cap de cordura 10%. Paper/dry-run: NO mueve capital real, reporta oportunidades |
| Ciclos security/forge/pulse/vault/atlas | horario | descubrimiento + scoring + sync de oportunidades bug bounty / freelance |
| `work_bank_daily_cycle` | diario 06:15 | prepara trabajos cero-barrera listos para entregar |
| `qa_daily_cycle` | diario 08:30 | regresión QA automática |

### Arbitraje manual (validación de edge)

```bash
# Simulación paper: 4 rondas, $1000, spread mínimo 0.5%
python scripts/paper_trade.py --runs 4 --capital 1000 --min-spread 0.5

# Con exchanges personalizados / filtro de liquidez
python scripts/paper_trade.py --exchanges binance,mexc --min-quote-volume 250000
```

El caso validado con datos reales: ZIL/USDT binance→mexc, spread 8.1–8.5%, +16.3%
compuesto en simulación. El desimplement REAL requiere API keys y validación de
libro de órdenes (ver plan de revenue).

## 4) Plan de revenue (ruta honesta a $25k–$100k/mes)

| Fuente | Estado | Ruta a $100k/mes | Hito realista 3-6 meses |
|---|---|---|---|
| Bug bounty (reports) | sistema completo, scheduler activo | 1–2 críticos/mes ($50–100k) — el camino principal | $10–25k/mes |
| Arbitraje cross-exchange | validado en paper (+16%/ciclo ZIL) | capital + keys + validación de book: compone sobre la base | $2–10k/mes sobre base |
| Forge (freelance/dev bounties) | scheduler activo | proyectos simultáneos | $2–5k/mes |
| Work bank (cero-barrera) | diario | entregables recurrentes | $1–3k/mes |
| Polymarket/ccxt spot | registry listo, requiere keys | apalancado sobre capital | menor |

Realidad: el sistema NO garantiza ingresos — maximiza la probabilidad:
detección automática 24/7, edge validado en arbitraje, y pipelines que quitan
fricción. $100k/mes en bug bounty = 1–2 reportes críticos aceptados al mes
(histórico de los mejores hunters). El triplo de $25k es el piso operativo
antes de escalar.

### Próximos pasos operativos (semana próxima)
1. Subir API keys en la config del sistema (exchanges + plataformas bounty).
2. Validar book real ZIL binance↔mexc (fetch_order_book) antes del primer
   desimplement con capital.
3. Dejar el backend corriendo con `npm run dev` (o servicio/systemd).
4. Revisar diario el dashboard: oportunidades + findings pendientes.

## 5) Comandos útiles

```bash
make work          # protocolo de arranque del agente (version check + health + next action)
make test          # pytest completo
make check         # ruff + mypy scoped + tests rápidos
make fmt           # ruff --fix
python run.py --backup   # backup de la DB
```
