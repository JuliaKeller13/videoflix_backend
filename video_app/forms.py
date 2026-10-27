from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from video_app.models import Video


MAX_VIDEO_BYTES = 200 * 1024 * 1024
MAX_THUMBNAIL_BYTES = 5 * 1024 * 1024


def _validate_video_upload(upload):
    """Validate the MP4 extension, size, and container header."""
    if Path(upload.name).suffix.lower() != ".mp4":
        raise ValidationError("Only MP4 videos are allowed.")
    if upload.size > MAX_VIDEO_BYTES:
        raise ValidationError("Video must not exceed 200 MiB.")
    position = upload.tell()
    try:
        upload.seek(0)
        header = upload.read(12)
    finally:
        upload.seek(position)
    if header[4:8] != b"ftyp":
        raise ValidationError("Invalid MP4 file header.")


def _validate_thumbnail_upload(upload):
    """Validate the image extension and maximum file size."""
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    if Path(upload.name).suffix.lower() not in allowed:
        raise ValidationError("Use JPG, PNG, or WebP images.")
    if upload.size > MAX_THUMBNAIL_BYTES:
        raise ValidationError("Thumbnail must not exceed 5 MiB.")


class VideoAdminForm(forms.ModelForm):
    """Validate newly uploaded video and thumbnail files."""

    class Meta:
        model = Video
        fields = (
            "title", "description", "category",
            "thumbnail", "original_video",
        )

    def clean_original_video(self):
        """Validate a newly uploaded original video."""
        upload = self.files.get("original_video")
        if upload:
            _validate_video_upload(upload)
        return self.cleaned_data["original_video"]

    def clean_thumbnail(self):
        """Validate a newly uploaded thumbnail."""
        upload = self.files.get("thumbnail")
        if upload:
            _validate_thumbnail_upload(upload)
        return self.cleaned_data["thumbnail"]
