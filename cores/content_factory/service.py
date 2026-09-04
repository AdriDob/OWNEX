"""Content Factory Pipeline Service - Orchestrates the full video generation pipeline."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from cores.content_factory.models import (
    ChannelConfig,
    VideoJob,
    VideoJobStatus,
    VideoTopic,
    VideoTopicStatus,
)
from cores.content_factory.mpt_client import (
    MPTClient,
    VideoGenerationRequest,
    VoiceProvider,
)

logger = logging.getLogger("ownex.content_factory.service")


class QualityGateResult:
    """Result of quality gate check."""

    def __init__(
        self,
        passed: bool,
        score: int,
        details: dict[str, Any],
        issues: list[str],
    ):
        self.passed = passed
        self.score = score
        self.details = details
        self.issues = issues


class ContentFactoryService:
    """
    Main service orchestrating the content factory pipeline:
    Topic Selection -> Video Generation -> Quality Gate -> Publishing -> Analytics
    """

    def __init__(
        self,
        db_session: Session,
        mpt_client: MPTClient,
        output_dir: str = "/home/adriel/projects/Rastro/data/mpt/output",
        quality_threshold: int = 70,
        max_concurrent_generations: int = 3,
    ):
        self.db = db_session
        self.mpt = mpt_client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.quality_threshold = quality_threshold
        self.max_concurrent = max_concurrent_generations
        self._generation_semaphore = asyncio.Semaphore(max_concurrent_generations)

    # ========== Topic Bank Management ==========

    def get_next_topics(
        self,
        channel_id: int,
        count: int = 5,
        min_score: int = 50,
    ) -> list[VideoTopic]:
        """Get next topics for generation, ordered by priority and score."""
        from cores.content_factory.models import VideoTopic

        topics = (
            self.db.query(VideoTopic)
            .filter(
                VideoTopic.channel_id == channel_id,
                VideoTopic.status == VideoTopicStatus.ACTIVE,
                VideoTopic.score >= min_score,
            )
            .order_by(
                VideoTopic.priority.desc(),
                VideoTopic.score.desc(),
                VideoTopic.usage_count.asc(),
            )
            .limit(count)
            .all()
        )

        return topics

    def mark_topic_used(self, topic: VideoTopic) -> None:
        """Mark a topic as used, increment counter."""
        topic.usage_count = topic.usage_count + 1  # type: ignore[assignment]
        topic.last_used_at = datetime.utcnow()  # type: ignore[assignment]
        if topic.usage_count >= 3:  # type: ignore[attr-defined]
            topic.status = "exhausted"  # type: ignore[assignment]
        self.db.commit()

    # ========== Video Generation ==========

    async def generate_videos_for_topic(
        self,
        topic: VideoTopic,
        channel: ChannelConfig,
        video_count: int = 3,
    ) -> VideoJob:
        """Generate videos for a specific topic."""
        from cores.content_factory.models import VideoJob

        job = VideoJob(
            channel_id=channel.id,
            topic_id=topic.id,
            status=VideoJobStatus.GENERATING,  # type: ignore[assignment]
            generation_params={
                "video_count": video_count,
                "video_duration": 60,
                "material_source": "pexels",
                "voice_provider": "edge",
            },
            started_at=datetime.utcnow(),
        )
        self.db.add(job)
        self.db.commit()

        try:
            request = VideoGenerationRequest(
                video_subject=str(topic.title),  # type: ignore[arg-type]
                video_count=video_count,
                video_duration=60,
                material_source="pexels",
                voice_provider=VoiceProvider.EDGE,
                subtitle_provider="edge",
            )

            response = await self.mpt.generate_video(request)

            if not response.task_id:
                raise Exception("No task ID returned from MoneyPrinterTurbo")

            job.mpt_job_id = response.task_id  # type: ignore[assignment]
            job.status = VideoJobStatus.GENERATING  # type: ignore[assignment]
            self.db.commit()

            status = await self.mpt.wait_for_completion(response.task_id)

            if status.status == "failed":
                raise Exception(f"Generation failed: {status.error or status.message}")

            job.status = "quality_gate"  # type: ignore[assignment]
            job.video_paths = status.videos  # type: ignore[assignment]
            self.db.commit()

            return job

        except Exception as e:
            job.status = "failed"  # type: ignore[assignment]
            job.error_message = str(e)  # type: ignore[assignment]
            job.error_stage = "generation"  # type: ignore[assignment]
            self.db.commit()
            raise

    # ========== Quality Gate ==========

    def run_quality_gate(self, job: VideoJob) -> QualityGateResult:
        """Run quality checks on generated videos."""
        if not job.video_paths:
            return QualityGateResult(
                passed=False,
                score=0,
                details={},
                issues=["No video files generated"],
            )

        issues = []
        details = {}
        score = 100

        for i, video_path in enumerate(job.video_paths):
            path = Path(video_path)
            video_details = {"path": str(path)}

            if not path.exists():
                issues.append(f"Video {i}: File not found at {video_path}")
                score -= 30
                continue

            size = path.stat().st_size
            video_details["size_bytes"] = size
            if size < 100_000:
                issues.append(f"Video {i}: File too small ({size} bytes)")
                score -= 20

            details[f"video_{i}"] = video_details

        passed = score >= self.quality_threshold and len(issues) == 0

        return QualityGateResult(
            passed=passed,
            score=max(0, score),
            details=details,
            issues=issues,
        )

    # ========== Publishing ==========

    async def publish_to_youtube(
        self,
        job: VideoJob,
        channel: ChannelConfig,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> bool:
        """Publish video to YouTube Shorts."""

        if not job.output_video_path or not Path(job.output_video_path).exists():
            job.error_message = "No output video file to publish"  # type: ignore[assignment]
            job.error_stage = "publishing"  # type: ignore[assignment]
            self.db.commit()
            return False

        job.status = "publishing"  # type: ignore[assignment]
        self.db.commit()

        try:
            if channel.upload_post_api_key:
                return await self._publish_via_upload_post(job, channel)

            if channel.youtube_refresh_token:
                return await self._publish_via_youtube_api(job, channel, title, description, tags)

            job.error_message = "No publishing method configured"  # type: ignore[assignment]
            job.error_stage = "publishing"  # type: ignore[assignment]
            self.db.commit()
            return False

        except Exception as e:
            logger.error(f"Publishing failed: {e}")
            job.error_message = str(e)  # type: ignore[assignment]
            job.error_stage = "publishing"  # type: ignore[assignment]
            self.db.commit()
            return False

    async def _publish_via_upload_post(
        self,
        job: VideoJob,
        channel: ChannelConfig,
    ) -> bool:
        job.status = "published"  # type: ignore[assignment]
        job.published_at = datetime.utcnow()  # type: ignore[assignment]
        self.db.commit()
        return True

    async def _publish_via_youtube_api(
        self,
        job: VideoJob,
        channel: ChannelConfig,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> bool:
        logger.warning("YouTube Data API publishing not fully implemented")
        return False

    # ========== Full Pipeline ==========

    async def run_full_pipeline(
        self,
        channel_id: int,
        topics_count: int = 5,
        videos_per_topic: int = 3,
    ) -> list[VideoJob]:
        """Run the full pipeline: select topics -> generate -> quality gate -> publish."""
        from cores.content_factory.models import ChannelConfig

        channel = self.db.query(ChannelConfig).get(channel_id)
        if not channel:
            raise ValueError(f"Channel {channel_id} not found")

        topics = self.get_next_topics(channel_id, count=topics_count)
        if not topics:
            logger.warning(f"No active topics for channel {channel_id}")
            return []

        jobs = []
        for topic in topics:
            try:
                job = await self.generate_videos_for_topic(topic, channel, videos_per_topic)

                qg_result = self.run_quality_gate(job)
                job.quality_score = qg_result.score  # type: ignore[assignment]
                job.quality_details = qg_result.details  # type: ignore[assignment]
                job.quality_passed = 1 if qg_result.passed else 0  # type: ignore[assignment]
                self.db.commit()

                if not qg_result.passed:
                    logger.warning(f"Job {job.id} failed quality gate: {qg_result.issues}")
                    job.status = VideoJobStatus.FAILED  # type: ignore[assignment]
                    job.error_message = "; ".join(qg_result.issues)  # type: ignore[assignment]
                    job.error_stage = "quality_gate"  # type: ignore[assignment]
                    self.db.commit()
                    continue

                if job.video_paths:
                    job.output_video_path = job.video_paths[0]  # type: ignore[assignment]
                    job.selected_video_index = 0  # type: ignore[assignment]

                await self.publish_to_youtube(job, channel)

                self.mark_topic_used(topic)

                jobs.append(job)

            except Exception as e:
                logger.error(f"Pipeline failed for topic {topic.id}: {e}")
                continue

        return jobs


async def create_content_factory_service(
    db_session: Session, mpt_base_url: str = "http://localhost:8080", **kwargs
) -> ContentFactoryService:
    """Factory function to create ContentFactoryService with MPT client."""

    mpt_client = MPTClient(base_url=mpt_base_url)
    await mpt_client._ensure_client()

    return ContentFactoryService(db_session=db_session, mpt_client=mpt_client, **kwargs)
