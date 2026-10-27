from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from video_app.models import Video


class HLSVisibilityTests(APITestCase):
    """Restrict HLS streaming to ready videos."""

    def setUp(self):
        """Authenticate a user and isolate media storage."""
        user = get_user_model().objects.create_user(
            username="viewer@example.com",
            password="SecurePassword123!",
        )
        token = RefreshToken.for_user(user).access_token
        self.client.cookies["access_token"] = str(token)
        self.media_dir = TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

    def create_unready_video(self):
        """Create a processing video with existing HLS files."""
        video = Video.objects.create(
            title="Unfinished", description="Test", category="Nature",
            original_video="videos/demo.mp4",
            processing_status=Video.ProcessingStatus.PROCESSING,
        )
        folder = Path(self.media_dir.name) / "hls" / str(video.pk) / "480p"
        folder.mkdir(parents=True)
        (folder / "index.m3u8").write_text(
            "#EXTM3U\n#EXTINF:4,\n000.ts\n#EXT-X-ENDLIST\n"
        )
        (folder / "000.ts").write_bytes(b"test segment")
        return video

    def test_playlist_requires_ready_status(self):
        """Reject a playlist while processing is incomplete."""
        video = self.create_unready_video()
        response = self.client.get(
            f"/api/video/{video.pk}/480p/index.m3u8"
        )
        self.assertEqual(response.status_code, 404)

    def test_segment_requires_ready_status(self):
        """Reject a segment while processing is incomplete."""
        video = self.create_unready_video()
        response = self.client.get(
            f"/api/video/{video.pk}/480p/000.ts/"
        )
        self.assertEqual(response.status_code, 404)
