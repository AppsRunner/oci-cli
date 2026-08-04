import uuid
from django.db import models
from django.utils import timezone


class BlockType(models.TextChoices):
    BINDING_LAW = "binding_law", "Binding Law"
    DOCTRINAL_CONTEXT = "doctrinal_context", "Doctrinal Context"
    VERIFY_CASE = "verify_case", "Verify Case (Unverified)"
    NARRATIVE = "narrative", "Narrative"
    CROSS_REFERENCE = "cross_reference", "Cross-Reference"


class ProvenanceBlock(models.Model):
    """
    A single paragraph-level content block with full source provenance.

    Every block carries: the text, its type (binding/doctrinal/verify),
    the artifact that produced it, and optional human edits. When a block
    is edited only that block is re-run through L3 (not the whole document).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    artifact = models.ForeignKey(
        "lexbangla.PipelineArtifact",
        on_delete=models.CASCADE,
        related_name="blocks",
    )
    block_type = models.CharField(max_length=30, choices=BlockType.choices)
    ordinal = models.PositiveIntegerField(help_text="Position within the artifact (0-indexed)")
    text = models.TextField()

    # Provenance metadata
    source_citations = models.JSONField(
        default=list,
        help_text='[{"citation": "67 DLR (AD) 123", "principle": "..."}]',
    )
    verify_case_suggestion = models.CharField(
        max_length=512,
        blank=True,
        help_text="Populated for verify_case blocks: 'Suggesting: [Name] re: [Principle]'",
    )
    verified_citation = models.CharField(
        max_length=255,
        blank=True,
        help_text="Filled by user after verifying the suggested case",
    )

    # Edit tracking
    is_human_edited = models.BooleanField(default=False)
    edited_text = models.TextField(blank=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "lex_provenance_blocks"
        ordering = ["artifact", "ordinal"]
        indexes = [
            models.Index(fields=["artifact", "block_type"]),
            models.Index(fields=["artifact", "ordinal"]),
        ]

    def __str__(self):
        snippet = (self.display_text[:60] + "…") if len(self.display_text) > 60 else self.display_text
        return f"[{self.block_type}] {snippet}"

    @property
    def display_text(self):
        return self.edited_text if self.is_human_edited else self.text

    @property
    def is_verified(self):
        return self.block_type == BlockType.VERIFY_CASE and bool(self.verified_citation)

    def apply_human_edit(self, new_text: str):
        self.is_human_edited = True
        self.edited_text = new_text
        self.edited_at = timezone.now()
        self.save(update_fields=["is_human_edited", "edited_text", "edited_at"])

    def resolve_verify_case(self, citation: str):
        """User pastes the confirmed citation for a <verify_case> block."""
        self.verified_citation = citation
        self.block_type = BlockType.BINDING_LAW
        self.save(update_fields=["verified_citation", "block_type"])

    def to_tooltip_dict(self):
        """Serialise block for the ProvenanceTooltip component."""
        return {
            "id": str(self.id),
            "type": self.block_type,
            "text": self.display_text,
            "sources": self.source_citations,
            "verify_suggestion": self.verify_case_suggestion,
            "verified_citation": self.verified_citation,
            "is_human_edited": self.is_human_edited,
        }
