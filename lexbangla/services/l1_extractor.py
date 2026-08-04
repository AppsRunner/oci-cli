"""
L1 — Document extraction and chunk structuring.

Splits raw source_text into typed chunks (statute, precedent, commentary)
using heuristics + regex. No LLM call; fast and deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


# Patterns that identify Bangladesh statutes and SCBD precedents
_BD_STATUTE_RE = re.compile(
    r"\b(Act|Ordinance|Code|Rules?|Regulations?|Order)\b.*?\b(\d{4})\b",
    re.IGNORECASE,
)
_BD_CASE_RE = re.compile(
    r"\b(\d+\s+DLR|BLD|BCR|MLR|CLC)\b",
    re.IGNORECASE,
)
_VERIFY_HINT_RE = re.compile(
    r"\b(ibid|supra|see also|cf\.)\b",
    re.IGNORECASE,
)


@dataclass
class L1Chunk:
    chunk_id: str
    text: str
    chunk_type: str = "narrative"       # statute | precedent | narrative | foreign
    metadata: dict = field(default_factory=dict)


def extract_chunks(source_text: str, document_id: str) -> List[L1Chunk]:
    """
    Split source_text into paragraph-level L1Chunks with auto-classified types.
    """
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", source_text) if p.strip()]
    chunks: List[L1Chunk] = []

    for idx, para in enumerate(paragraphs):
        chunk_type = _classify(para)
        chunks.append(
            L1Chunk(
                chunk_id=f"{document_id}::{idx:04d}",
                text=para,
                chunk_type=chunk_type,
                metadata={"ordinal": idx, "char_count": len(para)},
            )
        )

    return chunks


def _classify(text: str) -> str:
    if _BD_CASE_RE.search(text):
        return "precedent"
    if _BD_STATUTE_RE.search(text):
        return "statute"
    if _VERIFY_HINT_RE.search(text):
        return "foreign"
    return "narrative"


def chunks_to_payload(chunks: List[L1Chunk]) -> dict:
    return {
        "stage": "l1_extract",
        "chunk_count": len(chunks),
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "text": c.text,
                "chunk_type": c.chunk_type,
                "metadata": c.metadata,
            }
            for c in chunks
        ],
    }
