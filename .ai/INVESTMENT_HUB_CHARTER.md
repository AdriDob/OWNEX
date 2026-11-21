# INVESTMENT HUB CHARTER — Pilar central permanente de OWNEX

- **Estatus**: VIGENTE (no reducible, no posponible indefinidamente)
- **Fecha**: 2026-11-20
- **Autoridad**: confirmación explícita del usuario
- **Ámbito**: inversiones, trading, inteligencia financiera, gestión patrimonial

> OWNEX conserva **dos motores económicos**, no uno:
> 1. **Development & Earn** — encontrar, ejecutar y cobrar oportunidades de trabajo.
> 2. **Investment & Wealth Management** — administrar, analizar, proteger y hacer crecer el patrimonio.
>
> Ninguno se subordina al otro. El Investment Hub no es un gráfico de criptomonedas ni un
> módulo secundario detrás de Development & Earn.

---

## 1. Alcance permanente

| Pilar | Responsabilidad |
|---|---|
| Wealth Management | Patrimonio y posiciones consolidadas |
| AI Investment Intelligence | Análisis, investigación, estrategias |
| Market Monitoring | Seguimiento y alertas automáticas |
| Trading & Automation | Bots, señales, ejecución controlada |
| Research & Analytics | Indicadores, modelos, backtesting |
| Risk Management | Exposición, límites, protección |

## 2. Conectores exigidos (arquitectura extensible, no un solo broker)

Binance · IOL InvertirOnline (API REST/WS + MCP oficial) · Interactive Brokers · TradingView ·
MetaTrader 5 · Coinbase · Kraken · Bybit · CCXT · Freqtrade · NautilusTrader · OpenBB.

Cada conector debe exponer: capability matrix, autenticación, permisos, sincronización,
health check, límites, errores y evidencia de funcionamiento. Prioridad: APIs oficiales,
OAuth, WebSocket, MCP y SDKs oficiales; importación CSV como fallback autorizado.

## 3. Agentes especializados requeridos

Market Intelligence · Portfolio Analyst · Fundamental Analyst · Technical Analyst ·
Macro Analyst · Crypto Analyst · Risk Manager · Strategy Researcher · Trading Agent ·
Performance Analyst.

Toda recomendación incluye evidencia, hipótesis, riesgos, horizonte temporal,
incertidumbre y fecha de los datos usados.

## 4. Escalera de autonomía (por conexión, no global)

`DISCONNECTED → READ_ONLY → MONITORING → PAPER_TRADING → PRE_TRADE_VALIDATION →
CONFIRMATION_REQUIRED → LIVE_TRADING_AUTHORIZED`

Implementada en `cores/connections/permissions.py` con estas garantías:

- **Deny-by-default**: un provider sin registro está `DISCONNECTED`.
- **Escalado contiguo**: no se puede saltar un peldaño (rechazo auditable).
- **Ack humano obligatorio** para entrar en `LIVE_TRADING_AUTHORIZED`.
- **Revocación siempre permitida** (kill switch por conexión) y registrada.
- **`FUNDS_TRANSFER` / `WITHDRAW` no existen en ningún modo**: OWNEX nunca mueve dinero.
- **Lectura ≠ operación**: `LIVE_ORDER` solo lo otorga el modo más alto.
- Permisos independientes por plataforma; el audit es append-only JSONL sin secretos.

API: `GET /api/connection-manager/permissions`, `/permissions/matrix`,
`/permissions/audit`, `GET|POST /accounts/{provider}/permissions`,
`POST /accounts/{provider}/permissions/revoke`.

Gate de órdenes reales: `api/routers/investment.py::_order_gate(provider)` exige
`LIVE_ORDER` además del pause global del manager.

## 5. Criterio de finalización (reglas de honestidad)

- El hub debe arrancar **sin credenciales externas**, con datos públicos y datos de
  prueba claramente identificados.
- Nunca declarar un broker conectado sin autenticación efectiva.
- Nunca declarar operaciones reales, beneficios ni saldos sin evidencia.
- Un backtest con comisiones, slippage y drawdown no es una máquina de imprimir dinero.

## 6. Estado verificado del repositorio (2026-11-20)

| Sección | Estado | Dónde |
|---|---|---|
| Catálogo de conexiones AR/fintech (IOL, PPI, Binance, Cocos, Ualá, Ripio, Balanz, IEB, Lemon, Buenbit, Belvo…) | IMPLEMENTADO | `cores/connections/catalog.py` |
| Clientes reales IOL / PPI / Binance (solo lectura) | IMPLEMENTADO (sin creds verificadas) | `cores/brokers/` |
| Snapshots, historial de sync, importación CSV/JSON/XLSX | IMPLEMENTADO | `cores/connections/{snapshots,sync_history,importer}.py` |
| Normalización + portfolio consolidado multi-provider | IMPLEMENTADO | `cores/connections/financial_normalizer.py`, `portfolio_view.py` |
| Consent + audit para agentes MCP externos | IMPLEMENTADO | `cores/connections/mcp_consent.py` |
| **Permisos / autonomía por conexión** | **IMPLEMENTADO en esta sesión** | `cores/connections/permissions.py` |
| Gate de órdenes reales por conexión | **IMPLEMENTADO en esta sesión** | `api/routers/investment.py::_order_gate` |
| Adapters de inversión (ccxt, alpaca, ibkr, polymarket, defi, freqtrade, hummingbot, quant_research…) | IMPLEMENTADO | `core/investment/adapters/` |
| Risk guardian + allocation + métricas | IMPLEMENTADO | `core/investment/{risk_guardian,smart_allocator,metrics}.py` |
| Settlements/trades reales con cuentas propias | NO VERIFICADO | requiere credenciales del usuario |
| Agentes analistas (10 roles) como scheduler continuo | PARCIAL | capacidades existen; orquestación continua pendiente |
| Coinbase / Kraken / Bybit | IMPLEMENTADO (público verificado live; sync con keys sin probar) | `cores/brokers/cex_client.py`, catálogo `INVESTMENT_GLOBAL` |
| NautilusTrader / OpenBB / TradingView / MT5 | PENDIENTE | requieren adapter nuevo |
| UI de modos de permiso por conexión | IMPLEMENTADO | `frontend/src/components/connection/PermissionModePanel.vue` (tab "Permisos" en InvestmentHub) |

Regla de integración: lo que figure como IMPLEMENTADO tiene código y tests;
lo PENDIENTE no se declara operativo en UI ni en reportes.
