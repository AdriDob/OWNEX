"""Evidence Graph — SQLAlchemy models for persistent evidence storage."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class EvidenceNode(Base):
    """A single evidence item for or against a hypothesis.

    Each node represents one piece of evidence with weight, source, and confidence.
    """

    __tablename__ = "evidence_graph_nodes"

    id = Column(Integer, primary_key=True)
    hypothesis_id = Column(String(128), nullable=False, index=True)
    type = Column(String(16), nullable=False, default="neutral")
    description = Column(Text, nullable=False)
    weight = Column(Float, default=0.5)
    source = Column(String(64), default="unknown")
    confidence = Column(Float, default=0.0)
    origin = Column(String(64), default="core.evidence_graph")
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    edges_from = relationship(
        "EvidenceEdge",
        foreign_keys="EvidenceEdge.from_node_id",
        back_populates="from_node",
        lazy="selectin",
    )
    edges_to = relationship(
        "EvidenceEdge",
        foreign_keys="EvidenceEdge.to_node_id",
        back_populates="to_node",
        lazy="selectin",
    )


class EvidenceEdge(Base):
    """A relationship between two evidence nodes."""

    __tablename__ = "evidence_graph_edges"

    id = Column(Integer, primary_key=True)
    from_node_id = Column(Integer, ForeignKey("evidence_graph_nodes.id"), nullable=False)
    to_node_id = Column(Integer, ForeignKey("evidence_graph_nodes.id"), nullable=False)
    edge_type = Column(String(32), default="related_to")
    weight = Column(Float, default=0.5)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    from_node = relationship(
        "EvidenceNode",
        foreign_keys=[from_node_id],
        back_populates="edges_from",
        lazy="selectin",
    )
    to_node = relationship(
        "EvidenceNode",
        foreign_keys=[to_node_id],
        back_populates="edges_to",
        lazy="selectin",
    )
