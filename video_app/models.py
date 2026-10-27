from django.db import models


class Video(models.Model):
    """Store video metadata and processing information."""

    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100)
    thumbnail = models.ImageField(
        upload_to="thumbnail/",
        blank=True,
    )
    original_video = models.FileField(
        upload_to="videos/",
        blank=True,
    )
    processing_status = models.CharField(
        max_length=10,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Return the video title."""
        return self.title
