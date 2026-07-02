"""
/v1/retrieve — semantic search over the LexBangla vector store.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from functools import lru_cache

from fastapi import APIRouter, HTTPException

sys.path.insert(0, str(Path(__file__).parents[3] / "packages" / "rag"))

from lexbangla_rag import Retriever  # noqa: E402
from lexbangla_rag.models import RetrievalRequest, RetrievalResponse  # noqa: E402

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["retrieval"])


@lru_cache(maxsize=1)
def _get_retriever() -> Retriever:
    """Singleton retriever — model loaded once per process."""
    return Retriever()


@router.post("/retrieve", response_model=RetrievalResponse)
async def retrieve(req: RetrievalRequest) -> RetrievalResponse:
    """
    Retrieve the most semantically relevant legal document chunks for *query*.

    - **query**: Natural language question or keyword phrase (Bangla or English).
    - **top_k**: Maximum number of results to return (default 5, max 20).
    - **score_threshold**: Minimum cosine similarity score [0, 1] (default 0).
    - **collection**: Qdrant collection to search (default "lexbangla").
    """
    if not req.query.strip():
        raise HTTPException(status_code=422, detail="query must not be empty")

    top_k = min(req.top_k, 20)

    try:
        retriever = _get_retriever()
        results = retriever.retrieve(
            query=req.query,
            top_k=top_k,
            score_threshold=req.score_threshold,
            collection=req.collection,
        )
    except Exception as exc:
        logger.exception("Retrieval failed")
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return RetrievalResponse(query=req.query, results=results, total=len(results))


@router.get("/retrieve/health")
async def health() -> dict[str, str]:
    """Liveness check for the retrieval subsystem."""
    return {"status": "ok"}
