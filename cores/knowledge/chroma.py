"""ChromaDB Wrapper for KnowledgeBridge — Semantic search via embeddings."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.knowledge.chroma")


class ChromaDBWrapper:
    """ChromaDB wrapper for semantic search over knowledge notes.

    Provides:
    - Collection management (create/get)
    - Vector upsert/query/delete
    - Hybrid search (semantic + metadata filtering)
    - Automatic embedding generation via Ollama/local models
    """

    def __init__(
        self,
        persist_dir: str | Path = "~/.local/share/ownex/chroma",
        collection_name: str = "ownex_knowledge",
        embedding_model: str = "nomic-embed-text",
        ollama_base_url: str = "http://localhost:11434",
    ) -> None:
        self.persist_dir = Path(persist_dir).expanduser()
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.ollama_base_url = ollama_base_url.rstrip("/")

        self._client = None
        self._collection = None
        self._embed_cache: dict[str, list[float]] = {}

    def _get_client(self):
        """Lazy-initialize ChromaDB client."""
        if self._client is not None:
            return self._client

        try:
            import chromadb
            from chromadb.config import Settings

            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(anonymized_telemetry=False),
            )
            return self._client
        except ImportError:
            logger.warning("chromadb not installed. Run: pip install chromadb")
            return None
        except Exception as exc:
            logger.error("Failed to initialize ChromaDB: %s", exc)
            return None

    def _get_collection(self):
        """Get or create the knowledge collection."""
        client = self._get_client()
        if client is None:
            return None

        if self._collection is not None:
            return self._collection

        try:
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "OWNEX KnowledgeBridge notes"},
            )
            return self._collection
        except Exception as exc:
            logger.error("Failed to get/create collection: %s", exc)
            return None

    def is_available(self) -> bool:
        """Check if ChromaDB is available."""
        return self._get_client() is not None and self._get_collection() is not None

    def _get_embedding(self, text: str) -> list[float] | None:
        """Get embedding for text via Ollama."""
        if text in self._embed_cache:
            return self._embed_cache[text]

        try:
            import httpx

            response = httpx.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={"model": self.embedding_model, "prompt": text},
                timeout=30,
            )
            if response.status_code == 200:
                embedding = response.json().get("embedding", [])
                self._embed_cache[text] = embedding
                return embedding
            logger.warning("Ollama embedding failed: %s", response.text)
        except Exception as exc:
            logger.warning("Embedding generation failed: %s", exc)
        return None

    def _get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            emb = self._get_embedding(text)
            if emb is None:
                # Return zero vector as fallback
                emb = [0.0] * 768  # nomic-embed-text dimension
            embeddings.append(emb)
        return embeddings

    def upsert_note(self, note_id: str, title: str, body: str, metadata: dict[str, Any]) -> bool:
        """Upsert a note into the collection."""
        collection = self._get_collection()
        if collection is None:
            return False

        try:
            # Combine title + body for embedding
            text = f"{title}\n\n{body}"
            embedding = self._get_embedding(text)
            if embedding is None:
                logger.warning("Failed to generate embedding for note %s", note_id)
                return False

            # Ensure metadata values are JSON-serializable
            clean_metadata = {}
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_metadata[k] = v
                elif isinstance(v, (list, dict)):
                    import json

                    clean_metadata[k] = json.dumps(v)
                else:
                    clean_metadata[k] = str(v)

            collection.upsert(
                ids=[note_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[clean_metadata],
            )
            return True
        except Exception as exc:
            logger.error("Failed to upsert note %s: %s", note_id, exc)
            return False

    def upsert_notes_batch(self, notes: list[dict[str, Any]]) -> int:
        """Batch upsert multiple notes."""
        collection = self._get_collection()
        if collection is None:
            return 0

        successful = 0
        batch_size = 100

        for i in range(0, len(notes), batch_size):
            batch = notes[i : i + batch_size]
            try:
                ids = []
                embeddings = []
                documents = []
                metadatas = []

                for note in batch:
                    note_id = note.get("id") or note.get("path") or note.get("title", "")
                    if not note_id:
                        continue

                    text = f"{note.get('title', '')}\n\n{note.get('body', note.get('content', ''))}"
                    embedding = self._get_embedding(text)
                    if embedding is None:
                        continue

                    ids.append(note_id)
                    embeddings.append(embedding)
                    documents.append(text)

                    meta = {}
                    for k, v in note.items():
                        if k not in ("id", "title", "body", "content", "embedding"):
                            if isinstance(v, (str, int, float, bool)):
                                meta[k] = v
                            elif isinstance(v, (list, dict)):
                                import json

                                meta[k] = json.dumps(v)
                            else:
                                meta[k] = str(v)
                    metadatas.append(meta)

                if ids:
                    collection.upsert(
                        ids=ids,
                        embeddings=embeddings,
                        documents=documents,
                        metadatas=metadatas,
                    )
                    successful += len(ids)

            except Exception as exc:
                logger.error("Batch upsert failed: %s", exc)

        return successful

    def query(
        self,
        query_text: str,
        n_results: int = 10,
        where: dict[str, Any] | None = None,
        where_document: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Semantic search query with manual cosine similarity computation."""
        collection = self._get_collection()
        if collection is None:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        try:
            embedding = self._get_embedding(query_text)
            if embedding is None:
                return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

            # Get all embeddings and compute cosine similarity manually
            # (ChromaDB's distance metric doesn't reliably return cosine distance)
            all_data = collection.get(include=["embeddings", "documents", "metadatas", "uris"])
            embeddings = all_data.get("embeddings", [])
            documents = all_data.get("documents", [])
            metadatas = all_data.get("metadatas", [])
            ids = all_data.get("ids", [])

            if embeddings is None or len(embeddings) == 0:
                return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

            import numpy as np

            query_emb = np.array(embedding)
            query_norm = float(np.linalg.norm(query_emb))

            if query_norm == 0:
                return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

            # Compute cosine similarities
            results = []
            for i, (doc_emb, id_, doc, meta) in enumerate(zip(embeddings, ids, documents, metadatas)):
                doc_norm = float(np.linalg.norm(doc_emb))
                if doc_norm > 0 and query_norm > 0:
                    cosine_sim = float(np.dot(doc_emb, query_emb) / (doc_norm * query_norm))
                    cosine_dist = 1.0 - cosine_sim
                    results.append(
                        {
                            "id": ids[i],
                            "document": documents[i],
                            "metadata": metadatas[i],
                            "distance": cosine_dist,
                        }
                    )

            # Sort by distance (ascending = most similar first)
            results.sort(key=lambda x: x["distance"])

            # Take top n_results
            results = results[:n_results]

            # Filter by where clause if provided
            if where:
                filtered = []
                for r in results:
                    match = True
                    for k, v in where.items():
                        if r["metadata"].get(k) != v:
                            match = False
                            break
                    if match:
                        filtered.append(r)
                results = filtered

            # Filter by where_document if provided
            if where_document:
                filtered = []
                for r in results:
                    if any(v.lower() in r["document"].lower() for v in where_document.values()):
                        filtered.append(r)
                results = filtered

            return {
                "ids": [[r["id"] for r in results]],
                "documents": [[r["document"] for r in results]],
                "metadatas": [[r["metadata"] for r in results]],
                "distances": [[r["distance"] for r in results]],
            }
        except Exception as exc:
            logger.error("ChromaDB query failed: %s", exc)
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    def delete_note(self, note_id: str) -> bool:
        """Delete a note from the collection."""
        collection = self._get_collection()
        if collection is None:
            return False

        try:
            collection.delete(ids=[note_id])
            return True
        except Exception as exc:
            logger.error("Failed to delete note %s: %s", note_id, exc)
            return False

    def delete_notes_by_path(self, path: str) -> bool:
        """Delete notes by path metadata."""
        collection = self._get_collection()
        if collection is None:
            return False

        try:
            collection.delete(where={"path": path})
            return True
        except Exception as exc:
            logger.error("Failed to delete notes by path: %s", exc)
            return False

    def get_collection_stats(self) -> dict[str, Any]:
        """Get collection statistics."""
        collection = self._get_collection()
        if collection is None:
            return {"count": 0, "available": False}

        try:
            count = collection.count()
            return {"count": count, "available": True, "name": self.collection_name}
        except Exception as exc:
            logger.error("Failed to get stats: %s", exc)
            return {"count": 0, "available": False, "error": str(exc)}

    def reset_collection(self) -> bool:
        """Delete and recreate the collection."""
        client = self._get_client()
        if client is None:
            return False

        try:
            client.delete_collection(self.collection_name)
            self._collection = None
            self._get_collection()  # Recreate
            return True
        except Exception as exc:
            logger.error("Failed to reset collection: %s", exc)
            return False


def get_chroma_wrapper() -> ChromaDBWrapper:
    """Module-level singleton."""
    global _chroma_wrapper
    if _chroma_wrapper is None:
        _chroma_wrapper = ChromaDBWrapper()
    return _chroma_wrapper


_chroma_wrapper: ChromaDBWrapper | None = None
