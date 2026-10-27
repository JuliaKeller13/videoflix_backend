import shutil
from pathlib import Path

import django_rq
from django.conf import settings
from django.contrib import admin
from django.db import transaction

from video_app.models import Video
from video_app.services import process_video


def _source_changed(obj, form, previous):
    """Detect original video changes, including same-name uploads."""
    if form is not None:
        return "original_video" in form.changed_data
    return previous != (obj.original_video.name or None)


def _reset_processing(obj):
    """Mark a replacement pending and reset generated thumbnails."""
    obj.processing_status = Video.ProcessingStatus.PENDING
    generated = f"thumbnail/{obj.pk}.jpg"
    if obj.thumbnail.name == generated:
        obj.thumbnail = ""
        return generated
    return None


def _cleanup_replaced_media(movie_id, previous, old_thumbnail):
    """Remove files no longer referenced by a video."""
    files = (("original_video", previous), ("thumbnail", old_thumbnail))
    for field, filename in files:
        if filename and not Video.objects.filter(**{field: filename}).exists():
            Video._meta.get_field(field).storage.delete(filename)
    folder = Path(settings.MEDIA_ROOT) / "hls" / str(movie_id)
    shutil.rmtree(folder, ignore_errors=True)


def _finalize_video_save(movie_id, previous, old_thumbnail, replaced):
    """Clean old files and enqueue conversion when needed."""
    if replaced:
        _cleanup_replaced_media(movie_id, previous, old_thumbnail)
    video = Video.objects.get(pk=movie_id)
    if video.original_video:
        django_rq.get_queue("default").enqueue(process_video, movie_id)


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    """Manage videos and schedule their processing."""

    list_display = ("title", "category", "created_at")

    def _previous_source(self, obj, change):
        """Read the original file before an existing video is saved."""
        if not change:
            return None
        return Video.objects.filter(pk=obj.pk).values_list(
            "original_video", flat=True
        ).first()

    def save_model(self, request, obj, form, change):
        """Schedule cleanup and processing after a successful save."""
        previous = self._previous_source(obj, change)
        changed = _source_changed(obj, form, previous)
        old_thumbnail = _reset_processing(obj) if change and changed else None
        super().save_model(request, obj, form, change)
        if changed:
            transaction.on_commit(
                lambda: _finalize_video_save(
                    obj.pk, previous, old_thumbnail, change
                )
            )
