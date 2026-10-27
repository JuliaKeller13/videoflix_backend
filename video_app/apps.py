from importlib import import_module

from django.apps import AppConfig


class VideoAppConfig(AppConfig):
    """Configure the video application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "video_app"

    def ready(self):
        """Register the application's signal handlers."""
        import_module("video_app.signals")
