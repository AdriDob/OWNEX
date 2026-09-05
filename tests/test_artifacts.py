"""Tests for Artifact Store."""

from __future__ import annotations

import tempfile

import pytest

from core.artifacts.store import (
    ArtifactModel,
    ArtifactStore,
    ArtifactType,
)


@pytest.fixture()
def temp_artifact_store():
    """Provide a clean artifact store with temp directory."""
    from database.db import Base, engine

    # Create temp directory
    temp_dir = tempfile.mkdtemp()

    # Create tables
    Base.metadata.drop_all(bind=engine, tables=[ArtifactModel.__table__])
    Base.metadata.create_all(bind=engine, tables=[ArtifactModel.__table__])

    store = ArtifactStore(base_path=temp_dir)
    yield store

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)
    Base.metadata.drop_all(bind=engine, tables=[ArtifactModel.__table__])


class TestArtifactStore:
    """Tests for ArtifactStore."""

    def test_store_file(self, temp_artifact_store):
        """Test storing a file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_path = f.name

        try:
            artifact = temp_artifact_store.store(
                mission_id="test_mission_1",
                artifact_type=ArtifactType.REPORT,
                name="test_report.txt",
                file_path=temp_path,
                opportunity_id="opp-1",
                tags=["test", "report"],
                metadata={"author": "test"},
            )

            assert artifact.mission_id == "test_mission_1"
            assert artifact.artifact_type == ArtifactType.REPORT
            assert artifact.name == "test_report.txt"
            assert artifact.version == 1
            assert artifact.checksum != ""
            assert artifact.size_bytes > 0
            assert "test" in artifact.tags
            assert artifact.metadata_json is not None
        finally:
            import os

            os.unlink(temp_path)

    def test_get_artifact(self, temp_artifact_store):
        """Test retrieving an artifact by ID."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("get test")
            temp_path = f.name

        try:
            artifact = temp_artifact_store.store(
                mission_id="test_mission_2",
                artifact_type=ArtifactType.EVIDENCE,
                name="evidence.txt",
                file_path=temp_path,
            )

            retrieved = temp_artifact_store.get(artifact.artifact_id)
            assert retrieved is not None
            assert retrieved.artifact_id == artifact.artifact_id
            assert retrieved.name == "evidence.txt"
        finally:
            import os

            os.unlink(temp_path)

    def test_versioning(self, temp_artifact_store):
        """Test artifact versioning."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("version 1")
            temp_path = f.name

        try:
            # Store first version
            v1 = temp_artifact_store.store(
                mission_id="test_mission_3",
                artifact_type=ArtifactType.CODE,
                name="script.py",
                file_path=temp_path,
            )
            assert v1.version == 1

            # Modify file
            with open(temp_path, "w") as f:
                f.write("version 2")

            # Store second version
            v2 = temp_artifact_store.store(
                mission_id="test_mission_3",
                artifact_type=ArtifactType.CODE,
                name="script.py",
                file_path=temp_path,
            )
            assert v2.version == 2

            # Get versions
            versions = temp_artifact_store.get_versions("test_mission_3", "script.py", ArtifactType.CODE)
            assert len(versions) == 2
            assert versions[0].version == 2
            assert versions[1].version == 1
        finally:
            import os

            os.unlink(temp_path)

    def test_get_latest(self, temp_artifact_store):
        """Test getting latest version."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("latest test")
            temp_path = f.name

        try:
            temp_artifact_store.store(
                mission_id="test_mission_4",
                artifact_type=ArtifactType.REPORT,
                name="report.txt",
                file_path=temp_path,
            )

            latest = temp_artifact_store.get_latest("test_mission_4", "report.txt", ArtifactType.REPORT)
            assert latest is not None
            assert latest.version == 1
            assert latest.name == "report.txt"
        finally:
            import os

            os.unlink(temp_path)

    def test_get_by_mission(self, temp_artifact_store):
        """Test getting all artifacts for a mission."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("report content")
            temp_path = f.name

        try:
            temp_artifact_store.store(
                mission_id="test_mission_5",
                artifact_type=ArtifactType.REPORT,
                name="report1.txt",
                file_path=temp_path,
            )

            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
                f.write("evidence content")
                temp_path2 = f.name

            try:
                temp_artifact_store.store(
                    mission_id="test_mission_5",
                    artifact_type=ArtifactType.EVIDENCE,
                    name="evidence.txt",
                    file_path=temp_path2,
                )

                artifacts = temp_artifact_store.get_by_mission("test_mission_5")
                assert len(artifacts) == 2

                # Filter by type
                reports = temp_artifact_store.get_by_mission("test_mission_5", ArtifactType.REPORT)
                assert len(reports) == 1
                assert reports[0].artifact_type == ArtifactType.REPORT
            finally:
                import os

                os.unlink(temp_path2)
        finally:
            import os

            os.unlink(temp_path)

    def test_search(self, temp_artifact_store):
        """Test searching artifacts."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("important finding")
            temp_path = f.name

        try:
            temp_artifact_store.store(
                mission_id="test_mission_6",
                artifact_type=ArtifactType.EVIDENCE,
                name="finding.txt",
                file_path=temp_path,
                tags=["important", "xss"],
                metadata={"severity": "high"},
            )

            # Search by query
            results = temp_artifact_store.search(search_query="important", mission_id="test_mission_6")
            assert len(results) >= 1
            assert any(
                "important" in r.name.lower()
                or "important" in str(r.metadata_json).lower()
                or "important" in str(r.tags).lower()
                for r in results
            )

            # Search by tag
            results = temp_artifact_store.search(tags=["xss"])
            assert len(results) >= 1

            # Search by mission
            results = temp_artifact_store.search(mission_id="test_mission_6")
            assert len(results) >= 1
        finally:
            import os

            os.unlink(temp_path)

    def test_checksum_dedup(self, temp_artifact_store):
        """Test deduplication by checksum."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("duplicate content")
            temp_path = f.name

        try:
            # Store first
            a1 = temp_artifact_store.store(
                mission_id="test_mission_7",
                artifact_type=ArtifactType.REPORT,
                name="dup.txt",
                file_path=temp_path,
            )

            # Store same content again
            a2 = temp_artifact_store.store(
                mission_id="test_mission_7",
                artifact_type=ArtifactType.REPORT,
                name="dup2.txt",
                file_path=temp_path,
            )

            # Should return same artifact (dedup)
            assert a1.artifact_id == a2.artifact_id
        finally:
            import os

            os.unlink(temp_path)

    def test_delete(self, temp_artifact_store):
        """Test deleting an artifact."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("to delete")
            temp_path = f.name

        try:
            artifact = temp_artifact_store.store(
                mission_id="test_mission_8",
                artifact_type=ArtifactType.OTHER,
                name="delete_me.txt",
                file_path=temp_path,
            )
            artifact_id = artifact.artifact_id

            # Delete
            result = temp_artifact_store.delete(artifact_id)
            assert result is True

            # Should not exist
            assert temp_artifact_store.get(artifact_id) is None
        finally:
            import os

            os.unlink(temp_path)

    def test_verify_checksum(self, temp_artifact_store):
        """Test checksum verification."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("verify me")
            temp_path = f.name

        try:
            artifact = temp_artifact_store.store(
                mission_id="test_mission_9",
                artifact_type=ArtifactType.CODE,
                name="verify.py",
                file_path=temp_path,
            )

            # Should verify
            assert temp_artifact_store.verify_checksum(artifact.artifact_id) is True

            # Modify file externally
            with open(artifact.path, "w") as f:
                f.write("modified")

            # Should fail
            assert temp_artifact_store.verify_checksum(artifact.artifact_id) is False
        finally:
            import os

            os.unlink(temp_path)
