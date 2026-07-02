"""
Qdrant vector store wrapper for LexBangla.

Manages collection lifecycle (create / recreate) and
provides typed upsert + search operations.
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from .models import DocumentChunk, RetrievalResult

logger = logging.getLogger(__name__)

_QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
_QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")


class VectorStore:
    """CRUD interface over a single Qdrant collection."""

    def __init__(
        self,
        collection: str = "lexbangla",
        dimension: int = 768,
        url: str = _QDRANT_URL,
        api_key: str = _QDRANT_API_KEY,
    ) -> None:
        self.collection = collection
        self.dimension = dimension
        self._client = QdrantClient(
            url=url,
            api_key=api_key or None,
            timeout=30,
        )

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def ensure_collection(self, recreate: bool = False) -> None:
        """Create the collection if it doesn't exist (or recreate it)."""
        existing = {c.name for c in self._client.get_collections().collections}

        if recreate and self.collection in existing:
            logger.info("Deleting existing collection '%s'", self.collection)
            self._client.delete_collection(self.collection)
            existing.discard(self.collection)

        if self.collection not in existing:
            logger.info(
                "Creating collection '%s' (dim=%d)", self.collection, self.dimension
            )
            self._client.create_collection(
                collection_name=self.collection,
                vectors_config=qm.VectorParams(
                    size=self.dimension,
                    distance=qm.Distance.COSINE,
                ),
            )
            self._client.create_payload_index(
                collection_name=self.collection,
                field_name="source",
                field_schema=qm.PayloadSchemaType.KEYWORD,
            )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def upsert(
        self,
        chunks: list[DocumentChunk],
        vectors: list[list[float]],
    ) -> int:
        """Batch-upsert *chunks* with their *vectors*. Returns count inserted."""
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")

        points = [
            qm.PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload=self._chunk_payload(chunk),
            )
            for chunk, vec in zip(chunks, vectors)
        ]

        batch_size = 256
        for i in range(0, len(points), batch_size):
            self._client.upsert(
                collection_name=self.collection,
                points=points[i : i + batch_size],
                wait=True,
            )

        logger.info("Upserted %d points into '%s'", len(points), self.collection)
        return len(points)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
        filter_: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        """Return top-k results above *score_threshold*."""
        qdrant_filter = None
        if filter_:
            must = [
                qm.FieldCondition(
                    key=k,
                    match=qm.MatchValue(value=v),
                )
                for k, v in filter_.items()
            ]
            qdrant_filter = qm.Filter(must=must)

        hits = self._client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold if score_threshold > 0 else None,
            query_filter=qdrant_filter,
            with_payload=True,
        )

        return [
            RetrievalResult(
                text=h.payload.get("text", ""),
                score=h.score,
                source=h.payload.get("source", ""),
                section_title=h.payload.get("section_title", ""),
                chunk_index=h.payload.get("chunk_index", 0),
                metadata=h.payload.get("metadata", {}),
            )
            for h in hits
        ]

    def delete_by_source(self, source: str) -> None:
        """Remove all points originating from *source*."""
        self._client.delete(
            collection_name=self.collection,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[
                        qm.FieldCondition(
                            key="source",
                            match=qm.MatchValue(value=source),
                        )
                    ]
                )
            ),
        )

    def collection_info(self) -> dict[str, Any]:
        info = self._client.get_collection(self.collection)
        return {
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.value,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _chunk_payload(chunk: DocumentChunk) -> dict[str, Any]:
        return {
            "text": chunk.text,
            "source": chunk.source,
            "chunk_index": chunk.chunk_index,
            "section_title": chunk.section_title,
            "char_start": chunk.char_start,
            "char_end": chunk.char_end,
            "metadata": chunk.metadata,
        }
