"""
CommentaryPipeline — orchestrates L1 → L2 → L3 for a Document.

Key properties:
  - Each stage saves an immutable PipelineArtifact row.
  - Re-running a single block calls run_l3_single_block only.
  - Full re-run costs are tracked via token_cost fields.
"""

from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction

logger = logging.getLogger(__name__)


class PipelineResult:
    def __init__(self, l1_artifact, l2_artifact, l3_artifact):
        self.l1 = l1_artifact
        self.l2 = l2_artifact
        self.l3 = l3_artifact

    @property
    def total_input_tokens(self):
        total = 0
        for artifact in [self.l1, self.l2, self.l3]:
            if artifact:
                total += artifact.token_cost.get("input", 0)
        return total

    @property
    def total_output_tokens(self):
        total = 0
        for artifact in [self.l1, self.l2, self.l3]:
            if artifact:
                total += artifact.token_cost.get("output", 0)
        return total


class CommentaryPipeline:
    def __init__(self, document):
        self.document = document

    @transaction.atomic
    def run(self, force_l2: bool = False, force_l3: bool = False) -> PipelineResult:
        """
        Full L1 → L2 → L3 pipeline run.

        Saves immutable PipelineArtifact at each stage.
        Updates Document.status throughout.
        """
        from lexbangla.models import PipelineArtifact, ArtifactStage, ProvenanceBlock, BlockType
        from lexbangla.models.workspace import Document as Doc
        from .l1_extractor import extract_chunks, chunks_to_payload
        from .l2_gemini import run_l2
        from .l3_claude import run_l3

        doc = self.document
        doc.status = Doc.Status.PROCESSING
        doc.save(update_fields=["status"])

        try:
            # ── L1 ──────────────────────────────────────────────────────────
            logger.info("Pipeline L1: document=%s", doc.id)
            chunks = extract_chunks(doc.source_text, str(doc.id))
            l1_payload = chunks_to_payload(chunks)

            l1_run = PipelineArtifact.next_run_number(doc, ArtifactStage.L1_EXTRACT)
            l1_artifact = PipelineArtifact.objects.create(
                document=doc,
                stage=ArtifactStage.L1_EXTRACT,
                run_number=l1_run,
                payload=l1_payload,
                model_id="heuristic",
                token_cost={"input": 0, "output": 0, "model": "heuristic"},
            )

            # ── L2 ──────────────────────────────────────────────────────────
            logger.info("Pipeline L2: document=%s", doc.id)
            l2_payload = run_l2(l1_payload)

            l2_run = PipelineArtifact.next_run_number(doc, ArtifactStage.L2_GEMINI)
            l2_artifact = PipelineArtifact.objects.create(
                document=doc,
                stage=ArtifactStage.L2_GEMINI,
                run_number=l2_run,
                payload=l2_payload,
                model_id=l2_payload.get("model_id", ""),
                prompt_hash=l2_payload.get("prompt_hash", ""),
                token_cost=l2_payload.get("token_cost", {}),
            )

            # ── L3 ──────────────────────────────────────────────────────────
            logger.info("Pipeline L3: document=%s", doc.id)
            l3_payload = run_l3(l2_payload, document_title=doc.title)

            l3_run = PipelineArtifact.next_run_number(doc, ArtifactStage.L3_CLAUDE)
            l3_artifact = PipelineArtifact.objects.create(
                document=doc,
                stage=ArtifactStage.L3_CLAUDE,
                run_number=l3_run,
                payload=l3_payload,
                model_id=l3_payload.get("model_id", ""),
                prompt_hash=l3_payload.get("prompt_hash", ""),
                token_cost=l3_payload.get("token_cost", {}),
            )

            # ── Materialise ProvenanceBlocks from L3 output ──────────────
            _materialise_blocks(l3_artifact, l3_payload)

            doc.status = Doc.Status.PUBLISHED
            doc.save(update_fields=["status"])

            logger.info(
                "Pipeline complete: document=%s L3-blocks=%d",
                doc.id, len(l3_payload.get("blocks", []))
            )
            return PipelineResult(l1_artifact, l2_artifact, l3_artifact)

        except Exception:
            doc.status = Doc.Status.DRAFT
            doc.save(update_fields=["status"])
            raise

    @transaction.atomic
    def rerun_block(self, block_id: str) -> "ProvenanceBlock":
        """
        Re-run L3 for a single edited ProvenanceBlock.
        Cost < 10% of full document regen.
        """
        from lexbangla.models import ProvenanceBlock
        from .l3_claude import run_l3_single_block

        block = ProvenanceBlock.objects.get(id=block_id)
        block_dict = {
            "block_type": block.block_type,
            "text": block.display_text,
            "source_citations": block.source_citations,
        }
        result = run_l3_single_block(block_dict, document_title=self.document.title)
        updated = result.get("block", {})

        block.text = updated.get("text", block.text)
        block.source_citations = updated.get("source_citations", block.source_citations)
        block.save(update_fields=["text", "source_citations"])

        return block


def _materialise_blocks(l3_artifact, l3_payload: dict):
    """Save L3 output blocks as ProvenanceBlock rows."""
    from lexbangla.models import ProvenanceBlock, BlockType

    _TYPE_MAP = {
        "binding_law": BlockType.BINDING_LAW,
        "doctrinal_context": BlockType.DOCTRINAL_CONTEXT,
        "verify_case": BlockType.VERIFY_CASE,
        "narrative": BlockType.NARRATIVE,
        "cross_reference": BlockType.CROSS_REFERENCE,
    }

    blocks_data = l3_payload.get("blocks", [])
    ProvenanceBlock.objects.filter(artifact=l3_artifact).delete()

    to_create = []
    for idx, b in enumerate(blocks_data):
        raw_type = b.get("block_type", "narrative")
        verify_suggestion = ""
        text = b.get("text", "")

        if raw_type == "verify_case":
            import re
            m = re.search(r"Suggesting:\s*(.+)", text)
            verify_suggestion = m.group(1).strip() if m else text

        to_create.append(
            ProvenanceBlock(
                artifact=l3_artifact,
                block_type=_TYPE_MAP.get(raw_type, BlockType.NARRATIVE),
                ordinal=idx,
                text=text,
                source_citations=b.get("source_citations", []),
                verify_case_suggestion=verify_suggestion,
            )
        )

    ProvenanceBlock.objects.bulk_create(to_create)
