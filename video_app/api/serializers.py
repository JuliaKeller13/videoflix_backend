from django.templatetags.static import static
from rest_framework import serializers

from video_app.models import Video


class VideoSerializer(serializers.ModelSerializer):
    """Serialize video metadata for the frontend."""

    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            "id",
            "created_at",
            "title",
            "description",
            "thumbnail_url",
            "category",
        ]

    def get_thumbnail_url(self, video):
        """Return the thumbnail URL or the default image URL."""
        path = (
            video.thumbnail.url
            if video.thumbnail
            else static("default_thumbnail.svg")
        )
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path
