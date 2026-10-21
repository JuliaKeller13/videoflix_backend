
import re
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from video_app.api.serializers import VideoSerializer
from video_app.models import Video


class VideoListView(ListAPIView):
    """Return all videos to authenticated users."""

    queryset = Video.objects.order_by("-created_at")
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated]


class VideoPlaylistView(APIView):
    """Deliver HLS playlists to authenticated users."""

    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution):
        """Return the requested HLS playlist or HTTP 404."""
        get_object_or_404(Video, pk=movie_id)
        if resolution not in ("480p", "720p", "1080p"):
            raise Http404("Unsupported resolution.")
        folder = Path(settings.MEDIA_ROOT) / "hls" / str(movie_id)
        playlist = folder / resolution / "index.m3u8"
        if not playlist.is_file():
            raise Http404("Playlist not found.")
        return HttpResponse(
            playlist.read_bytes(),
            content_type="application/vnd.apple.mpegurl",
        )


class VideoSegmentView(APIView):
    """Deliver HLS video segments to authenticated users."""

    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution, segment):
        """Return a binary TS segment or HTTP 404."""
        get_object_or_404(Video, pk=movie_id)
        if resolution not in ("480p", "720p", "1080p"):
            raise Http404("Unsupported resolution.")
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.ts", segment):
            raise Http404("Invalid segment.")
        folder = Path(settings.MEDIA_ROOT) / "hls" / str(movie_id)
        segment_path = folder / resolution / segment
        if not segment_path.is_file():
            raise Http404("Segment not found.")
        return FileResponse(
            segment_path.open("rb"), content_type="video/MP2T"
        )
