# OWNEX — Acciones humanas pendientes

> **Estado del proyecto:** TECHNICALLY COMPLETE / HUMAN ACTIONS PENDING
> Todo lo que puede hacerse localmente está hecho y probado (suite: 5800 passed,
> backend health OK, frontend build OK). Esta es la lista única de todo lo que
> requiere tu intervención personal: credenciales, consentimientos, identidad
> o autorización legal.
>
> OWNEX **no está generando ingresos reales todavía** (USD 0 verificados).
> El primer cobro requiere completar las acciones de la Fase A.

---

## FASE A — Para el primer ciclo de ingresos (prioridad máxima)

### A1. make.fun — competencia "Sum up news" (HIT0, deadline más próximo)

| Campo | Detalle |
|---|---|
| Plataforma | make.fun |
| Motivo | Primera competencia con entregable ya construido y conforme a reglas |
| URL | https://make.fun/competitions |
| Paquete local | `~/projects/makefun-news-20261120/` (repo git, commit `0b2f7cc`) |
| Requisitos previos | Repo público en GitHub + cuenta make.fun + transcript bundle del agente constructor |
| Instrucciones | 1) `cd ~/projects/makefun-news-20261120 && git remote add origin <tu-repo-publico> && git push` 2) Crear cuenta/keypair Solana en make.fun (firma Ed25519, sin fee) 3) Generar transcript bundle con `node cli/makefun.mjs bundle` — **el harness que construyó la entrada debe exportar la sesión**; si Devin no es compatible, reconstruir en un cliente que grabe (skill.md sugiere Superbot gratis) 4) `POST /api/competitions/<slug>/submissions` con repo_url + commit_sha + bundle |
| Qué hace OWNEX después | Registra la entrega, sigue el estado de judging, y cuando haya pago USDC/Solana lo registra como evidencia de ingreso |
| Riesgo | Bajo: licencia MIT del entregable, pero los términos de make.fun exigen repo público + licencia amplia + transcripts públicos — **irreversible una vez publicado** |
| Permisos que solicita | Publicar código en repo público tuyo, firmar con keypair Solana tuyo, aceptar términos de la plataforma |
| Estado | **BLOCKED_ON_USER** — deadline `news-image-20261120` era 22-nov 00:00 UTC (probablemente vencido); apuntar a la próxima competencia "Sum up news" diaria |

### A2. Cuenta GitHub + verificación de plataformas de bounty

| Campo | Detalle |
|---|---|
| Plataforma | GitHub + Algora/Opire/IssueHunt/Gitcoin |
| Motivo | La mayoría de bounties OSS pagan vía PR mergeado en GitHub; sin cuenta no hay entregas |
| URL | https://github.com/signup |
| Instrucciones | 1) Crear/verificar cuenta GitHub 2) Configurar 2FA 3) En OWNEX → Integrations → conectar GitHub (PAT con `public_repo`) |
| Qué hace OWNEX después | Los fetchers de github_bounties/sponsors ya funcionan sin auth para descubrimiento; con PAT sube rate limits y habilita submissions |
| Riesgo | Bajo |
| Estado | **BLOCKED_ON_USER** |

### A3. Plataformas de evaluación IA (Alignerr, Mercor, DataAnnotation, Outlier)

| Campo | Detalle |
|---|---|
| Plataforma | Alignerr (Labelbox), Mercor, DataAnnotation, Outlier.ai, Prolific |
| Motivo | Circuito de mayor probabilidad de primer pago: tareas pagas por hora sin entregable externo |
| URL | https://alignerr.com · https://mercor.com · https://www.dataannotation.tech · https://outlier.ai · https://www.prolific.com |
| Instrucciones | 1) Crear cuenta en cada una 2) Completar evaluaciones de ingreso (paid o free según plataforma) 3) Verificar método de pago disponible en Argentina (PayPal/Payoneer/crypto — **confirmar antes de invertir horas**) 4) Registrar credenciales en OWNEX → Connections |
| Qué hace OWNEX después | Los adapters de catálogo ya las listan; con credenciales el Connection Manager habilita sync de tareas disponibles |
| Riesgo | Medio: evaluaciones consumen tiempo; algunas no aceptan Argentina o pagan solo por horas aprobadas |
| Estado | **BLOCKED_ON_USER** |

### A4. Bugcrowd / HackerOne — programas de seguridad

| Campo | Detalle |
|---|---|
| Plataforma | Bugcrowd, HackerOne, Intigriti, YesWeHack |
| Motivo | 629+ programas detectados por los fetchers reales; pagos altos pero competencia alta |
| URL | https://bugcrowd.com · https://hackerone.com |
| Instrucciones | 1) Crear cuenta 2) Completar verificación de identidad que exija cada plataforma 3) Revisar elegibilidad Argentina por programa (muchos exigen residency específico) 4) Conectar en OWNEX |
| Riesgo | Medio-alto: verificación KYC, programas geo-restringidos, payouts lentos |
| Estado | **BLOCKED_ON_USER** |

