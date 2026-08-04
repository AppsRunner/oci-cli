"""
Migration: Backfill legacy data.

Creates 1 default Workspace and 1 Matter "Legacy Commentaries".
Existing data_document_chunks remain untouched.
commentary_drafts is deprecated (not dropped here — see 0003).
"""

from django.db import migrations
import uuid


def create_default_workspace(apps, schema_editor):
    Workspace = apps.get_model("lexbangla", "Workspace")
    Matter = apps.get_model("lexbangla", "Matter")

    ws, created = Workspace.objects.get_or_create(
        slug="default",
        defaults={
            "id": uuid.uuid4(),
            "name": "Default Workspace",
            "kind": "personal",
            "owner_email": "admin@lexbangla.bd",
        },
    )

    Matter.objects.get_or_create(
        workspace=ws,
        reference_number="LEGACY-001",
        defaults={
            "id": uuid.uuid4(),
            "title": "Legacy Commentaries",
            "jurisdiction": "BD",
        },
    )


def reverse_backfill(apps, schema_editor):
    Workspace = apps.get_model("lexbangla", "Workspace")
    Workspace.objects.filter(slug="default").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("lexbangla", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_workspace, reverse_backfill),
    ]
