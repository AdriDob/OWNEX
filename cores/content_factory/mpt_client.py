"""MoneyPrinterTurbo API Client - HTTP client for MoneyPrinterTurbo API with retry logic."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import httpx

logger = logging.getLogger("ownex.content_factory.mpt_client")


def _default_mpt_base_url() -> str:
    """MPT sidecar URL. Env MPT_BASE_URL wins; default :8081 (:8080 is Open WebUI here)."""
    import os

    return os.environ.get("MPT_BASE_URL", "http://127.0.0.1:8081").rstrip("/")


class MPTError(Exception):
    """Base exception for MoneyPrinterTurbo client errors."""

    def __init__(self, message: str, status_code: int | None = None, response: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class MPTConnectionError(MPTError):
    """Connection/connection timeout error."""

    pass


class MPTAPIError(MPTError):
    """API returned an error response."""

    pass


class MPTJobStatus(StrEnum):
    """MoneyPrinterTurbo job statuses (OWNEX view)."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def _mpt_state_to_status(state: Any) -> MPTJobStatus:
    """Map MPT v1.3.6 integer task state to OWNEX status.

    Upstream consts: FAILED=-1, COMPLETE=1, PROCESSING=4.
    Anything else (0/queued/unknown) is honestly PENDING.
    """
    try:
        code = int(state)
    except (TypeError, ValueError):
        return MPTJobStatus.PENDING
    if code == 1:
        return MPTJobStatus.COMPLETED
    if code == -1:
        return MPTJobStatus.FAILED
    if code == 4:
        return MPTJobStatus.RUNNING
    return MPTJobStatus.PENDING


def _envelope_data(payload: Any) -> dict[str, Any]:
    """Unwrap MPT v1 envelope {status, message, data} (or legacy flat)."""
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload if isinstance(payload, dict) else {}


class VideoAspect(StrEnum):
    PORTRAIT = "9:16"
    LANDSCAPE = "16:9"


class MaterialSource(StrEnum):
    PEXELS = "pexels"
    PIXABAY = "pixabay"
    COVERR = "coverr"
    LOCAL = "local"
    WAVESPEED = "wavespeed"


class VoiceProvider(StrEnum):
    EDGE = "edge"
    ELEVENLABS = "elevenlabs"
    AZURE_V1 = "azure_v1"
    AZURE_V2 = "azure_v2"
    SILICONFLOW = "siliconflow"
    GEMINI = "gemini"
    XIAOMI_MIMO = "xiaomi_mimo"
    CHATTERBOX = "chatterbox"
    FISH_AUDIO = "fish_audio"


class SubtitleProvider(StrEnum):
    EDGE = "edge"
    WHISPER = "whisper"


@dataclass
class VideoGenerationRequest:
    """Request payload for video generation."""

    video_subject: str
    video_aspect: VideoAspect = VideoAspect.PORTRAIT
    video_duration: int = 60
    video_count: int = 3
    video_concat_mode: str = "random"
    # Legacy script knobs (kept for backward compat). MPT v1.3.6 resolves the
    # LLM server-side via config.toml (llm_provider); these are NOT sent.
    script_generator: str = "ollama"
    script_model: str = "qwen2.5:3b-instruct"
    paragraph_count: int = 3
    voice_provider: VoiceProvider = VoiceProvider.EDGE
    voice_name: str = "en-US-GuyNeural"
    voice_speed: float = 1.1
    subtitle_provider: SubtitleProvider = SubtitleProvider.EDGE
    subtitle_position: str = "bottom"
    subtitle_font_size: int = 60
    subtitle_color: str = "white"
    subtitle_stroke: str = "black"
    material_source: MaterialSource = MaterialSource.PEXELS
    background_music: str | None = None
    background_music_volume: float = 0.3
    transition_enabled: bool = True
    transition_duration: float = 0.3
    ken_burns_enabled: bool = True
    video_quality: str = "high"

    def to_mpt_params(self) -> dict[str, Any]:
        """Convert to MoneyPrinterTurbo API v1 parameters.

        Field names follow MPT v1.3.6 VideoParams (TaskVideoRequest).
        Server-side config.toml governs LLM/TTS providers; only
        generation knobs travel here.
        """

        def _val(value: Any) -> Any:
            return getattr(value, "value", value)

        def _hex(color: Any) -> Any:
            table = {
                "white": "#FFFFFF",
                "black": "#000000",
                "yellow": "#FFFF00",
                "red": "#FF0000",
                "blue": "#0000FF",
                "green": "#00FF00",
            }
            if isinstance(color, str) and not color.startswith("#"):
                return table.get(color.lower(), color)
            return color

        return {
            "video_subject": self.video_subject,
            "video_aspect": _val(self.video_aspect),
            "video_clip_duration": 3,
            "video_count": self.video_count,
            "video_concat_mode": self.video_concat_mode,
            "video_source": _val(self.material_source),
            "voice_name": self.voice_name,
            "voice_rate": self.voice_speed,
            "bgm_type": "random",
            "bgm_volume": self.background_music_volume,
            "subtitle_enabled": True,
            "subtitle_position": self.subtitle_position,
            "font_size": self.subtitle_font_size,
            "text_fore_color": _hex(self.subtitle_color),
            "stroke_color": _hex(self.subtitle_stroke),
            "stroke_width": 1.5,
            "paragraph_number": self.paragraph_count,
        }


