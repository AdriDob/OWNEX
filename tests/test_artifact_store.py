"""Tests for the Universal Artifact Store."""

from __future__ import annotations

import hashlib
import tempfile
import pytest

from cores.artifact_store import (
    Artifact,
    ArtifactStore,
    get_artifact_store,
)


@pytest.fixture
def temp_store():
    """Create a temporary artifact store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/artifacts.db"
        storage_dir = f"{tmpdir}/storage"
        store = ArtifactStore(db_path=db_path, storage_dir=storage_dir)
        yield store


def test_store_and_retrieve_artifact(temp_store: ArtifactStore):
    """Test storing and retrieving an artifact."""
    artifact = Artifact(
        type="test",
        name="test_artifact",
        content=b"Hello, World!",
        metadata={"key": "value"},
        tags=["test", "sample"],
    )

    stored = temp_store.store(artifact)

    assert stored.id is not None
    assert stored.content_hash == "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
    assert stored.version == 1

    # Retrieve
    retrieved = temp_store.get(artifact.id)
    assert retrieved is not None
    assert retrieved.id == artifact.id
    assert retrieved.content == b"Hello, World!"
    assert retrieved.metadata == {"key": "value"}
    assert retrieved.tags == ["test", "sample"]


def test_versioning(temp_store: ArtifactStore):
    """Test artifact versioning."""
    artifact = Artifact(
        type="test",
        name="versioned_artifact",
        content=b"v1 content",
        metadata={"version": 1},
    )

    # Store initial version
    v1 = temp_store.store(artifact)
    assert v1.version == 1

    # Create new version
    artifact.content = b"v2 content"
    artifact.metadata = {"version": 2}
    v2 = temp_store.store(artifact)
    assert v2.version == 2
    assert v2.previous_version_id == artifact.id

    # Retrieve specific version
    v1_retrieved = temp_store.get(artifact.id, version=1)
    assert v1_retrieved.content == b"v1 content"

    v2_retrieved = temp_store.get(artifact.id, version=2)
    assert v2_retrieved.content == b"v2 content"

    # Get all versions
    versions = temp_store.get_versions(artifact.id)
    assert len(versions) == 2
    assert versions[0]["version"] == 1
    assert versions[1]["version"] == 2


def test_content_addressable_lookup(temp_store: ArtifactStore):
    """Test content-addressable lookup by hash."""
    content = b"unique content for hash test"
    artifact = Artifact(
        type="test",
        name="hash_test",
        content=content,
    )

    temp_store.store(artifact)
    hash_value = hashlib.sha256(content).hexdigest()

    # Lookup by hash
    found = temp_store.get_by_hash(hash_value)
    assert found is not None
    assert found.id == artifact.id


def test_full_text_search(temp_store: ArtifactStore):
    """Test full-text search."""
    artifact1 = Artifact(
        type="test",
        name="python_script",
        content=b"import python script",
        tags=["python", "script"],
    )
    artifact2 = Artifact(
        type="test",
        name="javascript_code",
        content=b"const js = 'javascript'",
        tags=["javascript", "code"],
    )
    artifact3 = Artifact(
        type="other",
        name="data_file",
        content=b"just data",
        tags=["data"],
    )

    temp_store.store(artifact1)
    temp_store.store(artifact2)
    temp_store.store(artifact3)

    # Search by text
    results = temp_store.search("python")
    assert len(results) == 1
    assert results[0].name == "python_script"

    # Search by tag
    results = temp_store.search("javascript")
    assert len(results) == 1
    assert results[0].name == "javascript_code"

    # Search with type filter
    results = temp_store.search("data", artifact_type="test")
    assert len(results) == 0  # data_file is type "other"

    results = temp_store.search("data", artifact_type="other")
    assert len(results) == 1
    assert results[0].name == "data_file"


def test_get_by_type(temp_store: ArtifactStore):
    """Test filtering by type."""
    artifact1 = Artifact(type="test", name="a", content=b"a")
    artifact2 = Artifact(type="test", name="b", content=b"b")
    artifact3 = Artifact(type="other", name="c", content=b"c")

    temp_store.store(artifact1)
    temp_store.store(artifact2)
    temp_store.store(artifact3)

    test_artifacts = temp_store.get_by_type("test")
    assert len(test_artifacts) == 2

    other_artifacts = temp_store.get_by_type("other")
    assert len(other_artifacts) == 1


def test_delete(temp_store: ArtifactStore):
    """Test artifact deletion."""
    artifact = Artifact(type="test", name="to_delete", content=b"delete me")
    temp_store.store(artifact)

    assert temp_store.get(artifact.id) is not None
    assert temp_store.delete(artifact.id) is True
    assert temp_store.get(artifact.id) is None


def test_stats(temp_store: ArtifactStore):
    """Test storage statistics."""
    artifact1 = Artifact(type="test", name="a", content=b"a")
    artifact2 = Artifact(type="test", name="b", content=b"b")
    artifact3 = Artifact(type="other", name="c", content=b"c")

    temp_store.store(artifact1)
    temp_store.store(artifact2)
    temp_store.store(artifact3)

    stats = temp_store.get_stats()
    assert stats["total_artifacts"] == 3
    assert stats["by_type"]["test"] == 2
    assert stats["by_type"]["other"] == 1
    assert stats["storage_bytes"] > 0


def test_singleton():
    """Test that get_artifact_store returns singleton."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/artifacts.db"
        storage_dir = f"{tmpdir}/storage"

        store1 = get_artifact_store(db_path, "/tmp/storage1")
        store2 = get_artifact_store(db_path, "/tmp/storage2")

        assert store1 is store2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
