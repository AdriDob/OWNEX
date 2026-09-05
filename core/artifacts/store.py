"""Artifact Store — Unified storage for all OWNEX artifacts.

Single source of truth for: evidence, reports, submissions, deliverables, code, etc.
Searchable, versioned, checksummed, mission-linked.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from database.db import Base, SessionLocal

logger = logging.getLogger("ownex.artifacts")


class ArtifactType(StrEnum):
    """Types of artifacts OWNEX produces."""

    EVIDENCE = "evidence"
    REPORT = "report"
    SUBMISSION = "submission"
    DELIVERABLE = "deliverable"
    CODE = "code"
    SCREENSHOT = "screenshot"
    LOG = "log"
    BUNDLE = "bundle"
    METADATA = "metadata"
    OTHER = "other"


@dataclass
class Artifact:
    """Artifact metadata."""

    artifact_id: str
    mission_id: str
    opportunity_id: str | None
    artifact_type: ArtifactType
    name: str
    path: str
    version: int
    checksum: str
    size_bytes: int
    tags: list[str] = field(default_factory=list)
    metadata_json: str = "{}"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "mission_id": self.mission_id,
            "opportunity_id": self.opportunity_id,
            "artifact_type": self.artifact_type.value,
            "name": self.name,
            "path": self.path,
            "version": self.version,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "tags": self.tags,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ArtifactModel(Base):
    """SQLAlchemy model for artifacts."""

    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, index=True)
    artifact_id = Column(String(64), unique=True, nullable=False, index=True)
    mission_id = Column(String(64), nullable=False, index=True)
    opportunity_id = Column(String(64), nullable=True, index=True)
    artifact_type = Column(String(32), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    path = Column(String(512), nullable=False)
    version = Column(Integer, default=1)
    checksum = Column(String(64), nullable=False, index=True)
    size_bytes = Column(Integer, default=0)
    tags_json = Column(Text, default="[]")
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "artifact_id": self.artifact_id,
            "mission_id": self.mission_id,
            "opportunity_id": self.opportunity_id,
            "artifact_type": self.artifact_type,
            "name": self.name,
            "path": self.path,
            "version": self.version,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "tags": json.loads(self.tags_json) if self.tags_json else [],
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ArtifactStore:
    """Unified artifact storage — copies files, computes checksums, versions, searches."""

    def __init__(
        self,
        base_path: str | Path | None = None,
        session_factory: Any = None,
    ) -> None:
        self.base_path = Path(
            base_path or os.environ.get("OWNEX_DATA_DIR") or Path(__file__).resolve().parents[3] / "data" / "artifacts"
        )
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._session_factory = session_factory or SessionLocal

    def _get_session(self):
        return self._session_factory()

    def _checksum(self, file_path: Path) -> str:
        """Compute SHA256 checksum of file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _artifact_path(self, mission_id: str, artifact_type: ArtifactType, name: str) -> Path:
        """Generate storage path for artifact."""
        safe_name = name.replace("/", "_").replace("\\", "_")
        return self.base_path / mission_id / artifact_type.value / safe_name

    def _next_version(self, mission_id: str, artifact_type: ArtifactType, name: str) -> int:
        """Get next version number for artifact."""
        session = self._get_session()
        try:
            latest = (
                session.query(ArtifactModel)
                .filter(
                    ArtifactModel.mission_id == mission_id,
                    ArtifactModel.name == name,
                )
                .order_by(ArtifactModel.version.desc())
                .first()
            )
            return (latest.version + 1) if latest else 1
        finally:
            session.close()

    # ── Store & Retrieve ────────────────────────────────────────

    def store(
        self,
        mission_id: str,
        artifact_type: ArtifactType | str,
        name: str,
        file_path: str | Path,
        opportunity_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict | None = None,
        version: int | None = None,
    ) -> Artifact:
        """Copy file to store, compute checksum, persist metadata."""
        if isinstance(artifact_type, str):
            artifact_type = ArtifactType(artifact_type)

        src = Path(file_path)
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")

        # Compute checksum
        checksum = self._checksum(src)
        size = src.stat().st_size

        # Version
        version = version or self._next_version(mission_id, artifact_type, name)

        # Destination
        dest = self._artifact_path(mission_id, artifact_type, name)
        dest.parent.mkdir(parents=True, exist_ok=True)

        # If same checksum exists, don't copy (dedup)
        session = self._get_session()
        try:
            existing = (
                session.query(ArtifactModel)
                .filter(
                    ArtifactModel.mission_id == mission_id,
                    ArtifactModel.checksum == self._checksum(Path(file_path)),
                )
                .first()
            )
            if existing:
                logger.info(f"[ARTIFACT] Duplicate checksum, reusing: {existing.artifact_id}")
                return Artifact(
                    artifact_id=existing.artifact_id,
                    mission_id=existing.mission_id,
                    opportunity_id=existing.opportunity_id,
                    artifact_type=ArtifactType(existing.artifact_type),
                    name=existing.name,
                    path=existing.path,
                    version=existing.version,
                    checksum=existing.checksum,
                    size_bytes=existing.size_bytes,
                    tags=json.loads(existing.tags_json) if existing.tags_json else [],
                    metadata_json=existing.metadata_json,
                    created_at=existing.created_at.isoformat() if existing.created_at else "",
                    updated_at=existing.updated_at.isoformat() if existing.updated_at else "",
                )
        finally:
            session.close()

        # Copy file
        shutil.copy2(src, dest)
        logger.info(f"[ARTIFACT] Stored {src} -> {dest} (v{version})")

        # Create artifact record
        artifact = Artifact(
            artifact_id=f"art_{mission_id}_{ArtifactType(artifact_type).value}_{name.replace('.', '_')}_{uuid.uuid4().hex[:8]}",
            mission_id=mission_id,
            opportunity_id=opportunity_id,
            artifact_type=artifact_type,
            name=name,
            path=str(dest),
            version=version,
            checksum=self._checksum(src),
            size_bytes=size,
            tags=tags or [],
            metadata_json=json.dumps(metadata or {}),
        )

        # Persist
        session = self._get_session()
        try:
            model = ArtifactModel(
                artifact_id=artifact.artifact_id,
                mission_id=artifact.mission_id,
                opportunity_id=artifact.opportunity_id,
                artifact_type=artifact.artifact_type.value,
                name=artifact.name,
                path=artifact.path,
                version=artifact.version,
                checksum=artifact.checksum,
                size_bytes=artifact.size_bytes,
                tags_json=json.dumps(artifact.tags),
                metadata_json=artifact.metadata_json,
            )
            session.add(model)
            session.commit()
            logger.info(f"[ARTIFACT] Registered {artifact.artifact_id} v{version}")
            return artifact
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get(self, artifact_id: str) -> Artifact | None:
        """Get artifact by ID."""
        session = self._get_session()
        try:
            model = session.query(ArtifactModel).filter(ArtifactModel.artifact_id == artifact_id).first()
            return self._model_to_artifact(model) if model else None
        finally:
            session.close()

    def get_latest(self, mission_id: str, name: str, artifact_type: ArtifactType | str) -> Artifact | None:
        """Get latest version of artifact by name."""
        if isinstance(artifact_type, str):
            artifact_type = ArtifactType(artifact_type)
        session = self._get_session()
        try:
            model = (
                session.query(ArtifactModel)
                .filter(
                    ArtifactModel.mission_id == mission_id,
                    ArtifactModel.name == name,
                    ArtifactModel.artifact_type == artifact_type.value,
                )
                .order_by(ArtifactModel.version.desc())
                .first()
            )
            return self._model_to_artifact(model) if model else None
        finally:
            session.close()

    def get_versions(self, mission_id: str, name: str, artifact_type: ArtifactType | str) -> list[Artifact]:
        """Get all versions of an artifact."""
        if isinstance(artifact_type, str):
            artifact_type = ArtifactType(artifact_type)
        session = self._get_session()
        try:
            models = (
                session.query(ArtifactModel)
                .filter(
                    ArtifactModel.mission_id == mission_id,
                    ArtifactModel.name == name,
                    ArtifactModel.artifact_type == artifact_type.value,
                )
                .order_by(ArtifactModel.version.desc())
                .all()
            )
            return [self._model_to_artifact(m) for m in models]
        finally:
            session.close()

    def get_by_mission(self, mission_id: str, artifact_type: ArtifactType | str | None = None) -> list[Artifact]:
        """Get all artifacts for a mission."""
        if isinstance(artifact_type, str):
            artifact_type = ArtifactType(artifact_type)
        session = self._get_session()
        try:
            query = session.query(ArtifactModel).filter(ArtifactModel.mission_id == mission_id)
            if artifact_type:
                query = query.filter(ArtifactModel.artifact_type == artifact_type.value)
            models = query.order_by(ArtifactModel.created_at.desc()).all()
            return [self._model_to_artifact(m) for m in models]
        finally:
            session.close()

    def search(
        self,
        search_query: str = "",
        mission_id: str | None = None,
        artifact_type: ArtifactType | str | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[Artifact]:
        """Search artifacts by name, tags, or metadata (simple text search)."""
        if isinstance(artifact_type, str):
            artifact_type = ArtifactType(artifact_type)
        session = self._get_session()
        try:
            query = session.query(ArtifactModel)
            if mission_id:
                query = query.filter(ArtifactModel.mission_id == mission_id)
            if artifact_type:
                query = query.filter(ArtifactModel.artifact_type == artifact_type.value)
            if search_query:
                q_lower = search_query.lower()
                query = query.filter(
                    (ArtifactModel.name.ilike(f"%{q_lower}%"))
                    | (ArtifactModel.tags_json.ilike(f"%{q_lower}%"))
                    | (ArtifactModel.metadata_json.ilike(f"%{q_lower}%"))
                )
            if tags:
                for tag in tags:
                    query = query.filter(ArtifactModel.tags_json.ilike(f"%{tag}%"))
            models = query.order_by(ArtifactModel.created_at.desc()).limit(limit).all()
            return [self._model_to_artifact(m) for m in models]
        finally:
            session.close()

    def delete(self, artifact_id: str) -> bool:
        """Delete artifact record and file."""
        session = self._get_session()
        try:
            model = session.query(ArtifactModel).filter(ArtifactModel.artifact_id == artifact_id).first()
            if not model:
                return False
            # Delete file
            try:
                Path(model.path).unlink(missing_ok=True)
            except Exception:
                pass
            session.delete(model)
            session.commit()
            logger.info(f"[ARTIFACT] Deleted {artifact_id}")
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def verify_checksum(self, artifact_id: str) -> bool:
        """Verify file checksum matches stored."""
        artifact = self.get(artifact_id)
        if not artifact:
            return False
        path = Path(artifact.path)
        if not path.exists():
            return False
        return self._checksum(path) == artifact.checksum

    # ── Helpers ────────────────────────────────────────────────

    def _model_to_artifact(self, model: ArtifactModel | None) -> Artifact | None:
        if not model:
            return None
        return Artifact(
            artifact_id=model.artifact_id,
            mission_id=model.mission_id,
            opportunity_id=model.opportunity_id,
            artifact_type=ArtifactType(model.artifact_type),
            name=model.name,
            path=model.path,
            version=model.version,
            checksum=model.checksum,
            size_bytes=model.size_bytes,
            tags=json.loads(model.tags_json) if model.tags_json else [],
            metadata_json=model.metadata_json,
            created_at=model.created_at.isoformat() if model.created_at else "",
            updated_at=model.updated_at.isoformat() if model.updated_at else "",
        )


# ── Singleton ──────────────────────────────────────────────────

_artifact_store: Any | None = None


def get_artifact_store(base_path: str | Path | None = None) -> ArtifactStore:
    global _artifact_store
    if _artifact_store is None:
        _artifact_store = ArtifactStore(base_path)
    return _artifact_store
