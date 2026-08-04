from django.apps import AppConfig


class LexBanglaConfig(AppConfig):
    name = "lexbangla"
    verbose_name = "LexBangla Legal Research"

    def ready(self):
        import lexbangla.signals  # noqa: F401
