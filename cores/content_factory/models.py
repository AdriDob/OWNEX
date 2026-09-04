"""Content Factory Models - Database models for automated content generation."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

if TYPE_CHECKING:
    pass


class VideoJobStatus(str, enum.Enum):
    """Status of a video generation job."""

    PENDING = "pending"
    GENERATING = "generating"
    QUALITY_GATE = "quality_gate"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    ARCHIVED = "archived"


class VideoTopicStatus(str, enum.Enum):
    """Status of a video topic in the bank."""

    PENDING = "pending"
    ACTIVE = "active"
    ARCHIVED = "archived"
    EXHAUSTED = "exhausted"


class ChannelPlatform(str, enum.Enum):
    """Supported publishing platforms."""

    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"


class ChannelConfig(Base):
    """Configuration for a publishing channel."""

    __tablename__ = "content_factory_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    platform = Column(Enum(ChannelPlatform), nullable=False, default=ChannelPlatform.YOUTUBE)

    # YouTube Data API credentials
    youtube_client_id = Column(String(500), nullable=True)
    youtube_client_secret = Column(String(500), nullable=True)
    youtube_refresh_token = Column(Text, nullable=True)
    youtube_channel_id = Column(String(100), nullable=True)

    # Upload-Post credentials (for multi-platform)
    upload_post_api_key = Column(String(500), nullable=True)
    upload_post_username = Column(String(100), nullable=True)

    # Publishing settings
    default_privacy = Column(String(20), default="public")
    default_tags = Column(JSON, default=list)
    upload_schedule = Column(JSON, default=list)  # List of {"hour": 12, "timezone": "UTC"}
    auto_publish_enabled = Column(Integer, default=0)  # 0/1

    # Quality gate settings
    quality_threshold = Column(Integer, default=70)
    max_duration_seconds = Column(Integer, default=70)
    min_duration_seconds = Column(Integer, default=55)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Integer, default=1)

    # Relationships
    topics = relationship("VideoTopic", back_populates="channel")
    jobs = relationship("VideoJob", back_populates="channel")


class VideoTopic(Base):
    """A topic in the content bank, ready for video generation."""

    __tablename__ = "content_factory_topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(Integer, ForeignKey("content_factory_channels.id"), nullable=False)

    # Topic content
    title = Column(String(200), nullable=False)
    hook = Column(Text, nullable=True)  # The opening hook
    insight = Column(Text, nullable=True)  # The key insight/value
    keywords = Column(JSON, default=list)  # SEO keywords
    category = Column(String(50), default="science_curiosity")
    language = Column(String(10), default="en")

    # Scoring and prioritization
    score = Column(Integer, default=50)  # 0-100
    priority = Column(Integer, default=0)  # Higher = more urgent
    status = Column(Enum(VideoTopicStatus), default=VideoTopicStatus.PENDING)

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    avg_views = Column(Integer, default=0)
    avg_retention = Column(Integer, default=0)
    avg_rpm = Column(Integer, default=0)

    # Metadata
    source_url = Column(String(500), nullable=True)  # Original source
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    channel = relationship("ChannelConfig", back_populates="topics")
    jobs = relationship("VideoJob", back_populates="topic")

    __table_args__ = (UniqueConstraint("channel_id", "title", name="uq_channel_topic_title"),)


class VideoJob(Base):
    """A video generation job tracking the full pipeline."""

    __tablename__ = "content_factory_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(Integer, ForeignKey("content_factory_channels.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("content_factory_topics.id"), nullable=True)

    # Job status and tracking
    status = Column(Enum(VideoJobStatus), default=VideoJobStatus.PENDING, index=True)
    mpt_job_id = Column(String(100), nullable=True, index=True)  # MoneyPrinterTurbo job ID

    # Generation parameters
    generation_params = Column(JSON, default=dict)

    # Output
    video_paths = Column(JSON, default=list)  # List of generated video file paths
    selected_video_index = Column(Integer, nullable=True)
    output_video_path = Column(String(500), nullable=True)

    # Quality gate
    quality_score = Column(Integer, nullable=True)
    quality_details = Column(JSON, default=dict)
    quality_passed = Column(Integer, nullable=True)  # 0/1/NULL

    # Publishing
    youtube_video_id = Column(String(100), nullable=True)
    upload_post_result = Column(JSON, nullable=True)
    published_at = Column(DateTime, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_stage = Column(String(50), nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    channel = relationship("ChannelConfig", back_populates="jobs")
    topic = relationship("VideoTopic", back_populates="jobs")


class VideoAnalytics(Base):
    """Analytics data synced from YouTube Analytics API."""

    __tablename__ = "content_factory_analytics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_job_id = Column(Integer, ForeignKey("content_factory_jobs.id"), nullable=False, index=True)
    youtube_video_id = Column(String(100), nullable=False, index=True)

    # Core metrics
    views = Column(Integer, default=0)
    watch_time_seconds = Column(Integer, default=0)
    avg_view_duration_seconds = Column(Integer, default=0)

    # Retention
    retention_3s = Column(Integer, default=0)
    retention_10s = Column(Integer, default=0)
    retention_30s = Column(Integer, default=0)
    retention_60s = Column(Integer, default=0)

    # Engagement
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    subscribers_gained = Column(Integer, default=0)

    # Monetization
    estimated_revenue_usd = Column(Integer, default=0)  # In cents
    rpm_usd = Column(Integer, default=0)  # In cents per 1000 views

    # Traffic sources (JSON)
    traffic_sources = Column(JSON, default=dict)

    # Time windows
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    last_synced_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    video_job = relationship("VideoJob")


class TopicPerformance(Base):
    """Aggregated performance metrics per topic."""

    __tablename__ = "content_factory_topic_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("content_factory_topics.id"), nullable=False, unique=True)

    # Aggregated metrics
    videos_published = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    avg_views = Column(Integer, default=0)
    avg_retention_30s = Column(Integer, default=0)
    avg_rpm_cents = Column(Integer, default=0)
    success_rate = Column(Integer, default=0)  # Percentage * 100

    # Trend
    trend_views = Column(Integer, default=0)  # Positive = growing
    trend_retention = Column(Integer, default=0)

    # Metadata
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    topic = relationship("VideoTopic")


# Helper functions
def create_tables(engine):
    """Create all tables."""
    Base.metadata.create_all(engine)


def drop_tables(engine):
    """Drop all tables."""
    Base.metadata.drop_all(engine)


# JSON serialization helpers
def json_default(obj: Any) -> Any:
    """Default JSON serializer for non-standard types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, enum.Enum):
        return obj.value
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def to_dict(obj: Base) -> dict[str, Any]:
    """Convert SQLAlchemy model to dict."""
    result = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        if isinstance(value, datetime):
            result[column.name] = value.isoformat()
        elif isinstance(value, enum.Enum):
            result[column.name] = value.value
        else:
            result[column.name] = value
    return result
