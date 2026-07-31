"""Knowledge Graph — SQLAlchemy models for the unified graph.

Connects every entity: targets, companies, findings, reports, rewards,
invoices, events, decisions, CVEs, technologies, wallets, exchanges.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class KGNode(Base):
    """A node in the knowledge graph — any entity."""

    __tablename__ = "knowledge_graph_nodes"

    id = Column(String(64), primary_key=True)
    node_type = Column(String(32), nullable=False, index=True)
    name = Column(String(256), nullable=False, index=True)
    display_label = Column(String(256), default="")
    properties = Column(Text, default="{}")
    source = Column(String(64), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    edges_from = relationship(
        "KGEdge",
        foreign_keys="KGEdge.source_id",
        back_populates="source_node",
        lazy="selectin",
    )
    edges_to = relationship(
        "KGEdge",
        foreign_keys="KGEdge.target_id",
        back_populates="target_node",
        lazy="selectin",
    )


class KGEdge(Base):
    """A directed edge connecting two nodes."""

    __tablename__ = "knowledge_graph_edges"

    id = Column(Integer, primary_key=True)
    source_id = Column(String(64), ForeignKey("knowledge_graph_nodes.id"), nullable=False, index=True)
    target_id = Column(String(64), ForeignKey("knowledge_graph_nodes.id"), nullable=False, index=True)
    edge_type = Column(String(32), nullable=False, index=True)
    weight = Column(Float, default=1.0)
    properties = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    source_node = relationship(
        "KGNode",
        foreign_keys=[source_id],
        back_populates="edges_from",
        lazy="selectin",
    )
    target_node = relationship(
        "KGNode",
        foreign_keys=[target_id],
        back_populates="edges_to",
        lazy="selectin",
    )