---

## FASE B — Conexiones y credenciales técnicas

| # | Acción | Plataforma | Estado |
|---|---|---|---|
| B1 | API key make.fun (`x-api-key`) para rate limits >60/min y submissions | make.fun | BLOCKED_ON_USER |
| B2 | GitHub PAT (`public_repo` + `read:org` opcional) | GitHub | BLOCKED_ON_USER |
| B3 | Credenciales de plataformas en el vault de OWNEX (nunca en `.env` commiteado) | Todas | BLOCKED_ON_USER |
| B4 | Wallet Solana para recibir USDC de make.fun/crypto platforms | Solana | BLOCKED_ON_USER — **guardarla fuera del repo, jamás commitear seed phrase** |
| B5 | PayPal/Payoneer verificado como método de retiro | Pagos | BLOCKED_ON_USER |
| B6 | Autorizar registro de agente OWNEX en Taskmarket (Daydreams) — POST de registro ERC-8004, sin KYC, identidad onchain gratuita | Taskmarket | READY_FOR_AUTHORIZATION — OWNEX puede ejecutarlo con un POST; requiere tu wallet/base account |
| B7 | Autorizar registro de agente en Agent Hansa (`POST /api/agents/register` o `npx agent-hansa-mcp register`) — sin KYC, USDC Base | Agent Hansa | READY_FOR_AUTHORIZATION |
| B8 | Evaluar Clustly — API devolvió `DEPLOYMENT_DISABLED` el 2026-11-20; reintentar más adelante antes de registrar | Clustly | BLOCKED_ON_PLATFORM |
| B9 | Drips — requiere KYC + solicitud al maintainer por Wave; decidir si se completa verificación de identidad | Drips | BLOCKED_ON_USER |

---

## FASE C — Decisiones y autorizaciones

| # | Acción | Motivo | Estado |
|---|---|---|---|
| C1 | Autorizar publicación de repos públicos para competencias (make.fun, Gitcoin, grants OSS) | Los términos exigen código público + licencia amplia | BLOCKED_ON_USER |
| C2 | Aprobar envíos externos (PRs, submissions, propuestas) — OWNEX prepara, vos aprobás | Regla de aprobación humana | READY_FOR_AUTHORIZATION |
| C3 | Decidir si `ownex_weather/` se integra a OWNEX o queda como proyecto separado | Subproyecto completo sin integrar | BLOCKED_ON_USER |
| C4 | Revisar gitlinks de `cognee` y `work/ownex-economy-active-earn` (punteros movidos sin commit) | Submódulos con cambios pendientes | BLOCKED_ON_USER |
| C5 | Política de backup/VACUUM para `database/catseye.db` (13GB, es la DB dev activa) | Recuperar espacio sin riesgo | READY_FOR_AUTHORIZATION |
| C6 | Elegir si OWNEX se usa en modo dev (`database/catseye.db`) o desktop (`~/.ownex/database/cateye.db`) — hay dos nombres de DB | Unificar entrypoint | BLOCKED_ON_USER |

---

## Lo que YA está listo (no requiere acción tuya)

- Pipeline de oportunidades: 706+ items reales escaneados (HackerOne 215, Bugcrowd 297, Intigriti 67, YesWeHack 50, Superteam 12, GitHub 40, make.fun 13)
- Fetchers vivos verificados contra APIs públicas reales
- Eligibility engine con semántica UNKNOWN honesta
- Ranking con factor de saturación (submission_count real)
- Execution Studio: workspaces aislados, tests, review
- Revenue ledger: separa announced/expected/approved/pending/paid/withdrawn
- Backend: 1366 rutas, health OK · Frontend: build OK · Suite: 5800 tests verdes
- Entregable HIT0 make.fun construido y conforme a reglas
- Catálogo de fuentes: +6 agregadas 2026-11-20 (Google OSS VRP, Drips, Stacker News, Clustly, Agent Hansa, Daydreams TaskMarket); 5/6 activas en catálogo (Stacker News quedó fuera del cap de 1000 por prioridad); nueva familia `agent_native_markets`; AgentPact descartado (archivado 2026-11-16, API apagada); microtask marketplaces excluidos por decisión del owner
- Adapters read-only LIVE (2026-11-20): `TaskmarketAdapter` y `AgentHansaAdapter` en `core/opportunity/adapters/agent_markets.py` — discovery público verificado (Taskmarket: 6 tasks open de 20 listados; AgentHansa: 1 open). Solo fetch; claim/register/submit/wallet siguen BLOCKED_ON_USER (B6/B7).

## Regla permanente

> Nada de esta lista será ejecutado por OWNEX sin tu autorización expresa.
> El sistema prepara todo hasta el último paso seguro y espera.
> Ingreso verificado = USD 0.00 hasta que exista evidencia externa.

*Última actualización: 2026-11-20 — main `3c6130cb`+ (post-feeds/catalog commits)*