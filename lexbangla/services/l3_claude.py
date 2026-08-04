"""
L3 — Publication Standard pass.

Takes L2 provenance blocks and merges them into authoritative Bangladesh legal
commentary formatted to the DLR publication standard.
"""

from __future__ import annotations

import json
import logging

from .llm_client import _system_prompt, _hash_prompt, ClaudeClient, parse_json_response

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_FILE = "l3_publication_standard.txt"


def run_l3(l2_payload: dict, document_title: str = "") -> dict:
    """
    Takes an L2 artifact payload and returns final published commentary.

    Returns a payload dict ready to be stored as a PipelineArtifact.
    """
    client = ClaudeClient()
    system = _system_prompt(_SYSTEM_PROMPT_FILE)

    user_data = {
        "document_title": document_title,
        "l2_blocks": l2_payload.get("blocks", []),
        "jurisdiction_verified": l2_payload.get("jurisdiction_verified", False),
    }
    user = json.dumps(user_data, ensure_ascii=False, indent=2)
    prompt_hash = _hash_prompt(system, user)

    logger.info("L3 call: model=%s blocks=%d", client.model, len(user_data["l2_blocks"]))

    raw, usage = client.complete(system, user)
    parsed = parse_json_response(raw)

    # Flatten sections into a single ordered list of blocks with section tags
    flat_blocks = _flatten_sections(parsed.get("sections", []))
    provenance_summary = parsed.get("provenance_summary", {})

    return {
        "stage": "l3_claude",
        "title": parsed.get("title", document_title),
        "sections": parsed.get("sections", []),
        "blocks": flat_blocks,
        "provenance_summary": provenance_summary,
        "token_cost": usage,
        "prompt_hash": prompt_hash,
        "model_id": usage.get("model", ""),
    }


def run_l3_single_block(block_dict: dict, document_title: str = "") -> dict:
    """
    Re-run L3 for a single edited block only (cost < 10% of full regen).
    Returns updated block dict.
    """
    client = ClaudeClient()
    system = _system_prompt(_SYSTEM_PROMPT_FILE)

    user_data = {
        "document_title": document_title,
        "mode": "single_block_refresh",
        "l2_blocks": [block_dict],
    }
    user = json.dumps(user_data, ensure_ascii=False, indent=2)

    raw, usage = client.complete(system, user)
    parsed = parse_json_response(raw)

    sections = parsed.get("sections", [])
    flat_blocks = _flatten_sections(sections)
    return {
        "block": flat_blocks[0] if flat_blocks else block_dict,
        "token_cost": usage,
    }


def _flatten_sections(sections: list) -> list:
    flat = []
    for section in sections:
        heading = section.get("heading", "")
        for idx, block in enumerate(section.get("blocks", [])):
            block["section_heading"] = heading
            block["section_ordinal"] = idx
            flat.append(block)
    return flat
