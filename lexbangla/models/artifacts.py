import uuid
from django.db import models
from django.utils import timezone


class ArtifactStage(models.TextChoices):
    L1_EXTRACT = "l1_extract", "L1 Extraction"
    L2_GEMINI = "l2_gemini", "L2 Gemini Analysis"
    L3_CLAUDE = "l3_claude", "L3 Claude Publication"


class PipelineArtifact(models.Model):
    """
    Immutable snapshot of one pipeline stage output for a document.

    Each run appends a new artifact row; prior rows are never overwritten,
    which gives a full audit trail and enables block-level re-runs.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        "lexbangla.Document",
        on_delete=models.CASCADE,
        related_name="artifacts",
    )
    stage = models.CharField(max_length=20, choices=ArtifactStage.choices)
    run_number = models.PositiveIntegerField(default=1)
    payload = models.JSONField(help_text="Full structured output from the stage")
    model_id = models.CharField(max_length=100, blank=True, help_text="LLM model that produced this artifact")
    prompt_hash = models.CharField(max_length=64, blank=True, help_text="SHA-256 of system+user prompt")
    token_cost = models.JSONField(
        default=dict,
        help_text='{"input": N, "output": N, "model": "..."}',
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "lex_pipeline_artifacts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["document", "stage"]),
            models.Index(fields=["document", "stage", "run_number"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "stage", "run_number"],
                name="unique_artifact_per_run",
            )
        ]

    def __str__(self):
        return f"{self.document.title} | {self.stage} run#{self.run_number}"

    @classmethod
    def next_run_number(cls, document, stage):
        last = (
            cls.objects.filter(document=document, stage=stage)
            .aggregate(models.Max("run_number"))["run_number__max"]
        )
        return (last or 0) + 1
