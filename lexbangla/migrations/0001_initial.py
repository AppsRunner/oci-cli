import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        # ── Workspace ──────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Workspace",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(unique=True, max_length=80)),
                ("kind", models.CharField(
                    choices=[("personal", "Personal"), ("firm", "Firm"), ("public", "Public")],
                    default="personal",
                    max_length=20,
                )),
                ("owner_email", models.EmailField()),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"db_table": "lex_workspaces", "ordering": ["name"]},
        ),
        # ── Matter ─────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Matter",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("workspace", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="matters",
                    to="lexbangla.workspace",
                )),
                ("title", models.CharField(max_length=512)),
                ("jurisdiction", models.CharField(default="BD", max_length=50)),
                ("reference_number", models.CharField(blank=True, max_length=100)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "lex_matters", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="matter",
            index=models.Index(fields=["workspace", "jurisdiction"], name="lex_matters_ws_jur_idx"),
        ),
        # ── Document ───────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("matter", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="documents",
                    to="lexbangla.matter",
                )),
                ("title", models.CharField(max_length=512)),
                ("status", models.CharField(
                    choices=[("draft", "Draft"), ("processing", "Processing"),
                             ("published", "Published"), ("archived", "Archived")],
                    default="draft",
                    max_length=20,
                )),
                ("source_text", models.TextField(blank=True)),
                ("citation", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "lex_documents", "ordering": ["-created_at"]},
        ),
        # ── PipelineArtifact ───────────────────────────────────────────────
        migrations.CreateModel(
            name="PipelineArtifact",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("document", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="artifacts",
                    to="lexbangla.document",
                )),
                ("stage", models.CharField(
                    choices=[("l1_extract", "L1 Extraction"),
                             ("l2_gemini", "L2 Gemini Analysis"),
                             ("l3_claude", "L3 Claude Publication")],
                    max_length=20,
                )),
                ("run_number", models.PositiveIntegerField(default=1)),
                ("payload", models.JSONField()),
                ("model_id", models.CharField(blank=True, max_length=100)),
                ("prompt_hash", models.CharField(blank=True, max_length=64)),
                ("token_cost", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={"db_table": "lex_pipeline_artifacts", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="pipelineartifact",
            index=models.Index(fields=["document", "stage"], name="lex_artifact_doc_stage_idx"),
        ),
        migrations.AddIndex(
            model_name="pipelineartifact",
            index=models.Index(fields=["document", "stage", "run_number"], name="lex_artifact_doc_stage_run_idx"),
        ),
        migrations.AddConstraint(
            model_name="pipelineartifact",
            constraint=models.UniqueConstraint(
                fields=["document", "stage", "run_number"],
                name="unique_artifact_per_run",
            ),
        ),
        # ── ProvenanceBlock ─────────────────────────────────────────────────
        migrations.CreateModel(
            name="ProvenanceBlock",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("artifact", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="blocks",
                    to="lexbangla.pipelineartifact",
                )),
                ("block_type", models.CharField(
                    choices=[("binding_law", "Binding Law"), ("doctrinal_context", "Doctrinal Context"),
                             ("verify_case", "Verify Case (Unverified)"), ("narrative", "Narrative"),
                             ("cross_reference", "Cross-Reference")],
                    max_length=30,
                )),
                ("ordinal", models.PositiveIntegerField()),
                ("text", models.TextField()),
                ("source_citations", models.JSONField(default=list)),
                ("verify_case_suggestion", models.CharField(blank=True, max_length=512)),
                ("verified_citation", models.CharField(blank=True, max_length=255)),
                ("is_human_edited", models.BooleanField(default=False)),
                ("edited_text", models.TextField(blank=True)),
                ("edited_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={"db_table": "lex_provenance_blocks", "ordering": ["artifact", "ordinal"]},
        ),
        migrations.AddIndex(
            model_name="provenanceblock",
            index=models.Index(fields=["artifact", "block_type"], name="lex_block_artifact_type_idx"),
        ),
        migrations.AddIndex(
            model_name="provenanceblock",
            index=models.Index(fields=["artifact", "ordinal"], name="lex_block_artifact_ord_idx"),
        ),
    ]
