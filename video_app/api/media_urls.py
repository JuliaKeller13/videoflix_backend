from pathlib import Path

from django.conf import settings
from django.conf.urls.static import static


def development_media_patterns():
    """Serve only thumbnails during local development."""
    return static(
        f"{settings.MEDIA_URL}thumbnail/",
        document_root=Path(settings.MEDIA_ROOT) / "thumbnail",
    )
