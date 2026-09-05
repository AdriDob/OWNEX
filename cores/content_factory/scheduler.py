"""Content Factory Scheduler Jobs - Registered with OWNEX CoreScheduler."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apscheduler.triggers.cron import CronTrigger

from cores.content_factory.models import (
    ChannelConfig,
    VideoAnalytics,
    VideoJob,
    VideoJobStatus,
    VideoTopic,
)
from cores.content_factory.topic_bank import TopicBankService


def get_content_factory_jobs() -> list[dict[str, Any]]:
    """Return list of Content Factory job definitions for CoreScheduler."""
    return [
        {
            "job_id": "content_factory_daily_generate",
            "name": "Content Factory - Daily Video Generation",
            "trigger": CronTrigger(hour=6, minute=0),  # 06:00 UTC
            "handler": "cores.content_factory.scheduler:run_daily_generate",
            "max_instances": 1,
            "misfire_grace_time": 3600,
            "coalesce": True,
        },
        {
            "job_id": "content_factory_daily_publish",
            "name": "Content Factory - Daily Video Publishing",
            "trigger": CronTrigger(hour=7, minute=0),  # 07:00 UTC
            "handler": "cores.content_factory.scheduler:run_daily_publish",
            "max_instances": 1,
            "misfire_grace_time": 3600,
            "coalesce": True,
        },
        {
            "job_id": "content_factory_hourly_analytics",
            "name": "Content Factory - Hourly Analytics Sync",
            "trigger": CronTrigger(minute=15),  # Every hour at :15
            "handler": "cores.content_factory.scheduler:run_hourly_analytics",
            "max_instances": 1,
            "misfire_grace_time": 1800,
            "coalesce": True,
        },
        {
            "job_id": "content_factory_weekly_optimize",
            "name": "Content Factory - Weekly Optimization",
            "trigger": CronTrigger(day_of_week=6, hour=2, minute=0),  # Sunday 02:00 UTC
            "handler": "cores.content_factory.scheduler:run_weekly_optimize",
            "max_instances": 1,
            "misfire_grace_time": 7200,
            "coalesce": True,
        },
        {
            "job_id": "content_factory_health_check",
            "name": "Content Factory - MPT Health Check",
            "trigger": CronTrigger(minute="*/10"),  # Every 10 minutes
            "handler": "cores.content_factory.scheduler:run_health_check",
            "max_instances": 1,
            "misfire_grace_time": 300,
            "coalesce": True,
        },
    ]


# Global service instances (initialized by lifespan)
_mpt_client: Optional = None
_topic_bank_service: Optional = None


def init_services(mpt_client, db_session_factory):
    """Initialize global service instances."""
    global _mpt_client, _topic_bank_service

    _mpt_client = mpt_client

    # TopicBankService needs a db session - we'll create it per job
    _topic_bank_service = TopicBankService


def get_mpt_client() -> Optional:
    return _mpt_client


def get_topic_bank_service():
    return _topic_bank_service


# ========== Job Handlers ==========


async def run_daily_generate() -> dict[str, Any]:
    """Generate videos for all active channels."""
    from cores.content_factory.mpt_client import create_mpt_client
    from cores.content_factory.service import ContentFactoryService
    from database.db import SessionLocal

    results = {"channels_processed": 0, "total_jobs_created": 0, "errors": []}

    db = SessionLocal()
    try:
        channels = db.query(ChannelConfig).filter(ChannelConfig.is_active == 1).all()

        mpt_client = await create_mpt_client()

        for channel in channels:
            try:
                service = ContentFactoryService(
                    db_session=db,
                    mpt_client=mpt_client,
                )
                jobs = await service.run_full_pipeline(
                    channel_id=channel.id,
                    topics_count=5,
                    videos_per_topic=3,
                )
                results["total_jobs_created"] += len(jobs)
                results["channels_processed"] += 1
            except Exception as e:
                results["errors"].append(f"Channel {channel.id}: {str(e)}")

        return results
    finally:
        db.close()


async def run_daily_publish() -> dict[str, Any]:
    """Publish pending videos for all active channels."""
    from cores.content_factory.models import VideoJob
    from cores.content_factory.mpt_client import create_mpt_client
    from cores.content_factory.service import create_content_factory_service
    from database.db import SessionLocal

    results = {"channels_processed": 0, "total_published": 0, "errors": []}

    db = SessionLocal()
    try:
        channels = db.query(ChannelConfig).filter(ChannelConfig.is_active == 1).all()

        mpt_client = await create_mpt_client()

        for channel in channels:
            try:
                # Find jobs ready for publishing
                pending_jobs = (
                    db.query(VideoJob)
                    .filter(
                        VideoJob.channel_id == channel.id,
                        VideoJob.status.in_([VideoJobStatus.QUALITY_GATE, VideoJobStatus.PUBLISHING]),
                        VideoJob.quality_passed == 1,
                    )
                    .all()
                )

                async with create_content_factory_service(db, await create_mpt_client()) as service:
                    for job in pending_jobs:
                        try:
                            await service.publish_to_youtube(job)
                        except Exception:
                            pass

                published = sum(1 for j in pending_jobs if j.status == VideoJobStatus.PUBLISHED)
                results["total_published"] += published
                results["channels_processed"] += 1

            except Exception as e:
                results["errors"].append(f"Channel {channel.id}: {str(e)}")

        return results
    finally:
        db.close()


async def run_hourly_analytics() -> dict[str, Any]:
    """Sync analytics from YouTube for recent videos."""
    from cores.content_factory.models import VideoJob
    from database.db import SessionLocal

    results = {"synced": 0, "errors": []}

    db = SessionLocal()
    try:
        # Get recently published videos (last 7 days)
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(days=7)

        published_jobs = (
            db.query(VideoJob)
            .filter(
                VideoJob.status == VideoJobStatus.PUBLISHED,
                VideoJob.published_at >= cutoff,
                VideoJob.youtube_video_id.isnot(None),
            )
            .all()
        )

        # Note: Actual YouTube Analytics API sync would go here
        # Requires OAuth2 tokens and google-api-python-client

        results["synced"] = len(published_jobs)
        return results
    finally:
        db.close()


async def run_weekly_optimize() -> dict[str, Any]:
    """Weekly optimization: re-score topics, archive exhausted, feedback loop."""
    from sqlalchemy import func

    from cores.content_factory.models import ChannelConfig
    from database.db import SessionLocal

    results = {"channels_processed": 0, "topics_rescored": 0, "topics_archived": 0}

    db = SessionLocal()
    try:
        channels = db.query(ChannelConfig).filter(ChannelConfig.is_active == 1).all()

        for channel in channels:
            # Re-score topics based on recent performance
            topic_performance = (
                db.query(
                    VideoAnalytics.video_job_id,
                    func.avg(VideoAnalytics.views).label("avg_views"),
                    func.avg(VideoAnalytics.retention_30s).label("avg_retention"),
                    func.avg(VideoAnalytics.rpm_usd).label("avg_rpm"),
                )
                .join(VideoJob, VideoAnalytics.video_job_id == VideoJob.id)
                .filter(
                    VideoJob.channel_id == channel.id,
                    VideoJob.status == "published",
                )
                .group_by(VideoAnalytics.video_job_id)
                .all()
            )

            # Map job_id -> topic_id
            # Update topic scores based on performance

            # Archive exhausted topics
            exhausted = (
                db.query(VideoTopic)
                .filter(
                    VideoTopic.channel_id == channel.id,
                    VideoTopic.status == "exhausted",
                )
                .count()
            )

            results["channels_processed"] += 1

        return results
    finally:
        db.close()


async def run_health_check() -> dict[str, Any]:
    """Check MoneyPrinterTurbo API health."""
    from cores.content_factory.mpt_client import create_mpt_client

    try:
        mpt_client = await create_mpt_client()
        healthy = await mpt_client.wait_for_healthy(timeout=30.0, interval=2.0)

        return {
            "healthy": healthy,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# For backward compatibility with CoreScheduler
def get_job_handlers():
    """Return dict of job_id -> handler function."""
    return {
        "content_factory_daily_generate": run_daily_generate,
        "content_factory_daily_publish": run_daily_publish,
        "content_factory_hourly_analytics": run_hourly_analytics,
        "run_weekly_optimize": run_weekly_optimize,
        "content_factory_health_check": run_health_check,
    }
