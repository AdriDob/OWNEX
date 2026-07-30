from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Session

from cores.knowledge.abstracts import KnowledgeSourceInfo, KnowledgeStore
from database.db import Base

logger = logging.getLogger("ownex.knowledge.store")


class KnowledgeSourceModel(Base):
    __tablename__ = "knowledge_sources"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    homepage = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    version = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP")


class KnowledgeArtifactModel(Base):
    __tablename__ = "knowledge_artifacts"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    content_type = Column(String, nullable=False)
    body = Column(Text, nullable=True)
    canonical_entities = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP")
    updated_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP")
    version = Column(Integer, default=1)
    fingerprint = Column(String, nullable=True, index=True)
    dedup_source_ids = Column(JSON, nullable=True)


class KnowledgeRelationshipModel(Base):
    __tablename__ = "knowledge_relationships"

    id = Column(String, primary_key=True, index=True)
    source_artifact_id = Column(String, nullable=False, index=True)
    target_artifact_id = Column(String, nullable=False, index=True)
    relation_type = Column(String, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP")
    updated_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP")


class SqlAlchemyKnowledgeStore(KnowledgeStore):
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_source(self, source: KnowledgeSourceInfo) -> str:
        source_id = source.metadata.get("source_id") if source.metadata else None
        source_id = source_id or source.name or str(uuid.uuid4())
        db_source = KnowledgeSourceModel(
            id=source_id,
            name=source.name,
            provider=source.provider,
            source_type=source.source_type,
            homepage=source.homepage,
            description=source.description,
            version=source.version,
            metadata_json=source.metadata or {},
        )
        self.session.merge(db_source)
        self.session.commit()
        return source_id

    def save_artifact(self, artifact: dict[str, Any]) -> str:
        artifact_id = artifact.get("artifact_id") or str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        model = KnowledgeArtifactModel(
            id=artifact_id,
            title=artifact.get("title", "untitled"),
            summary=artifact.get("summary"),
            description=artifact.get("description"),
            content_type=artifact.get("content_type", "other"),
            body=artifact.get("body"),
            canonical_entities=artifact.get("canonical_entities", []),
            metadata_json=artifact.get("metadata", {}),
            created_at=artifact.get("created_at", now),
            updated_at=artifact.get("updated_at", now),
            version=artifact.get("version", 1),
            fingerprint=artifact.get("fingerprint"),
            dedup_source_ids=artifact.get("dedup_source_ids", []),
        )
        self.session.merge(model)
        self.session.commit()
        return artifact_id

    def save_relationship(self, relation: dict[str, Any]) -> str:
        relation_id = relation.get("relation_id") or str(uuid.uuid4())
        model = KnowledgeRelationshipModel(
            id=relation_id,
            source_artifact_id=relation["source_artifact_id"],
            target_artifact_id=relation["target_artifact_id"],
            relation_type=relation["relation_type"],
            metadata_json=relation.get("metadata", {}),
            confidence=relation.get("confidence", 0.0),
        )
        self.session.merge(model)
        self.session.commit()
        return relation_id

    def find_artifacts(self, fingerprint: str) -> list[dict[str, Any]]:
        rows = self.session.query(KnowledgeArtifactModel).filter(KnowledgeArtifactModel.fingerprint == fingerprint).all()
        results = []
        for row in rows:
            results.append({
                "artifact_id": row.id,
                "title": row.title,
                "summary": row.summary,
                "description": row.description,
                "content_type": row.content_type,
                "body": row.body,
                "canonical_entities": row.canonical_entities,
                "metadata": row.metadata_json,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "version": row.version,
                "fingerprint": row.fingerprint,
                "dedup_source_ids": row.dedup_source_ids,
            })
        return results

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        row = self.session.query(KnowledgeArtifactModel).filter(KnowledgeArtifactModel.id == artifact_id).first()
        if not row:
            return None
        result = {
            "artifact_id": row.id,
            "title": row.title,
            "summary": row.summary,
            "description": row.description,
            "content_type": row.content_type,
            "body": row.body,
            "canonical_entities": row.canonical_entities,
            "metadata": row.metadata_json,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "version": row.version,
            "fingerprint": row.fingerprint,
            "dedup_source_ids": row.dedup_source_ids,
        }
        return result


KnowledgeRepository = SqlAlchemyKnowledgeStore
