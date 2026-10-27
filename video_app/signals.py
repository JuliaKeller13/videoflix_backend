import shutil
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from video_app.models import Video


def _remove_media_files(paths, hls_folder):
    """Remove the original, thumbnail, and HLS files."""
    for path in paths:
        if path:
            Path(path).unlink(missing_ok=True)
    shutil.rmtree(hls_folder, ignore_errors=True)


@receiver(post_delete, sender=Video)
def remove_video_files(sender, instance, **kwargs):
    """Schedule file cleanup after the database commit."""
    paths = (
        instance.original_video.path if instance.original_video else None,
        instance.thumbnail.path if instance.thumbnail else None,
    )
    hls_folder = Path(settings.MEDIA_ROOT) / "hls" / str(instance.pk)
    transaction.on_commit(
        lambda: _remove_media_files(paths, hls_folder)
    )
