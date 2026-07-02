from dataclasses import dataclass, field
from typing import Any
from pydantic import BaseModel


@dataclass
class DocumentChunk:
    text: str
    chunk_index: int
    source: str
    section_title: str = ""
    char_start: int = 0
    char_end: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class RetrievalResult(BaseModel):
    text: str
    score: float
    source: str
    section_title: str
    chunk_index: int
    metadata: dict[str, Any] = {}


class RetrievalRequest(BaseModel):
    query: str
    top_k: int = 5
    score_threshold: float = 0.0
    collection: str = "lexbangla"


class RetrievalResponse(BaseModel):
    results: list[RetrievalResult]
    query: str
    total: int
