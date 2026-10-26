import django_rq
from django.contrib import admin
from django.db import transaction

from video_app.models import Video
from video_app.services import process_video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    """Manage videos and schedule their processing."""

    list_display = ("title", "category", "created_at")

    def save_model(self, request, obj, form, change):
        """Queue conversion only when the original video changes."""
        previous_file = None
        if change:
            previous_file = Video.objects.filter(pk=obj.pk).values_list(
                "original_video", flat=True
            ).first()
        super().save_model(request, obj, form, change)
        if not obj.original_video or previous_file == obj.original_video.name:
            return
        transaction.on_commit(
            lambda: django_rq.get_queue("default").enqueue(
                process_video, obj.pk
            )
        )
