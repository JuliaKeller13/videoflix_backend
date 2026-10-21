
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from video_app.models import Video


class VideoSegmentTests(APITestCase):
    """Test authenticated HLS video segment delivery."""

    @classmethod
    def setUpTestData(cls):
        """Create a user and a video for the tests."""
        cls.user = get_user_model().objects.create_user(
            username="segments@example.com",
            password="SecurePassword123!",
        )
        cls.video = Video.objects.create(
            title="Test Movie", description="Test Description",
            category="Drama", thumbnail="thumbnail/test.jpg",
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
        self.url = f"/api/video/{self.video.pk}/480p/000.ts/"

    def _create_segment(self, resolution="480p", segment="000.ts"):
        """Create a binary video segment in temporary storage."""
        folder = Path(self.media_dir.name, "hls", str(self.video.pk))
        folder = folder / resolution
        folder.mkdir(parents=True, exist_ok=True)
        (folder / segment).write_bytes(b"\x47" + bytes(187))

    def test_segment_requires_authentication(self):
        """Reject requests without a valid access token."""
        self._create_segment()
        self.client.cookies.clear()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_segment_returns_binary_content(self):
        """Return the requested MPEG-TS video segment."""
        self._create_segment()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "video/MP2T")
        content = (
            b"".join(response.streaming_content)
            if response.streaming else response.content
        )
        self.assertEqual(content, b"\x47" + bytes(187))

    def test_segment_returns_404_for_unknown_video(self):
        """Reject requests for videos that do not exist."""
        self._create_segment()
        url = "/api/video/999999/480p/000.ts/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_segment_returns_404_when_file_is_missing(self):
        """Reject requests for missing segment files."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_segment_rejects_unsupported_resolution(self):
        """Reject unsupported video resolutions."""
        self._create_segment()
        url = f"/api/video/{self.video.pk}/360p/000.ts/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_segment_rejects_non_ts_files(self):
        """Prevent access to files other than TS segments."""
        self._create_segment(segment="secret.txt")
        url = f"/api/video/{self.video.pk}/480p/secret.txt/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_segment_supports_720p(self):
        """Return a segment for another supported resolution."""
        self._create_segment("720p")
        url = f"/api/video/{self.video.pk}/720p/000.ts/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
