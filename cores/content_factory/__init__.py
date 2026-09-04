"""Content Factory - Automated content generation for YouTube Shorts."""

from __future__ import annotations

from cores.content_factory.models import (
    ChannelConfig,
    TopicPerformance,
    VideoAnalytics,
    VideoJob,
    VideoJobStatus,
    VideoTopic,
    VideoTopicStatus,
)
from cores.content_factory.mpt_client import (
    MaterialSource,
    MPTClient,
    MPTJobStatus,
    SubtitleProvider,
    VideoAspect,
    VideoGenerationRequest,
    VoiceProvider,
    create_mpt_client,
)
from cores.content_factory.scheduler import (
    get_content_factory_jobs,
    init_services,
    run_daily_generate,
    run_daily_publish,
    run_health_check,
    run_hourly_analytics,
    run_weekly_optimize,
)
from cores.content_factory.service import (
    ContentFactoryService,
    QualityGateResult,
    create_content_factory_service,
)
from cores.content_factory.topic_bank import TopicBankService

__all__ = [
    # Models
    "ChannelConfig",
    "VideoJob",
    "VideoJobStatus",
    "VideoTopic",
    "VideoTopicStatus",
    "VideoAnalytics",
    "TopicPerformance",
    # MPT Client
    "MPTClient",
    "create_mpt_client",
    "VideoGenerationRequest",
    "VideoAspect",
    "MaterialSource",
    "VoiceProvider",
    "SubtitleProvider",
    "MPTJobStatus",
    # Topic Bank
    "TopicBankService",
    # Service
    "ContentFactoryService",
    "QualityGateResult",
    "create_content_factory_service",
    # Scheduler
    "get_content_factory_jobs",
    "init_services",
    "run_daily_generate",
    "run_daily_publish",
    "run_hourly_analytics",
    "run_weekly_optimize",
    "run_health_check",
]
