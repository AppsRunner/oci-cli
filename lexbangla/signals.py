from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="lexbangla.Document")
def auto_pipeline_on_source_update(sender, instance, created, **kwargs):
    """
    If a Document's source_text is set for the first time (created with text),
    schedule the pipeline asynchronously if Celery is available.
    Silently skips if no task queue is configured.
    """
    if not created or not instance.source_text:
        return

    try:
        from lexbangla.tasks import run_pipeline_task
        run_pipeline_task.delay(str(instance.id))
    except ImportError:
        pass
