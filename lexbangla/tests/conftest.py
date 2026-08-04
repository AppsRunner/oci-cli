"""
Shared pytest fixtures for LexBangla tests.
"""

import json
import pytest
from unittest.mock import MagicMock, patch


# ── Fixture: minimal L1 payload ────────────────────────────────────────────

@pytest.fixture
def l1_payload_statute():
    return {
        "stage": "l1_extract",
        "chunk_count": 2,
        "chunks": [
            {
                "chunk_id": "doc-uuid::0000",
                "text": "Section 7 of the Contract Act 1872 requires acceptance to be absolute.",
                "chunk_type": "statute",
                "metadata": {"ordinal": 0, "char_count": 70},
            },
            {
                "chunk_id": "doc-uuid::0001",
                "text": "The Appellate Division held in 45 DLR (AD) 112 that consideration need not be adequate.",
                "chunk_type": "precedent",
                "metadata": {"ordinal": 1, "char_count": 90},
            },
        ],
    }


@pytest.fixture
def l1_payload_mixed():
    return {
        "stage": "l1_extract",
        "chunk_count": 3,
        "chunks": [
            {
                "chunk_id": "doc::0000",
                "text": "The High Court Division in 55 DLR (HCD) 201 applied the rule from Carlill v Carbolic Smoke Ball.",
                "chunk_type": "precedent",
                "metadata": {"ordinal": 0, "char_count": 95},
            },
            {
                "chunk_id": "doc::0001",
                "text": "Chitty on Contracts (34th ed) sets out the English law on offer and acceptance.",
                "chunk_type": "narrative",
                "metadata": {"ordinal": 1, "char_count": 79},
            },
            {
                "chunk_id": "doc::0002",
                "text": "Section 2(a) of the Contract Act 1872 defines a proposal.",
                "chunk_type": "statute",
                "metadata": {"ordinal": 2, "char_count": 57},
            },
        ],
    }


# ── Fixture: L2 output blocks ──────────────────────────────────────────────

@pytest.fixture
def l2_payload_clean():
    return {
        "stage": "l2_gemini",
        "jurisdiction_verified": True,
        "blocks": [
            {
                "block_type": "binding_law",
                "text": "Section 7 of the Contract Act 1872 requires acceptance to be absolute and unqualified.",
                "source_citations": [{"citation": "Contract Act 1872, s 7", "principle": "Absolute acceptance"}],
            },
            {
                "block_type": "binding_law",
                "text": "The Appellate Division held in 45 DLR (AD) 112 that consideration need not be adequate.",
                "source_citations": [{"citation": "45 DLR (AD) 112", "principle": "Adequacy of consideration"}],
            },
            {
                "block_type": "doctrinal_context",
                "text": "Chitty on Contracts (34th ed) articulates the English test for certainty of terms.",
                "source_citations": [{"citation": "Chitty on Contracts (34th ed)", "principle": "Certainty of terms"}],
            },
        ],
        "token_cost": {"input": 500, "output": 300, "model": "deepseek-reasoner"},
        "prompt_hash": "abc123",
        "model_id": "deepseek-reasoner",
    }


@pytest.fixture
def l2_payload_with_verify():
    return {
        "stage": "l2_gemini",
        "jurisdiction_verified": True,
        "blocks": [
            {
                "block_type": "verify_case",
                "text": "Suggesting: Rahim v Bangladesh Steel Authority re: Promissory Estoppel",
                "source_citations": [],
            },
            {
                "block_type": "binding_law",
                "text": "63 DLR (AD) 45 confirmed that equitable doctrines apply in Bangladesh.",
                "source_citations": [{"citation": "63 DLR (AD) 45", "principle": "Equitable jurisdiction"}],
            },
        ],
        "token_cost": {"input": 400, "output": 200, "model": "deepseek-reasoner"},
        "prompt_hash": "def456",
        "model_id": "deepseek-reasoner",
    }


