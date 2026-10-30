"""Universal Artifact Store — Versioned, searchable, hash-verified artifact storage.

Provides a unified storage layer for all artifacts with:
- Content-addressable storage (SHA-256)
- Versioned artifacts with immutable history
- Full-text search via SQLite FTS5
- Metadata indexing for fast queries
- Immutable audit trail
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger("artifact_store")


@dataclass(slots=True)
class Artifact:
    """Universal artifact with versioning and content-addressable storage."""

    id: str = field(default_factory=lambda: uuid4().hex[:16])
    type: str = ""  # e.g., "pipeline", "evidence", "execution", "finding"
    name: str = ""
    content: bytes = b""
    content_hash: str = ""
    version: int = 1
    previous_version_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    created_by: str = "system"

    def __post_init__(self):
        if not self.content_hash and self.content:
            self.content_hash = hashlib.sha256(self.content).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Don't store raw bytes in dict
        d.pop("content", None)
        return d

    @property
    def size(self) -> int:
        return len(self.content)


@dataclass(slots=True)
class ArtifactVersion:
    """A specific version of an artifact."""

    artifact_id: str
    version: int
    content_hash: str
    content: bytes
    metadata: dict[str, Any]
    created_at: str
    created_by: str


class ArtifactStore:
    """Universal Artifact Store with versioning, search, and content-addressable storage."""

    def __init__(self, db_path: str | None = None, storage_dir: str | None = None):
        self.db_path = db_path or os.path.join(Path.home(), ".ownex", "artifacts.db")
        self.storage_dir = Path(storage_dir or os.path.join(Path.home(), ".ownex", "artifacts"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_conn() as conn:
            # Artifacts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    previous_version_id TEXT,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    tags TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    created_by TEXT NOT NULL DEFAULT 'system',
                    FOREIGN KEY (previous_version_id) REFERENCES artifacts(id)
                )
            """)

            # Artifact versions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS artifact_versions (
                    id TEXT PRIMARY KEY,
                    artifact_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    content_hash TEXT NOT NULL,
                    content BLOB NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    FOREIGN KEY (artifact_id) REFERENCES artifacts(id)
                )
            """)

            # FTS5 search index
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS artifacts_fts USING fts5(
                    id UNINDEXED,
                    type,
                    name,
                    metadata,
                    tags,
                    content='artifacts',
                    content_rowid='rowid'
                )
            """)

            # Triggers to keep FTS in sync
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS artifacts_ai AFTER INSERT ON artifacts BEGIN
                    INSERT INTO artifacts_fts (rowid, type, name, metadata, tags)
                    VALUES (new.rowid, new.type, new.name, new.metadata, new.tags);
                END
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS artifacts_ad AFTER DELETE ON artifacts BEGIN
                    DELETE FROM artifacts_fts WHERE rowid = old.rowid;
                END
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS artifacts_au AFTER UPDATE ON artifacts BEGIN
                    DELETE FROM artifacts_fts WHERE rowid = old.rowid;
                    INSERT INTO artifacts_fts (rowid, type, name, metadata, tags)
                    VALUES (new.rowid, new.type, new.name, new.metadata, new.tags);
                END
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_name ON artifacts(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_hash ON artifacts(content_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_type_name ON artifacts(type, name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_versions_artifact ON artifact_versions(artifact_id, version)")

            conn.commit()

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _compute_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def store(self, artifact: Artifact) -> Artifact:
        """Store a new artifact or new version of existing artifact."""
        content_hash = artifact.content_hash or self._compute_hash(artifact.content)
        artifact.content_hash = content_hash

        with self._get_conn() as conn:
            # Check if artifact with same hash exists
            existing = conn.execute("SELECT id FROM artifacts WHERE content_hash = ?", (content_hash,)).fetchone()

            if existing:
                # Create new version of existing artifact
                existing_id = existing["id"]
                return self._create_version(existing_id, artifact)

            # New artifact
            artifact_id = artifact.id
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO artifacts (id, type, name, content_hash, version, previous_version_id,
                                         metadata, tags, created_at, updated_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        artifact_id,
                        artifact.type,
                        artifact.name,
                        artifact.content_hash,
                        artifact.version,
                        artifact.previous_version_id,
                        json.dumps(artifact.metadata),
                        json.dumps(artifact.tags),
                        artifact.created_at,
                        artifact.updated_at,
                        artifact.created_by,
                    ),
                )

                # Store content in filesystem (not in DB)
                content_path = self.storage_dir / f"{artifact_id}_v{artifact.version}"
                content_path.write_bytes(artifact.content)

                # Create initial version record
                version_id = uuid4().hex[:16]
                conn.execute(
                    """
                    INSERT INTO artifact_versions (id, artifact_id, version, content_hash, content, metadata, created_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        version_id,
                        artifact_id,
                        artifact.version,
                        artifact.content_hash,
                        artifact.content,
                        json.dumps(artifact.metadata),
                        artifact.created_at,
                        artifact.created_by,
                    ),
                )

                conn.commit()
                return artifact

    def _create_version(self, artifact_id: str, artifact: Artifact) -> Artifact:
        """Create a new version of an existing artifact."""
        with self._get_conn() as conn:
            # Get current version
            row = conn.execute(
                "SELECT MAX(version) FROM artifact_versions WHERE artifact_id = ?",
                (artifact_id,),
            ).fetchone()
            current_version = row[0] if row and row[0] else 0
            new_version = current_version + 1

            artifact.version = new_version
            artifact.previous_version_id = artifact.id
            artifact.content_hash = artifact.content_hash or self._compute_hash(artifact.content)
            artifact.updated_at = datetime.now(UTC).isoformat()

            # Update artifact record
            conn.execute(
                """
                UPDATE artifacts SET version = ?, updated_at = ?, metadata = ?, tags = ?
                WHERE id = ?
                """,
                (
                    new_version,
                    artifact.updated_at,
                    json.dumps(artifact.metadata),
                    json.dumps(artifact.tags),
                    artifact_id,
                ),
            )

            # Store new content
            content_path = self.storage_dir / f"{artifact.id}_v{new_version}"
            content_path.write_bytes(artifact.content)

            # Create version record
            version_id = uuid4().hex[:16]
            conn.execute(
                """
                INSERT INTO artifact_versions (id, artifact_id, version, content_hash, content, metadata, created_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid4().hex[:16],
                    artifact.id,
                    new_version,
                    artifact.content_hash,
                    artifact.content,
                    json.dumps(artifact.metadata),
                    artifact.updated_at,
                    artifact.created_by,
                ),
            )

            conn.commit()
            return artifact

    def get(self, artifact_id: str, version: int | None = None) -> Artifact | None:
        """Retrieve an artifact by ID and optional version."""
        with self._get_conn() as conn:
            if version is None:
                row = conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT a.*, av.content, av.metadata as version_metadata
                    FROM artifacts a
                    JOIN artifact_versions av ON a.id = av.artifact_id
                    WHERE a.id = ? AND av.version = ?
                    """,
                    (artifact_id, version),
                ).fetchone()

            if not row:
                return None

            return self._row_to_artifact(row)

    def _row_to_artifact(self, row: sqlite3.Row) -> Artifact:
        """Convert database row to Artifact."""
        artifact = Artifact(
            id=row["id"],
            type=row["type"],
            name=row["name"],
            content_hash=row["content_hash"],
            version=row["version"],
            previous_version_id=row["previous_version_id"] if "previous_version_id" in row.keys() else None,
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            tags=json.loads(row["tags"]) if row["tags"] else [],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=row["created_by"] if "created_by" in row.keys() else "system",
        )
        # Load content from filesystem
        if "content" in row.keys() and row["content"] is not None:
            artifact.content = row["content"]
        else:
            content_path = self.storage_dir / f"{artifact.id}_v{artifact.version}"
            if content_path.exists():
                artifact.content = content_path.read_bytes()
        return artifact

    def search(self, query: str, limit: int = 20, artifact_type: str | None = None) -> list[Artifact]:
        """Full-text search across artifacts."""
        with self._get_conn() as conn:
            if artifact_type:
                rows = conn.execute(
                    """
                    SELECT a.* FROM artifacts a
                    JOIN artifacts_fts fts ON a.rowid = fts.rowid
                    WHERE artifacts_fts MATCH ? AND a.type = ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (query, artifact_type, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT a.* FROM artifacts a
                    JOIN artifacts_fts fts ON a.rowid = fts.rowid
                    WHERE artifacts_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (query, limit),
                ).fetchall()

            return [self._row_to_artifact(row) for row in rows]

    def get_by_type(self, artifact_type: str, limit: int = 100) -> list[Artifact]:
        """Get all artifacts of a specific type."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM artifacts WHERE type = ? ORDER BY updated_at DESC LIMIT ?",
                (artifact_type, limit),
            ).fetchall()
            return [self._row_to_artifact(row) for row in rows]

    def get_by_hash(self, content_hash: str) -> Artifact | None:
        """Get artifact by content hash (content-addressable lookup)."""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM artifacts WHERE content_hash = ?", (content_hash,)).fetchone()
            return self._row_to_artifact(row) if row else None

    def get_versions(self, artifact_id: str) -> list[dict]:
        """Get all versions of an artifact."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, version, content_hash, created_at, created_by FROM artifact_versions WHERE artifact_id = ? ORDER BY version",
                (artifact_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def delete(self, artifact_id: str) -> bool:
        """Delete an artifact and all its versions."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM artifact_versions WHERE artifact_id = ?", (artifact_id,))
            conn.execute("DELETE FROM artifacts WHERE id = ?", (artifact_id,))
            conn.commit()
            return True

    def get_stats(self) -> dict:
        """Get storage statistics."""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
            versions = conn.execute("SELECT COUNT(*) FROM artifact_versions").fetchone()[0]
            types = conn.execute("SELECT type, COUNT(*) FROM artifacts GROUP BY type").fetchall()

            # Calculate storage size
            total_size = sum(f.stat().st_size for f in self.storage_dir.glob("*") if f.is_file())

            return {
                "total_artifacts": total,
                "total_versions": versions,
                "by_type": dict(types),
                "storage_bytes": total_size,
                "storage_mb": round(total_size / (1024 * 1024), 2),
            }


# Global instance
_artifact_store: ArtifactStore | None = None


def get_artifact_store(db_path: str | None = None, storage_dir: str | None = None) -> ArtifactStore:
    """Get or create the global artifact store."""
    global _artifact_store
    if _artifact_store is None:
        _artifact_store = ArtifactStore(db_path, storage_dir)
    return _artifact_store
