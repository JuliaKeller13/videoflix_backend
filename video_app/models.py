from django.db import models


class Video(models.Model):
    """Store video metadata and processing information."""
    class Category(models.TextChoices):
        ACTION = "Action", "Action"
        ADVENTURE = "Adventure", "Adventure"
        COMEDY = "Comedy", "Comedy"
        DOCUMENTARY = "Documentary", "Documentary"
        DRAMA = "Drama", "Drama"
        FANTASY = "Fantasy", "Fantasy"
        HORROR = "Horror", "Horror"
        NATURE = "Nature", "Nature"
        SCI_FI = "Sci-Fi", "Sci-Fi"
        THRILLER = "Thriller", "Thriller"

    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100, choices=Category.choices)
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
