from .chunker import LegalDocumentChunker, DocumentChunk
from .models import RetrievalResult, RetrievalRequest, RetrievalResponse

__all__ = [
    "LegalDocumentChunker",
    "DocumentChunk",
    "RetrievalResult",
    "RetrievalRequest",
    "RetrievalResponse",
]


def __getattr__(name: str):
    if name == "Embedder":
        from .embedder import Embedder  # noqa: PLC0415
        return Embedder
    if name == "VectorStore":
        from .vector_store import VectorStore  # noqa: PLC0415
        return VectorStore
    if name == "Retriever":
        from .retriever import Retriever  # noqa: PLC0415
        return Retriever
    raise AttributeError(f"module 'lexbangla_rag' has no attribute {name!r}")
