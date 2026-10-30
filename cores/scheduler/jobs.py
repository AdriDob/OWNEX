"""Scheduler Job Definitions — All cycles (Forge, Pulse, Vault, Atlas).

Each cycle has staggered discovery jobs + a sync/scoring job.
"""

from __future__ import annotations

from cores.interfaces.scheduler import JobDefinition


def _discovery_job(
    job_id: str,
    app_id: str,
    handler: str,
    seconds: int,
    metadata: dict | None = None,
) -> JobDefinition:
    """Create a discovery job with interval trigger."""
    return JobDefinition(
        job_id=job_id,
        app_id=app_id,
        handler=handler,
        trigger="interval",
        seconds=seconds,
        metadata=metadata or {},
    )


def _cron_job(
    job_id: str,
    app_id: str,
    handler: str,
    cron: str,
    args: list | None = None,
    metadata: dict | None = None,
) -> JobDefinition:
    """Create a job with cron trigger."""
    return JobDefinition(
        job_id=job_id,
        app_id=app_id,
        handler=handler,
        trigger="cron",
        seconds=0,  # not used for cron
        cron=cron,
        args=args or [],
        metadata=metadata,
    )


def get_forge_jobs() -> list[JobDefinition]:
    """FORGE cycle jobs — run hourly for dev bounty platforms."""
    jobs = []

    # Open Source Funding platforms
    jobs.append(
        _discovery_job(
            job_id="forge_opencollective_discover",
            app_id="forge",
            handler="cores.opportunity.adapters.forge.opencollective:fetch_opportunities",
            seconds=3600,  # hourly
            metadata={"cycle": "forge", "platform": "opencollective"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="forge_opencollective_projects_discover",
            app_id="forge",
            handler="cores.opportunity.adapters.forge.opencollective_projects:fetch_opportunities",
            seconds=3600,
            metadata={"cycle": "forge", "platform": "opencollective_projects"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="forge_algora_discover",
            app_id="forge",
            handler="cores.opportunity.adapters.forge.algora:fetch_opportunities",
            seconds=3600,
            metadata={"cycle": "forge", "platform": "algora"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="forge_superteam_discover",
            app_id="forge",
            handler="cores.opportunity.adapters.forge.superteam:fetch_opportunities",
            seconds=3600,
            metadata={"cycle": "forge", "platform": "superteam"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="forge_github_sponsors_discover",
            app_id="forge",
            handler="cores.opportunity.adapters.forge.github_sponsors:fetch_opportunities",
            seconds=3600,
            metadata={"cycle": "forge", "platform": "github_sponsors"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="forge_freelancer_discover",
            app_id="forge",
            handler="cores.opportunity.adapters.forge.freelancer:fetch_opportunities",
            seconds=3600,
            metadata={"cycle": "forge", "platform": "freelancer"},
        )
    )

    # Issue Platforms (also in Forge)
    jobs.append(
        _discovery_job(
            job_id="forge_issuehunt_discover",
            app_id="forge",
            handler="cores.opportunity.adapters.forge.issuehunt:fetch_opportunities",
            seconds=3600,
            metadata={"cycle": "forge", "platform": "issuehunt"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="forge_opire_discover",
            app_id="forge",
            handler="cores.opportunity.adapters.forge.opire:fetch_opportunities",
            seconds=3600,
            metadata={"cycle": "forge", "platform": "opire"},
        )
    )

    # Sync job — runs after all discovery (hourly at minute 55)
    jobs.append(
        _cron_job(
            job_id="forge_sync_scores",
            app_id="forge",
            handler="cores.opportunity.tasks:sync_cycle_scores",
            cron="55 * * * *",
            args=["forge"],
            metadata={"cycle": "forge", "type": "sync"},
        )
    )

    # Internal dev agent — propose-only cycle for the repo's own queue (daily 04:30).
    # Read-only: picks oldest queued task, saves OpenCode proposal, parks for human approve.
    jobs.append(
        _cron_job(
            job_id="forge_internal_dev_propose",
            app_id="forge",
            handler="cores.autonomy.internal_dev:run_internal_dev_propose_job",
            cron="30 4 * * *",
            args=[],
            metadata={"cycle": "forge", "type": "internal_dev"},
        )
    )

    return jobs


def get_pulse_jobs() -> list[JobDefinition]:
    """PULSE cycle jobs — run every 30 minutes for AI work platforms."""
    jobs = []

    # Staggered every 30 minutes across platforms
    platforms_30min = [
        ("pulse_outlier_discover", "outlier", 0),
        ("pulse_mindrift_discover", "mindrift", 5),
        ("pulse_dataannotation_discover", "dataannotation", 10),
        ("pulse_freelancer_micro_discover", "freelancer_microtask", 20),
        ("pulse_linkedin_discover", "linkedin_easyapply", 25),
        ("pulse_opyre_discover", "opyre_microtask", 30),
    ]

    for job_id, platform, offset in platforms_30min:
        # Run at :offset and :offset+30 every hour
        cron = f"{offset},{offset + 30} * * * *"
        jobs.append(
            _cron_job(
                job_id=job_id,
                app_id="pulse",
                handler="cores.opportunity.engine:OpportunityOrchestrator.execute_cycle",
                cron=cron,
                args=["pulse", 10],
                metadata={"cycle": "pulse", "platform": platform},
            )
        )

    # Pulse sync job (runs every 30 minutes at minute 45)
    jobs.append(
        _cron_job(
            job_id="pulse_sync_scores",
            app_id="pulse",
            handler="cores.opportunity.tasks:sync_cycle_scores",
            cron="45 * * * *",
            args=["pulse"],
            metadata={"cycle": "pulse", "type": "sync"},
        )
    )

    # Pulse execution orchestrator job (runs every 30 minutes at minute 45)
    jobs.append(
        _cron_job(
            job_id="pulse_execute_orchestrator",
            app_id="pulse",
            handler="cores.opportunity.engine:OpportunityOrchestrator.execute_cycle",
            cron="45 * * * *",
            args=["pulse", 100],
            metadata={"cycle": "pulse", "type": "orchestrator"},
        )
    )

    # PULSE fast platform executors (run every 15 minutes)
    jobs.append(
        _cron_job(
            job_id="pulse_mindrift_fast",
            app_id="pulse",
            handler="cores.opportunity.executors.mindrift_executor:claim",
            cron="*/15 * * * *",
            args=[],
            metadata={"cycle": "pulse", "platform": "mindrift", "type": "fast"},
        )
    )

    return jobs


def get_vault_jobs() -> list[JobDefinition]:
    """VAULT cycle — backup secrets and rotate credentials every 2 hours."""
    jobs = []

    jobs.append(
        _cron_job(
            job_id="vault_backup_2h",
            app_id="vault",
            handler="cores.credentials.vault.backup_vault",
            cron="0 */2 * * *",
            metadata={"cycle": "vault", "type": "backup"},
        )
    )

    jobs.append(
        _cron_job(
            job_id="vault_health_4h",
            app_id="vault",
            handler="cores.credentials.health:check_secrets_health",
            cron="*/30 * * * *",
            metadata={"cycle": "vault", "type": "health_check"},
        )
    )

    return jobs


def get_atlas_jobs() -> list[JobDefinition]:
    """ATLAS cycle — health and intelligence collection every 5 minutes."""
    jobs = []

    jobs.append(
        _cron_job(
            job_id="atlas_health_5min",
            app_id="atlas",
            handler="cores.orion.health.checker:collect_health_metrics",
            cron="*/5 * * * *",
            metadata={"cycle": "atlas", "type": "health"},
        )
    )

    jobs.append(
        _cron_job(
            job_id="atlas_intel_30min",
            app_id="atlas",
            handler="cores.orion.intelligence.collector:collect_intel",
            cron="*/30 * * * *",
            metadata={"cycle": "atlas", "type": "intel"},
        )
    )

    return jobs


def get_security_jobs() -> list[JobDefinition]:
    """SECURITY cycle jobs — run Rastro pipeline automatically.

    Jobs:
    - security_cycle_start: auto-start cycle every 2h (if idle)
    - security_cycle_advance: advance pipeline every 30min
    - security_cycle_sync: sync scores/knowledge hourly
    """
    jobs = []

    # Auto-start cycle every 2 hours (if idle/not running)
    jobs.append(
        _cron_job(
            job_id="security_cycle_start",
            app_id="security",
            handler="cores.cycles.tasks:auto_start_security_cycle",
            cron="0 */2 * * *",
            args=[],
            metadata={"cycle": "security", "type": "auto_start"},
        )
    )

    # Advance pipeline stages every 30 minutes
    jobs.append(
        _cron_job(
            job_id="security_cycle_advance",
            app_id="security",
            handler="cores.cycles.tasks:advance_security_pipeline",
            cron="30 * * * *",
            metadata={"cycle": "security", "type": "advance"},
        )
    )

    # Auto-submit confirmed findings that pass Quality Gate — every 30 min
    jobs.append(
        _cron_job(
            job_id="security_auto_submit",
            app_id="security",
            handler="cores.cycles.tasks:auto_submit_pending_findings",
            cron="45 * * * *",
            metadata={"cycle": "security", "type": "auto_submit"},
        )
    )

    # Sync scores and knowledge hourly
    jobs.append(
        _cron_job(
            job_id="security_cycle_sync",
            app_id="security",
            handler="cores.opportunity.tasks:sync_cycle_scores",
            cron="15 * * * *",
            args=["security"],
            metadata={"cycle": "security", "type": "sync"},
        )
    )

    # Bounty coordinator — manage parallel bounty execution every 15 minutes
    jobs.append(
        _discovery_job(
            job_id="security_bounty_coordinator",
            app_id="security",
            handler="cores.agents.bounty_coordinator:run_coordinator_cycle",
            seconds=900,  # 15 minutes
            metadata={"cycle": "security", "type": "coordinator"},
        )
    )

    # Change watch — baselines de superficie + alertas de delta cada 6h (P3)
    jobs.append(
        _cron_job(
            job_id="security_change_watch",
            app_id="security",
            handler="cores.cycles.tasks:run_change_watch",
            cron="0 */6 * * *",
            metadata={"cycle": "security", "type": "change_watch"},
        )
    )

    # Review digest — un aviso diario si la cola necesita ojos humanos (08:00)
    jobs.append(
        _cron_job(
            job_id="security_review_digest",
            app_id="security",
            handler="cores.cycles.tasks:run_review_queue_digest",
            cron="0 8 * * *",
            metadata={"cycle": "security", "type": "review_digest"},
        )
    )

    # AI scope watch — scope de programas AI frontier cada día (P(unique) alta
    # ante asset nuevo: OpenAI/Anthropic/Microsoft). Handler sin DB.
    jobs.append(
        _cron_job(
            job_id="security_ai_scope_watch",
            app_id="security",
            handler="cores.cycles.tasks:run_ai_scope_watch",
            cron="0 7 * * *",
            metadata={"cycle": "security", "type": "ai_scope_watch"},
        )
    )

    # NOTE (2026-09-09): coder_autopilot job removed — handler
    # cores.cycles.tasks_coder_autopilot:run_coder_autopilot was never
    # implemented (dead silent no-op). Re-add with a real runner
    # (see DECISIONS.md). Dev bounties still flow via DevBountyPipeline
    # + execution_queue jobs.

    # Security bounty platform discovery — every 2 hours
    jobs.append(
        _discovery_job(
            job_id="security_hackerone_discover",
            app_id="security",
            handler="cores.opportunity.adapters.security.hackerone:HackerOneAdapter.fetch_opportunities",
            seconds=7200,  # every 2 hours
            metadata={"cycle": "security", "platform": "hackerone"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="security_bugcrowd_discover",
            app_id="security",
            handler="cores.opportunity.adapters.security.bugcrowd:BugcrowdAdapter.fetch_opportunities",
            seconds=7200,
            metadata={"cycle": "security", "platform": "bugcrowd"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="security_intigriti_discover",
            app_id="security",
            handler="cores.opportunity.adapters.security.intigriti:IntigritiAdapter.fetch_opportunities",
            seconds=7200,
            metadata={"cycle": "security", "platform": "intigriti"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="security_yeswehack_discover",
            app_id="security",
            handler="cores.opportunity.adapters.security.yeswehack:YesWeHackAdapter.fetch_opportunities",
            seconds=7200,
            metadata={"cycle": "security", "platform": "yeswehack"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="security_immunefi_discover",
            app_id="security",
            handler="cores.opportunity.adapters.security.immunefi:ImmunefiAdapter.fetch_opportunities",
            seconds=7200,
            metadata={"cycle": "security", "platform": "immunefi"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="security_synack_discover",
            app_id="security",
            handler="cores.opportunity.adapters.security.synack:SynackAdapter.fetch_opportunities",
            seconds=7200,
            metadata={"cycle": "security", "platform": "synack"},
        )
    )

    # Security bounty submissions sync — every hour (placeholder for future)

    return jobs


def get_direct_work_jobs() -> list[JobDefinition]:
    """DIRECT WORK jobs — autonomous production of delivery-ready zero-barrier jobs.

    Jobs:
    - work_bank_daily_cycle: discover + prepare zero-barrier jobs every day (06:15)
    - autonomous_discovery: continuous web research for new zero-barrier platforms (every 6h)
    - market_evolution_daily: analyze platform sources, update market KB, retire stale (daily at 06:30)
    """
    return [
        _cron_job(
            job_id="work_bank_daily_cycle",
            app_id="direct-work",
            handler="cores.direct_work_engine.workbank:run_daily_cycle",
            cron="15 6 * * *",
            args=[],
            metadata={"type": "work_bank", "desc": "prepara trabajos cero-barrera listos para entregar"},
        ),
        _cron_job(
            job_id="autonomous_discovery_research",
            app_id="direct-work",
            handler="cores.direct_work_engine.autonomous_discovery:run_autonomous_research_cycle",
            cron="0 */6 * * *",
            args=[],
            metadata={"type": "discovery", "desc": "investigación autónoma de nuevas plataformas cero-barrera"},
        ),
        _cron_job(
            job_id="market_evolution_daily",
            app_id="direct-work",
            handler="cores.cycles.tasks:run_daily_market_evolution",
            cron="30 6 * * *",
            args=[],
            metadata={
                "type": "market_evolution",
                "desc": "analiza fuentes de plataformas, actualiza market KB, retira plataformas obsoletas",
            },
        ),
        _cron_job(
            job_id="daily_delivery_preparation",
            app_id="direct-work",
            handler="cores.cycles.tasks:run_daily_delivery_preparation",
            cron="45 6 * * *",
            args=[],
            metadata={
                "type": "delivery",
                "desc": "prepara paquetes de entrega para trabajos ready_to_deliver del banco",
            },
        ),
        _cron_job(
            job_id="daily_task_refresh",
            app_id="direct-work",
            handler="cores.cycles.tasks:run_daily_task_refresh",
            cron="0 7 * * *",
            args=[],
            metadata={
                "type": "daily_tasks",
                "desc": "auto-completa tareas resueltas + refresca el tablero diario",
            },
        ),
        _cron_job(
            job_id="curated_sources_probe",
            app_id="direct-work",
            handler="cores.direct_work_engine.source_registry:run_source_probe_cycle",
            cron="0 5 * * 0",
            args=[],
            metadata={
                "type": "probe",
                "desc": "verifica liveness de las fuentes curadas cada domingo (tri-estado + quarantine)",
            },
        ),
    ]


def get_investment_jobs() -> list[JobDefinition]:
    """INVESTMENT jobs — autonomous revenue engines.

    - investment_arbitrage_scan: cross-exchange price-gap scan (8 exchanges,
      $500k liquidity floor) every 4h. Paper/dry-run; surfaces real edge.
    - risk_guardian_check: auto-pause strategies in drawdown every 15min.
    - startup_checks: detect missing credentials, stalled pipelines every 1h.
    """
    return [
        _cron_job(
            job_id="investment_arbitrage_scan",
            app_id="investment",
            handler="cores.investment.tasks:run_investment_arbitrage_scan",
            cron="0 */4 * * *",
            args=[],
            metadata={
                "cycle": "investment",
                "type": "scan",
                "desc": "escaneo de brechas de precio cross-exchange cada 4h (solo lectura, sin ordenes)",
            },
        ),
        _cron_job(
            job_id="risk_guardian_check",
            app_id="investment",
            handler="cores.investment.risk_guardian:run_risk_guardian_check",
            cron="*/15 * * * *",
            args=[],
            metadata={
                "cycle": "investment",
                "type": "risk",
                "desc": "verificacion automatica de drawdown y pausa de estrategias",
            },
        ),
        _cron_job(
            job_id="startup_checks",
            app_id="system",
            handler="cores.startup_checks:run_all_checks",
            cron="0 * * * *",
            args=[],
            metadata={
                "cycle": "system",
                "type": "health",
                "desc": "deteccion de credenciales faltantes, pipelines estancados",
            },
        ),
    ]


def get_qa_jobs() -> list[JobDefinition]:
    """QA jobs — daily automated QA regression run.

    Jobs:
    - qa_daily_cycle: auto-generated test suite run + persistence (08:30)
    """
    return [
        _cron_job(
            job_id="qa_daily_cycle",
            app_id="qa",
            handler="cores.cycles.tasks:run_qa_cycle",
            cron="30 8 * * *",
            args=[],
            metadata={"cycle": "qa", "type": "qa", "desc": "regresion QA automatica diaria"},
        ),
    ]


def get_evolution_jobs() -> list[JobDefinition]:
    """EVOLUTION jobs — daily self-audit of the system.

    Jobs:
    - evolution_report_daily: generate + persist Daily Optimization Report (06:45)
    """
    return [
        _cron_job(
            job_id="evolution_report_daily",
            app_id="evolution",
            handler="cores.cycles.tasks:run_daily_evolution_report",
            cron="45 6 * * *",
            args=[],
            metadata={"cycle": "evolution", "type": "audit", "desc": "reporte de optimizacion diario persistido"},
        ),
    ]


def get_knowledge_jobs() -> list[JobDefinition]:
    """KNOWLEDGE jobs — Obsidian vault sync.

    Jobs:
    - knowledge_sync_daily: incremental index + health snapshot + embeddings (06:30)
    """
    return [
        _cron_job(
            job_id="knowledge_sync_daily",
            app_id="knowledge",
            handler="cores.knowledge.tasks:run_knowledge_sync",
            cron="30 6 * * *",
            args=[],
            metadata={"cycle": "knowledge", "type": "sync", "desc": "sincronizacion diaria del vault de conocimiento"},
        ),
    ]


def get_intelligence_jobs() -> list[JobDefinition]:
    """INTELLIGENCE jobs — feeds refresh (threat intel + science).

    Jobs:
    - intelligence_refresh: fetch 7 feeds → cache w/ provenance (05:00 daily)
    """
    return [
        _cron_job(
            job_id="intelligence_refresh",
            app_id="intelligence",
            handler="cores.intelligence.tasks:run_intelligence_refresh",
            cron="0 5 * * *",
            args=[],
            metadata={"cycle": "intelligence", "type": "sync", "desc": "refresh diario de feeds de inteligencia"},
        ),
    ]


def get_trading_jobs() -> list[JobDefinition]:
    """TRADING jobs — autonomous trading pipeline with copy trading + OWNEX reasoning loop.

    Full automation stack:
    - Risk control + emergency stop (every 5 min)
    - Strategy DNA update from decision journal (every 3:30)
    - Trader discovery + scoring (every 6:30)
    - Auto-backtest pipeline (phases 1-8, every 12h)
    - Auto-validation pipeline (8 phases, every 24h)
    - Regime detection + allocation adjustment (every 30 min)
    - Portfolio rebalancing (daily at 04:00)
    - Capital ladder advance (weekly Sunday 02:00)
    - Kill switch monitoring (every 10 min)
    - Paper trading auto-advance (every 8h if metrics OK)
    - Copy trading ratio optimization (every 6h)
    - Live strategy monitoring + alerts (every 15 min)
    - Expected revenue tracking + probability update (every hour)
    """
    return [
        # ── CORE RISK & SAFETY ──────────────────────────────────────────────
        _cron_job(
            job_id="trading_risk_check",
            app_id="trading",
            handler="cores.trading.copy_trading:run_trading_risk_check",
            cron="*/5 * * * *",
            args=[],
            metadata={
                "cycle": "trading",
                "type": "risk",
                "desc": "verificacion de drawdown y parada de emergencia del copy trading",
            },
        ),
        # ── STRATEGY DNA FROM DECISION JOURNAL ──────────────────────────────
        _cron_job(
            job_id="trading_dna_update",
            app_id="trading",
            handler="cores.trading.reasoning:run_dna_update",
            cron="30 3 * * *",
            args=[],
            metadata={
                "cycle": "trading",
                "type": "reasoning",
                "desc": "correlacion del decision journal a strategy DNA y propuestas",
            },
        ),
        # ── TRADER DISCOVERY & SCORING ──────────────────────────────────────
        _cron_job(
            job_id="trading_discovery",
            app_id="trading",
            handler="cores.trading.trader_intelligence:run_discovery",
            cron="30 6 * * *",
            args=[],
            metadata={
                "cycle": "trading",
                "type": "discovery",
                "desc": "descubrimiento y scoring de traders candidatos",
            },
        ),
        # ── MEMECOIN PAPER LOOP (DRY-RUN, kill-switch gated) ─────────────────
        _cron_job(
            job_id="trading_memecoin_paper",
            app_id="trading",
            handler="cores.trading.paper.memecoin_paper:run_memecoin_paper_cycle",
            cron="*/15 * * * *",
            args=[],
            metadata={
                "cycle": "trading",
                "type": "paper",
                "desc": "paper loop memecoins cada 15m (scan+filtros+exits, sin fondos)",
            },
        ),
        _cron_job(
            job_id="trading_pump_radar",
            app_id="trading",
            handler="cores.trading.pump_radar:run_pump_radar_cycle_sync",
            cron="*/5 * * * *",
            args=[],
            metadata={
                "cycle": "trading",
                "type": "radar",
                "desc": "radar de pumps cada 5m (DexScreener → filtros hard → score, sin fondos)",
            },
        ),
        _cron_job(
            job_id="trading_dip_radar",
            app_id="trading",
            handler="cores.trading.extra_radars:run_dip_radar_cycle_sync",
            cron="*/7 * * * *",
            args=[],
            metadata={
                "cycle": "trading",
                "type": "radar",
                "desc": "dip radar mean-reversion cada 7m (pump + retrace → oportunidad, sin fondos)",
            },
        ),
        _cron_job(
            job_id="trading_spread_radar",
            app_id="trading",
            handler="cores.trading.extra_radars:run_spread_radar_cycle_sync",
            cron="*/3 * * * *",
            args=[],
            metadata={
                "cycle": "trading",
                "type": "radar",
                "desc": "spread CEX/DEX SOL cada 3m (Binance vs Jupiter, sin fondos)",
            },
        ),
        # NOTE (2026-09-18): 8 jobs trading_backtest_phase1-8 removed — handlers
        # "cores.trading.lifecycle:<bare>" solo existen como alias a
        # *_handler(strategy, ...) con args requeridos; jobs con args=[]
        # crasheaban cada ciclo (TypeError) ensuciando ledger+logs. Precedente
        # 2026-09-09. El lifecycle sigue vía API/manual con Human Gate.
        # Re-agregar SOLO con runner testeado (ver DECISIONS.md).
        # NOTE (2026-09-18): 5 jobs trading_validation_* removed — mismo caso:
        # handler "cores.trading.lifecycle:complete_validation" es alias a
        # complete_validation_handler(strategy, passed); jobs con args=[]
        # crasheaban cada ciclo. Re-agregar SOLO con runner testeado.
        # NOTE (2026-09-09): 5 trading jobs removed here (regime_detection,
        # auto_allocation, rebalance_daily, capital_ladder_check,
        # kill_switch_monitor) — handlers were never implemented as
        # module-level functions (dead silent no-ops). Re-add with real
        # runners (see DECISIONS.md). Kill-switch protection stays live
        # via trading_risk_check (CopyTradingEngine.risk_breached).
        # NOTE (2026-09-18): trading_paper_auto_advance removed — mismo caso
        # (handler bare con args requeridos) y además el auto-advance a canary
        # por cron contradice el Human Gate. El lifecycle sigue vía API/manual.
        # NOTE (2026-09-09): 3 trading jobs removed here (copy_optimization,
        # live_monitor, revenue_tracking) — handlers were never implemented
        # as module-level functions (dead silent no-ops). Re-add with real
        # runners (see DECISIONS.md).
    ]


def get_integration_jobs() -> list[JobDefinition]:
    """INTEGRATION jobs — external platform syncs (Outlook calendar)."""
    return [
        _cron_job(
            job_id="outlook_calendar_sync",
            app_id="integrations",
            handler="cores.integrations.outlook.sync:run_calendar_sync",
            cron="*/15 * * * *",
            args=[],
            metadata={
                "cycle": "integrations",
                "type": "calendar",
                "desc": "sincroniza tasks locales con el calendario de Outlook (push) y refresca agenda (pull)",
            },
        ),
    ]


def get_execution_queue_jobs() -> list[JobDefinition]:
    """EXECUTION QUEUE jobs — autonomous processing of the execution queue.

    Jobs:
    - execution_queue_process: process QUEUED items every minute
    - execution_queue_retry: retry FAILED items every 15 minutes
    - execution_queue_dlq: move stale FAILED to DEAD_LETTER hourly
    """
    return [
        _discovery_job(
            job_id="execution_queue_process",
            app_id="execution",
            handler="cores.execution_queue.driver:process_queue_scheduler",
            seconds=60,  # every minute
            metadata={"cycle": "execution", "type": "process"},
        ),
        _cron_job(
            job_id="execution_queue_retry",
            app_id="execution",
            handler="cores.execution_queue.driver:retry_failed_scheduler",
            cron="*/15 * * * *",
            metadata={"cycle": "execution", "type": "retry"},
        ),
        _cron_job(
            job_id="execution_queue_dlq",
            app_id="execution",
            handler="cores.execution_queue.driver:move_to_dlq_scheduler",
            cron="0 * * * *",
            metadata={"cycle": "execution", "type": "dlq"},
        ),
    ]


def get_worker_core_jobs() -> list[JobDefinition]:
    """WorkerCore orchestration jobs."""
    return [
        JobDefinition(
            job_id="worker_core_heartbeat",
            app_id="worker_core",
            handler="cores.worker_core.orchestrator:worker_core_heartbeat",
            trigger="interval",
            seconds=900,  # every 15 min
            kwargs={"args": []},
            metadata={"description": "Ensure WorkerCore is running, start if stopped"},
        ),
    ]


def get_economic_feedback_jobs() -> list[JobDefinition]:
    """Economic Feedback — LEARN→RECALIBRATE→REALLOCATE daily."""
    return [
        _cron_job(
            job_id="economic_feedback_daily",
            app_id="economic_feedback",
            handler="cores.economic_feedback.tasks:run_economic_feedback",
            cron="40 6 * * *",
            metadata={
                "cycle": "economic_feedback",
                "type": "recalibrate",
                "desc": "recalcula net/h realizado, P(CASH) real y reasignación diaria",
            },
        ),
        _cron_job(
            job_id="autopilot_kill_scale",
            app_id="economic_feedback",
            handler="cores.automation.kill_scale:run_autopilot_scheduler",
            cron="45 6 * * *",
            metadata={
                "cycle": "economic_feedback",
                "type": "autopilot",
                "desc": "pausa canales muertos / mata productos solo con evidencia dura (reversible)",
            },
        ),
        _cron_job(
            job_id="daily_loop_run",
            app_id="economic_feedback",
            handler="cores.automation.daily_loop_tasks:run_daily_loop_scheduler",
            cron="50 6 * * *",
            metadata={
                "cycle": "economic_feedback",
                "type": "daily_loop",
                "desc": "SELECT→PREPARE→GATE: parquea top-3 en A3 para solo-aprobar",
            },
        ),
    ]


def get_ecommerce_jobs() -> list[JobDefinition]:
    """E-commerce cycle jobs (lazy import: pipeline owns the handlers)."""
    from cores.ecommerce.pipeline import get_ecommerce_jobs as _get_jobs

    return _get_jobs()


def get_all_jobs() -> dict[str, list[JobDefinition]]:
    """Return all cycle jobs."""
    return {
        "security": get_security_jobs(),
        "forge": get_forge_jobs(),
        "pulse": get_pulse_jobs(),
        "vault": get_vault_jobs(),
        "atlas": get_atlas_jobs(),
        "direct_work": get_direct_work_jobs(),
        "investment": get_investment_jobs(),
        "qa": get_qa_jobs(),
        "evolution": get_evolution_jobs(),
        "knowledge": get_knowledge_jobs(),
        "intelligence": get_intelligence_jobs(),
        "trading": get_trading_jobs(),
        "integrations": get_integration_jobs(),
        "execution": get_execution_queue_jobs(),
        "worker_core": get_worker_core_jobs(),
        "ecommerce": get_ecommerce_jobs(),
        "economic_feedback": get_economic_feedback_jobs(),
    }
