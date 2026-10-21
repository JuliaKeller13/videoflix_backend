from django.db import models


class Video(models.Model):
    """Store video metadata and its thumbnail."""

    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100)
    thumbnail = models.ImageField(upload_to="thumbnail/")
    created_at = models.DateTimeField(auto_now_add=True)