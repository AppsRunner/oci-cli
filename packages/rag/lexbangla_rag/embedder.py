"""
Sentence-transformer based embedder with lazy model loading.

Default model: intfloat/multilingual-e5-large  (1024-dim, strong Bengali support)
Fallback:      paraphrase-multilingual-mpnet-base-v2  (768-dim, lighter)
"""
from __future__ import annotations

import os
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "paraphrase-multilingual-mpnet-base-v2",
)


class Embedder:
    """Thin wrapper around SentenceTransformer with batch support."""

    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> "SentenceTransformer":
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415

            logger.info("Loading embedding model %s …", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()  # type: ignore[return-value]

    def embed(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """Return L2-normalised embeddings for *texts*."""
        if not texts:
            return []
        vecs = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 64,
        )
        return vecs.tolist()

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
