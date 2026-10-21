from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from video_app.api.serializers import VideoSerializer
from video_app.models import Video


class VideoListView(ListAPIView):
    """Return all videos to authenticated users."""

    queryset = Video.objects.order_by("-created_at")
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated]