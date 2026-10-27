from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from video_app.models import Video


class VideoStreamingIntegrationTests(APITestCase):
    """Test authenticated video playback across API endpoints."""

    def setUp(self):
        """Prepare isolated media files and an authenticated client."""
        self.media_dir = TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.ready = self._make_video("Ready", "ready")
        self.pending = self._make_video("Pending", "pending")
        self.failed = self._make_video("Failed", "failed")
        for video in (self.ready, self.pending, self.failed):
            self._write_hls(video)
        self._authenticate()

    def _make_video(self, title, processing_status):
        """Create video metadata with a specific processing status."""
        return Video.objects.create(
            title=title, description="Integration test",
            category="Nature",
            thumbnail=f"thumbnail/{title.lower()}.jpg",
            processing_status=processing_status,
        )

    def _hls_folder(self, video):
        """Return the temporary HLS directory for a video."""
        return (
            Path(self.media_dir.name) / "hls" / str(video.pk) / "480p"
        )

    def _write_hls(self, video):
        """Create a playlist and one segment without running FFmpeg."""
        folder = self._hls_folder(video)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.m3u8").write_text(
            "#EXTM3U\n#EXTINF:4.0,\n000.ts\n#EXT-X-ENDLIST\n",
            encoding="utf-8",
        )
        (folder / "000.ts").write_bytes(b"test segment")

    def _authenticate(self):
        """Authenticate the API client using the access cookie."""
        user = get_user_model().objects.create_user(
            username="integration@example.com",
            password="SecurePassword123!",
        )
        token = RefreshToken.for_user(user).access_token
        self.client.cookies["access_token"] = str(token)

    def _url(self, video, segment=False):
        """Build a playlist or segment API URL."""
        filename = "000.ts/" if segment else "index.m3u8"
        return f"/api/video/{video.pk}/480p/{filename}"

    def test_anonymous_requests_are_rejected(self):
        """Require authentication for listing and streaming."""
        self.client.cookies.clear()
        urls = (
            "/api/video/",
            self._url(self.ready),
            self._url(self.ready, segment=True),
        )
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 401)

    def test_video_list_contains_only_ready_videos(self):
        """Hide pending and failed videos from the overview."""
        response = self.client.get("/api/video/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [video["id"] for video in response.data],
            [self.ready.pk],
        )

    def test_video_list_returns_thumbnail_url(self):
        """Provide a usable thumbnail URL in the metadata."""
        response = self.client.get("/api/video/")
        self.assertEqual(
            response.data[0]["thumbnail_url"],
            "http://testserver/media/thumbnail/ready.jpg",
        )

    def test_ready_video_playlist_is_accessible(self):
        """Deliver the playlist of a processed video."""
        response = self.client.get(self._url(self.ready))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"#EXTM3U", response.content)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.apple.mpegurl",
        )

    def test_ready_video_segment_is_accessible(self):
        """Deliver binary segments for processed videos."""
        response = self.client.get(self._url(self.ready, segment=True))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            b"".join(response.streaming_content), b"test segment"
        )
        self.assertEqual(response["Content-Type"], "video/MP2T")

    def test_segment_without_trailing_slash(self):
        """Support the existing frontend segment URL format."""
        url = self._url(self.ready, segment=True).rstrip("/")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unfinished_videos_cannot_be_streamed(self):
        """Reject unfinished videos even when HLS files exist."""
        for video in (self.pending, self.failed):
            for segment in (False, True):
                with self.subTest(video=video.pk, segment=segment):
                    response = self.client.get(self._url(video, segment))
                    self.assertEqual(response.status_code, 404)

    def test_unknown_video_is_not_found(self):
        """Return 404 for an unknown video ID."""
        missing = Video(pk=999999)
        for segment in (False, True):
            response = self.client.get(self._url(missing, segment))
            self.assertEqual(response.status_code, 404)

    def test_missing_playlist_is_not_found(self):
        """Do not stream when the playlist file is missing."""
        (self._hls_folder(self.ready) / "index.m3u8").unlink()
        response = self.client.get(self._url(self.ready))
        self.assertEqual(response.status_code, 404)

    def test_missing_segment_is_not_found(self):
        """Do not stream when the requested segment is missing."""
        (self._hls_folder(self.ready) / "000.ts").unlink()
        response = self.client.get(self._url(self.ready, True))
        self.assertEqual(response.status_code, 404)

    def test_invalid_resolution_is_rejected(self):
        """Reject resolutions outside the supported set."""
        url = f"/api/video/{self.ready.pk}/999p/index.m3u8"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_invalid_segment_name_is_rejected(self):
        """Reject non-TS files from the streaming endpoint."""
        url = f"/api/video/{self.ready.pk}/480p/invalid.mp4/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_direct_hls_media_access_is_blocked(self):
        """Never serve existing HLS files through public media URLs."""
        self.client.cookies.clear()
        url = f"/media/hls/{self.ready.pk}/480p/index.m3u8"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_direct_original_media_access_is_blocked(self):
        """Prevent access to uploaded originals through media URLs."""
        source = Path(self.media_dir.name) / "videos" / "ready.mp4"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"private video")
        self.client.cookies.clear()
        response = self.client.get("/media/videos/ready.mp4")
        self.assertEqual(response.status_code, 404)
