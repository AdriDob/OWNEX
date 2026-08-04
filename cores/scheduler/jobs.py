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
            handler="core.cycles.security:get_security_cycle",
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

    return jobs


def get_investment_jobs() -> list[JobDefinition]:
    """INVESTMENT jobs — autonomous revenue engines.

    - investment_arbitrage_scan: cross-exchange price-gap scan (8 exchanges,
      $500k liquidity floor) every 4h. Paper/dry-run; surfaces real edge.
    """
    return [
        _cron_job(
            job_id="investment_arbitrage_scan",
            app_id="investment",
            handler="core.investment.tasks:run_global_arbitrage_scan",
            cron="23 */4 * * *",
            args=[],
            metadata={"cycle": "investment", "type": "revenue", "desc": "escaneo automatico de arbitraje cross-exchange"},
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
        "investment": get_investment_jobs(),
    }
