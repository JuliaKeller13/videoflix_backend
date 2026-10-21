from rest_framework import serializers

from video_app.models import Video


class VideoSerializer(serializers.ModelSerializer):
    """Serialize video metadata for the frontend."""

    thumbnail_url = serializers.ImageField(
        source="thumbnail",
        read_only=True,
    )

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