@dataclass
class VideoGenerationResponse:
    """Response from video generation API."""

    task_id: str
    status: MPTJobStatus
    message: str | None = None
    videos: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class JobStatusResponse:
    """Job status response."""

    task_id: str
    status: MPTJobStatus
    progress: int = 0
    message: str | None = None
    videos: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


@dataclass
class HealthResponse:
    """Health check response."""

    status: str
    version: str | None = None
    components: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class MPTClient:
    """
    Async HTTP client for MoneyPrinterTurbo API.

    Features:
    - Automatic retry with exponential backoff
    - Health checks
    - Job polling with callbacks
    - Timeout management
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 300.0,
        max_retries: int = 3,
        base_backoff: float = 1.0,
        max_backoff: float = 60.0,
    ):
        self.base_url = (base_url or _default_mpt_base_url()).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff
        self._client: httpx.AsyncClient | None = None
        self._health_cache: HealthResponse | None = None
        self._health_cache_ttl: float = 30.0  # seconds
        self._health_cache_time: float = 0.0

    async def __aenter__(self) -> MPTClient:
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
                headers={"User-Agent": "OWNEX-ContentFactory/1.0"},
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _build_url(self, path: str) -> str:
        """Build full URL from path."""
        return f"{self.base_url}{path}"

    async def _request_with_retry(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make HTTP request with retry logic."""
        await self._ensure_client()

        client = self._client
        assert client is not None, "HTTP client not initialized"

        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await client.request(method, path, **kwargs)

                if response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = float(response.headers.get("Retry-After", self.base_backoff * (2**attempt)))
                    logger.warning(f"Rate limited, waiting {retry_after}s before retry {attempt + 1}")
                    await asyncio.sleep(min(retry_after, self.max_backoff))
                    continue

                if 500 <= response.status_code < 600:
                    # Server error - retry
                    if attempt < self.max_retries:
                        backoff = min(self.base_backoff * (2**attempt), self.max_backoff)
                        logger.warning(
                            f"Server error {response.status_code}, retrying in {backoff}s (attempt {attempt + 1})"
                        )
                        await asyncio.sleep(backoff)
                        continue
                    raise MPTAPIError(
                        f"Server error: {response.status_code}",
                        status_code=response.status_code,
                        response=response.json()
                        if response.headers.get("content-type", "").startswith("application/json")
                        else None,
                    )

                return response

            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                last_exception = MPTConnectionError(f"Connection failed: {e}")
                if attempt < self.max_retries:
                    backoff = min(self.base_backoff * (2**attempt), self.max_backoff)
                    logger.warning(f"Connection failed, retrying in {backoff}s (attempt {attempt + 1})")
                    await asyncio.sleep(backoff)
                    continue
                raise

            except httpx.TimeoutException as e:
                last_exception = MPTConnectionError(f"Request timeout: {e}")
                if attempt < self.max_retries:
                    backoff = min(self.base_backoff * (2**attempt), self.max_backoff)
                    logger.warning(f"Request timeout, retrying in {backoff}s (attempt {attempt + 1})")
                    await asyncio.sleep(backoff)
                    continue
                raise

        # If we exhausted retries
        raise last_exception or MPTError("Max retries exceeded")

    # ========== Health & Status ==========

    async def health_check(self, force: bool = False) -> HealthResponse:
        """Check API health with caching.

        MPT v1.3.6 exposes no /health route (stale compose healthcheck);
        liveness = GET /api/v1/tasks reachable (200).
        """
        now = time.time()
        if not force and self._health_cache and (now - self._health_cache_time) < self._health_cache_ttl:
            return self._health_cache

        try:
            response = await self._request_with_retry("GET", "/api/v1/tasks", params={"page_size": 1})
            if response.status_code == 200:
                health = HealthResponse(status="healthy", components={"api": "v1"})
                self._health_cache = health
                self._health_cache_time = time.time()
                return health
        except Exception as e:
            logger.warning(f"Health check failed: {e}")

        # Return degraded status
        health = HealthResponse(status="degraded")
        self._health_cache = health
        self._health_cache_time = time.time()
        return health

    async def is_healthy(self) -> bool:
        """Quick health check."""
        health = await self.health_check()
        return health.status == "healthy"

    async def wait_for_healthy(self, timeout: float = 120.0, interval: float = 5.0) -> bool:
        """Wait for service to become healthy."""
        start = time.time()
        while time.time() - start < timeout:
            if await self.is_healthy():
                return True
            await asyncio.sleep(interval)
        return False

    # ========== Video Generation ==========

    async def generate_video(self, request: VideoGenerationRequest) -> VideoGenerationResponse:
        """Submit a video generation job (POST /api/v1/videos)."""
        response = await self._request_with_retry(
            "POST",
            "/api/v1/videos",
            json=request.to_mpt_params(),
        )

        if response.status_code not in (200, 201, 202):
            raise MPTAPIError(
                f"Generation failed: {response.status_code}",
                status_code=response.status_code,
                response=response.json()
                if response.headers.get("content-type", "").startswith("application/json")
                else None,
            )

        data = _envelope_data(response.json())
        return VideoGenerationResponse(
            task_id=data.get("task_id", ""),
            status=MPTJobStatus.PENDING,
            message=data.get("message"),
            videos=data.get("videos", []),
        )

    async def generate_batch(
        self,
        subjects: list[str],
        base_params: VideoGenerationRequest | None = None,
    ) -> list[VideoGenerationResponse]:
        """Generate multiple videos in parallel."""
        if base_params is None:
            base_params = VideoGenerationRequest(video_subject="")

        tasks = []
        for subject in subjects:
            params = VideoGenerationRequest(**{**base_params.__dict__, "video_subject": subject})
            tasks.append(self.generate_video(params))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        results_list = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch generation failed for '{subjects[i]}': {result}")
                results_list.append(
                    VideoGenerationResponse(
                        task_id="",
                        status=MPTJobStatus.FAILED,
                        message=str(result),
                    )
                )
            else:
                results_list.append(result)
        return results_list

    # ========== Job Management ==========

    async def get_job_status(self, task_id: str) -> JobStatusResponse:
        """Get job status by task ID (GET /api/v1/tasks/{id})."""
        response = await self._request_with_retry("GET", f"/api/v1/tasks/{task_id}")

        if response.status_code == 404:
            raise MPTAPIError(f"Job not found: {task_id}", status_code=404)

        if response.status_code != 200:
            raise MPTAPIError(
                f"Status check failed: {response.status_code}",
                status_code=response.status_code,
            )

        data = _envelope_data(response.json())
        videos = data.get("videos") or []
        if not videos and data.get("combined_videos"):
            videos = data["combined_videos"]
        return JobStatusResponse(
            task_id=data.get("task_id", task_id),
            status=_mpt_state_to_status(data.get("state")),
            progress=data.get("progress", 0),
            message=data.get("failed_stage"),
            videos=videos,
            error=data.get("error"),
        )

    async def wait_for_completion(
        self,
        task_id: str,
        timeout: float = 600.0,
        poll_interval: float = 5.0,
        progress_callback: Callable[[JobStatusResponse], None] | None = None,
    ) -> JobStatusResponse:
        """Poll job until completion or timeout."""
        start = time.time()
        while time.time() - start < timeout:
            status = await self.get_job_status(task_id)

            if progress_callback:
                progress_callback(status)

            if status.status in (MPTJobStatus.COMPLETED, MPTJobStatus.FAILED):
                return status

            await asyncio.sleep(poll_interval)

        raise MPTConnectionError(f"Job {task_id} timed out after {timeout}s")

    async def cancel_job(self, task_id: str) -> bool:
        """Delete a task (MPT v1.3.6 exposes no cancel — DELETE removes it)."""
        response = await self._request_with_retry("DELETE", f"/api/v1/tasks/{task_id}")
        return response.status_code in (200, 202, 204)

    async def list_jobs(
        self,
        status: MPTJobStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[JobStatusResponse]:
        """List jobs with optional filtering (GET /api/v1/tasks).

        v1 has no server-side status filter; filtering happens client-side.
        """
        page = offset // max(limit, 1) + 1
        response = await self._request_with_retry("GET", "/api/v1/tasks", params={"page": page, "page_size": limit})

        if response.status_code != 200:
            raise MPTAPIError(f"List jobs failed: {response.status_code}")

        data = _envelope_data(response.json())
        jobs = data.get("tasks", [])

        out: list[JobStatusResponse] = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            mapped = _mpt_state_to_status(job.get("state"))
            if status is not None and mapped != status:
                continue
            videos = job.get("videos") or job.get("combined_videos") or []
            out.append(
                JobStatusResponse(
                    task_id=job.get("task_id", ""),
                    status=mapped,
                    progress=job.get("progress", 0),
                    message=job.get("failed_stage"),
                    videos=videos,
                    error=job.get("error"),
                )
            )
        return out

    # ========== Video Files ==========

    async def get_video_file(self, task_id: str, video_index: int = 0) -> bytes:
        """Download a generated video file (via the static /tasks mount)."""
        status = await self.get_job_status(task_id)
        if not status.videos or video_index >= len(status.videos):
            raise MPTAPIError(f"Video file not found: {task_id}[{video_index}]", status_code=404)
        url = self._resolve_media_url(self.base_url, task_id, status.videos[video_index])
        await self._ensure_client()
        assert self._client is not None
        response = await self._client.get(url, timeout=httpx.Timeout(300.0))
        if response.status_code == 404:
            raise MPTAPIError(f"Video file not found: {task_id}[{video_index}]", status_code=404)
        response.raise_for_status()
        return response.content

    @staticmethod
    def _resolve_media_url(base_url: str, task_id: str, entry: Any) -> str:
        """Resolve an MPT videos[] entry to a downloadable URL.

        v1.3.6 already returns absolute or /tasks-relative URIs.
        """
        if not isinstance(entry, str) or not entry:
            raise MPTAPIError(f"Empty video entry for task {task_id}", status_code=404)
        if entry.startswith(("http://", "https://")):
            return entry
        if entry.startswith("/"):
            return f"{base_url}{entry}"
        return f"{base_url}/tasks/{task_id}/{entry}"

    async def get_video_url(self, task_id: str, video_index: int = 0) -> str:
        """Get direct URL to video file (served from the static /tasks mount)."""
        status = await self.get_job_status(task_id)
        if not status.videos or video_index >= len(status.videos):
            raise MPTAPIError(f"Video file not found: {task_id}[{video_index}]", status_code=404)
        return self._resolve_media_url(self.base_url, task_id, status.videos[video_index])

    # ========== Configuration ==========

    async def get_config(self) -> dict[str, Any]:
        """Get current configuration (NOT exposed by MPT v1.3.6 API)."""
        raise MPTAPIError("MPT v1.3.6 exposes no /api/config route — edit config.toml directly")

    async def update_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Update configuration (NOT exposed by MPT v1.3.6 API)."""
        raise MPTAPIError("MPT v1.3.6 exposes no /api/config route — edit config.toml directly")

    # ========== Utility ==========

    async def test_generation(self, subject: str = "test video") -> bool:
        """Quick test generation to verify API works."""
        try:
            request = VideoGenerationRequest(
                video_subject=subject,
                video_count=1,
                video_duration=10,
            )
            result = await self.generate_video(request)
            return bool(result.task_id)
        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            return False


# Convenience factory
async def create_mpt_client(base_url: str | None = None, **kwargs) -> MPTClient:
    """Create and initialize MPT client."""
    client = MPTClient(base_url=base_url, **kwargs)
    await client._ensure_client()
    return client
