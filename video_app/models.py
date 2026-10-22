from django.db import models


class Video(models.Model):
    """Store video metadata, thumbnail, and original file."""

    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100)
    thumbnail = models.ImageField(upload_to="thumbnail/")
    original_video = models.FileField(
        upload_to="videos/",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
