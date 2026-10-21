
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from video_app.models import Video


class VideoPlaylistTests(APITestCase):
    """Test authenticated HLS playlist delivery."""

    @classmethod
    def setUpTestData(cls):
        """Create the test user and video."""
        cls.user = get_user_model().objects.create_user(
            username="playlist@example.com",
            password="SecurePassword123!",
        )
        cls.video = Video.objects.create(
            title="Test Movie",
            description="Test Description",
            category="Drama",
            thumbnail="thumbnail/test.jpg",
        )

    def setUp(self):
        """Prepare temporary media storage and authentication."""
        self.media_dir = TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        token = RefreshToken.for_user(self.user).access_token
        self.client.cookies["access_token"] = str(token)
        self.url = f"/api/video/{self.video.pk}/480p/index.m3u8"

    def _create_playlist(self, resolution="480p"):
        """Create a test playlist in temporary storage."""
        folder = Path(self.media_dir.name, "hls", str(self.video.pk))
        folder = folder / resolution
        folder.mkdir(parents=True, exist_ok=True)
        content = "#EXTM3U\n#EXTINF:4,\n000.ts\n#EXT-X-ENDLIST\n"
        (folder / "index.m3u8").write_text(content, encoding="utf-8")

    def test_playlist_requires_authentication(self):
        """Reject requests without a valid access token."""
        self._create_playlist()
        self.client.cookies.clear()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_playlist_returns_hls_content(self):
        """Return a playlist with the correct content type."""
        self._create_playlist()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.apple.mpegurl",
        )
        self.assertContains(response, "#EXTM3U")

    def test_playlist_returns_404_for_unknown_video(self):
        """Reject requests for videos that do not exist."""
        self._create_playlist()
        url = "/api/video/999999/480p/index.m3u8"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_playlist_returns_404_when_file_is_missing(self):
        """Reject requests when no playlist file exists."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_playlist_rejects_unknown_resolution(self):
        """Reject unsupported video resolutions."""
        self._create_playlist()
        url = f"/api/video/{self.video.pk}/360p/index.m3u8"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_playlist_supports_720p(self):
        """Return a playlist for another supported resolution."""
        self._create_playlist("720p")
        url = f"/api/video/{self.video.pk}/720p/index.m3u8"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