@pytest.fixture
def l2_payload_with_bleed():
    """Contains a foreign court case incorrectly inside binding_law."""
    return {
        "stage": "l2_gemini",
        "jurisdiction_verified": False,
        "blocks": [
            {
                "block_type": "binding_law",
                "text": "The House of Lords in Donoghue v Stevenson established the neighbour principle.",
                "source_citations": [],
            },
        ],
        "token_cost": {"input": 100, "output": 50, "model": "deepseek-reasoner"},
        "prompt_hash": "bleed000",
        "model_id": "deepseek-reasoner",
    }


# ── Fixture: L3 output ─────────────────────────────────────────────────────

@pytest.fixture
def l3_payload():
    return {
        "stage": "l3_claude",
        "title": "Commentary: Contract Act 1872 — Section 7",
        "sections": [
            {
                "heading": "Purpose",
                "blocks": [
                    {
                        "block_type": "binding_law",
                        "text": "Section 7 mandates absolute acceptance for contract formation under Bangladesh law.",
                        "source_citations": [{"citation": "Contract Act 1872, s 7", "principle": "Absolute acceptance"}],
                        "section_heading": "Purpose",
                        "section_ordinal": 0,
                    }
                ],
            },
            {
                "heading": "Key Requirements",
                "blocks": [
                    {
                        "block_type": "binding_law",
                        "text": "45 DLR (AD) 112 confirms adequacy of consideration is irrelevant.",
                        "source_citations": [{"citation": "45 DLR (AD) 112", "principle": "Consideration adequacy"}],
                        "section_heading": "Key Requirements",
                        "section_ordinal": 0,
                    },
                ],
            },
            {
                "heading": "Practical Application",
                "blocks": [
                    {
                        "block_type": "narrative",
                        "text": "Practitioners should ensure acceptance is communicated unequivocally.",
                        "source_citations": [],
                        "section_heading": "Practical Application",
                        "section_ordinal": 0,
                    }
                ],
            },
            {
                "heading": "Cross-References",
                "blocks": [
                    {
                        "block_type": "cross_reference",
                        "text": "See also Contract Act 1872, s 2(a) on proposal definitions.",
                        "source_citations": [],
                        "section_heading": "Cross-References",
                        "section_ordinal": 0,
                    }
                ],
            },
        ],
        "blocks": [
            {
                "block_type": "binding_law",
                "text": "Section 7 mandates absolute acceptance.",
                "source_citations": [{"citation": "Contract Act 1872, s 7", "principle": "Absolute acceptance"}],
                "section_heading": "Purpose",
                "section_ordinal": 0,
            },
        ],
        "provenance_summary": {"binding_count": 2, "doctrinal_count": 1, "verify_count": 0},
        "token_cost": {"input": 800, "output": 600, "model": "claude-sonnet-4-6"},
        "prompt_hash": "ghi789",
        "model_id": "claude-sonnet-4-6",
    }


# ── Mock LLM responses ─────────────────────────────────────────────────────

@pytest.fixture
def mock_l2_client(l2_payload_clean):
    """Patches get_l2_client to return a mock that yields l2_payload_clean."""
    mock = MagicMock()
    mock.complete.return_value = (
        json.dumps({"blocks": l2_payload_clean["blocks"], "jurisdiction_verified": True}),
        l2_payload_clean["token_cost"],
    )
    mock.model = "deepseek-reasoner"
    with patch("lexbangla.services.l2_gemini.get_l2_client", return_value=mock):
        yield mock


@pytest.fixture
def mock_l3_client(l3_payload):
    """Patches ClaudeClient to return a mock that yields l3_payload."""
    mock = MagicMock()
    mock.complete.return_value = (
        json.dumps({
            "title": l3_payload["title"],
            "sections": l3_payload["sections"],
            "provenance_summary": l3_payload["provenance_summary"],
        }),
        l3_payload["token_cost"],
    )
    mock.model = "claude-sonnet-4-6"
    with patch("lexbangla.services.l3_claude.ClaudeClient", return_value=mock):
        yield mock
