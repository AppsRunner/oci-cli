import uuid
from django.db import models
from django.utils import timezone


class Workspace(models.Model):
    """
    Top-level organisational unit. Polymorphic: personal, firm, or public.
    """

    class Kind(models.TextChoices):
        PERSONAL = "personal", "Personal"
        FIRM = "firm", "Firm"
        PUBLIC = "public", "Public"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=80)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.PERSONAL)
    owner_email = models.EmailField()
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "lex_workspaces"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.kind})"


class Matter(models.Model):
    """
    A legal matter (case, project, topic) within a workspace.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="matters"
    )
    title = models.CharField(max_length=512)
    jurisdiction = models.CharField(max_length=50, default="BD")
    reference_number = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "lex_matters"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "jurisdiction"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.reference_number or 'no ref'}]"

    @property
    def is_open(self):
        return self.closed_at is None


class Document(models.Model):
    """
    A source document within a matter. Parent of pipeline artifacts.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PROCESSING = "processing", "Processing"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    matter = models.ForeignKey(
        Matter, on_delete=models.CASCADE, related_name="documents"
    )
    title = models.CharField(max_length=512)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    source_text = models.TextField(blank=True)
    citation = models.CharField(max_length=255, blank=True, help_text="e.g. 67 DLR (AD) 123")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lex_documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.status})"

    def run_pipeline(self):
        """Trigger L1→L2→L3 pipeline for this document."""
        from lexbangla.services.pipeline import CommentaryPipeline
        pipeline = CommentaryPipeline(document=self)
        return pipeline.run()
