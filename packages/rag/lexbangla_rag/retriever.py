"""High-level retrieval: query → embed → search → return ranked results."""
from __future__ import annotations

from .embedder import Embedder
from .models import RetrievalResult
from .vector_store import VectorStore


class Retriever:
    """Combines Embedder + VectorStore into a single retrieval call."""

    def __init__(
        self,
        embedder: Embedder | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self._embedder = embedder or Embedder()
        self._store = vector_store or VectorStore()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
        collection: str | None = None,
        filter_source: str | None = None,
    ) -> list[RetrievalResult]:
        """Embed *query* and return top-k semantically similar chunks."""
        if collection:
            store = VectorStore(
                collection=collection,
                dimension=self._embedder.dimension,
            )
        else:
            store = self._store

        query_vec = self._embedder.embed_one(query)
        filter_ = {"source": filter_source} if filter_source else None

        return store.search(
            query_vector=query_vec,
            top_k=top_k,
            score_threshold=score_threshold,
            filter_=filter_,
        )
