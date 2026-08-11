"""Scheduler Job Definitions — All cycles (Forge, Pulse, Vault, Atlas).

Each cycle has staggered discovery jobs + a sync/scoring job.
"""

from __future__ import annotations

from core.interfaces.scheduler import JobDefinition


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
        kwargs={"cron": cron, "args": args or []},
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
            handler="core.opportunity.adapters.forge.opencollective:fetch_opportunities",
            seconds=3600,  # hourly
            metadata={"cycle": "forge", "platform": "opencollective"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="forge_opencollective_projects_discover",
            app_id="forge",
            handler="core.opportunity.adapters.forge.opencollective_projects:fetch_opportunities",
            seconds=3600,
            metadata={"cycle": "forge", "platform": "opencollective_projects"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="forge_algora_discover",
            app_id="forge",
            handler="core.opportunity.adapters.forge.algora:fetch_opportunities",
            seconds=3600,
            metadata={"cycle": "forge", "platform": "algora"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="forge_superteam_discover",
            app_id="forge",
            handler="core.opportunity.adapters.forge.superteam:fetch_opportunities",
            seconds=3600,
            metadata={"cycle": "forge", "platform": "superteam"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="forge_github_sponsors_discover",
            app_id="forge",
            handler="core.opportunity.adapters.forge.github_sponsors:fetch_opportunities",
            seconds=3600,
            metadata={"cycle": "forge", "platform": "github_sponsors"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="forge_freelancer_discover",
            app_id="forge",
            handler="core.opportunity.adapters.forge.freelancer:fetch_opportunities",
            seconds=3600,
            metadata={"cycle": "forge", "platform": "freelancer"},
        )
    )

    # Issue Platforms (also in Forge)
    jobs.append(
        _discovery_job(
            job_id="forge_issuehunt_discover",
            app_id="forge",
            handler="core.opportunity.adapters.forge.issuehunt:fetch_opportunities",
            seconds=3600,
            metadata={"cycle": "forge", "platform": "issuehunt"},
        )
    )
    jobs.append(
        _discovery_job(
            job_id="forge_opire_discover",
            app_id="forge",
            handler="core.opportunity.adapters.forge.opire:fetch_opportunities",
            seconds=3600,
            metadata={"cycle": "forge", "platform": "opire"},
        )
    )

    # Sync job — runs after all discovery (hourly at minute 55)
    jobs.append(
        _cron_job(
            job_id="forge_sync_scores",
            app_id="forge",
            handler="core.opportunity.tasks:sync_cycle_scores",
            cron="55 * * * *",
            args=["forge"],
            metadata={"cycle": "forge", "type": "sync"},
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
        ("pulse_remotasks_discover", "remotasks", 15),
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
                handler="core.opportunity.engine:OpportunityOrchestrator.execute_cycle",
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
            handler="core.opportunity.tasks:sync_cycle_scores",
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
            handler="core.opportunity.engine:OpportunityOrchestrator.execute_cycle",
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
            handler="core.opportunity.executors.mindrift_executor:claim",
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
            handler="core.credentials.vault.backup_vault",
            cron="0 */2 * * *",
            metadata={"cycle": "vault", "type": "backup"},
        )
    )

    jobs.append(
        _cron_job(
            job_id="vault_health_4h",
            app_id="vault",
            handler="core.credentials.health:check_secrets_health",
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
            handler="core.orion.health.checker:collect_health_metrics",
            cron="*/5 * * * *",
            metadata={"cycle": "atlas", "type": "health"},
        )
    )

    jobs.append(
        _cron_job(
            job_id="atlas_intel_30min",
            app_id="atlas",
            handler="core.orion.intelligence.collector:collect_intel",
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
            handler="core.cycles.tasks:auto_start_security_cycle",
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
            handler="core.cycles.tasks:advance_security_pipeline",
            cron="30 * * * *",
            metadata={"cycle": "security", "type": "advance"},
        )
    )

    # Auto-submit confirmed findings that pass Quality Gate — every 30 min
    jobs.append(
        _cron_job(
            job_id="security_auto_submit",
            app_id="security",
            handler="core.cycles.tasks:auto_submit_pending_findings",
            cron="45 * * * *",
            metadata={"cycle": "security", "type": "auto_submit"},
        )
    )

    # Sync scores and knowledge hourly
    jobs.append(
        _cron_job(
            job_id="security_cycle_sync",
            app_id="security",
            handler="core.opportunity.tasks:sync_cycle_scores",
            cron="15 * * * *",
            args=["security"],
            metadata={"cycle": "security", "type": "sync"},
        )
    )

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
            handler="core.cycles.tasks:run_daily_market_evolution",
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
            handler="core.cycles.tasks:run_daily_delivery_preparation",
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
            handler="core.cycles.tasks:run_daily_task_refresh",
            cron="0 7 * * *",
            args=[],
            metadata={
                "type": "daily_tasks",
                "desc": "auto-completa tareas resueltas + refresca el tablero diario",
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
            handler="core.investment.tasks:run_global_arbitrage_scan",
            cron="23 */4 * * *",
            args=[],
            metadata={
                "cycle": "investment",
                "type": "revenue",
                "desc": "escaneo automatico de arbitraje cross-exchange",
            },
        ),
        _cron_job(
            job_id="risk_guardian_check",
            app_id="investment",
            handler="core.investment.risk_guardian:get_risk_guardian",
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
            handler="core.cycles.tasks:run_qa_cycle",
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
            handler="core.cycles.tasks:run_daily_evolution_report",
            cron="45 6 * * *",
            args=[],
            metadata={"cycle": "evolution", "type": "audit", "desc": "reporte de optimizacion diario persistido"},
        ),
    ]


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
    }
