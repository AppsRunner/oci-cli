"""
L2 — Jurisdictional Firewall analysis.

Applies the Bangladesh-only legal reasoning rules, wrapping content in
<binding_law>, <doctrinal_context>, or <verify_case> XML tags.
Output is a list of ProvenanceBlock-compatible dicts.
"""

from __future__ import annotations

import json
import logging
from typing import List

from .llm_client import _system_prompt, _hash_prompt, get_l2_client, parse_json_response

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_FILE = "l2_jurisdictional_firewall.txt"


def run_l2(l1_payload: dict) -> dict:
    """
    Takes an L1 artifact payload and returns an L2 payload with provenance blocks.

    Raises ValueError if the LLM output contains a foreign case in binding_law
    (jurisdictional bleed detection).
    """
    client = get_l2_client()
    system = _system_prompt(_SYSTEM_PROMPT_FILE)
    user = json.dumps(l1_payload, ensure_ascii=False, indent=2)
    prompt_hash = _hash_prompt(system, user)

    logger.info("L2 call: provider=%s model=%s chunks=%d",
                type(client).__name__, getattr(client, "model", "?"),
                l1_payload.get("chunk_count", 0))

    raw, usage = client.complete(system, user)
    parsed = parse_json_response(raw)

    blocks = parsed.get("blocks", [])
    _assert_no_jurisdictional_bleed(blocks)

    return {
        "stage": "l2_gemini",
        "jurisdiction_verified": parsed.get("jurisdiction_verified", False),
        "blocks": blocks,
        "token_cost": usage,
        "prompt_hash": prompt_hash,
        "model_id": usage.get("model", ""),
    }


_FOREIGN_COURT_SIGNALS = [
    "England", "House of Lords", "Supreme Court UK",
    "India", "Supreme Court of India", "Calcutta",
    "Pakistan", "Lahore", "Karachi",
    "Court of Appeal",
]


def _assert_no_jurisdictional_bleed(blocks: List[dict]) -> None:
    """
    Guard: a binding_law block must not contain foreign court signals.
    Raises ValueError on bleed detection.
    """
    for block in blocks:
        if block.get("block_type") != "binding_law":
            continue
        text = block.get("text", "")
        for signal in _FOREIGN_COURT_SIGNALS:
            if signal.lower() in text.lower():
                raise ValueError(
                    f"Jurisdictional bleed detected: foreign court '{signal}' "
                    f"appears inside a binding_law block.\n"
                    f"Block text (truncated): {text[:200]}"
                )
