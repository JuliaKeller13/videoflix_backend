from django.test import SimpleTestCase, override_settings
from rest_framework.test import APITestCase

from video_app.api.media_urls import development_media_patterns


class MediaRoutingTests(SimpleTestCase):
    """Test local media exposure rules."""

    @override_settings(DEBUG=True)
    def test_thumbnails_have_a_public_development_route(self):
        """Allow the frontend to display thumbnail images."""
        patterns = development_media_patterns()
        self.assertEqual(len(patterns), 1)
        match = patterns[0].resolve("media/thumbnail/demo.jpg")
        self.assertIsNotNone(match)
        self.assertEqual(match.kwargs["path"], "demo.jpg")

    @override_settings(DEBUG=True)
    def test_original_videos_are_not_public(self):
        """Do not expose original uploads directly."""
        pattern = development_media_patterns()[0]
        self.assertIsNone(pattern.resolve("media/videos/demo.mp4"))

    @override_settings(DEBUG=True)
    def test_hls_files_are_not_public(self):
        """Do not expose HLS files outside the protected API."""
        pattern = development_media_patterns()[0]
        self.assertIsNone(
            pattern.resolve("media/hls/1/480p/index.m3u8")
        )

    @override_settings(DEBUG=False)
    def test_development_media_routes_are_disabled(self):
        """Do not enable debug media serving in production."""
        self.assertEqual(development_media_patterns(), [])


class StreamingAuthenticationTests(APITestCase):
    """Test authentication for HLS requests."""

    def test_anonymous_playlist_request_is_rejected(self):
        """Reject playlist requests without a JWT."""
        response = self.client.get("/api/video/1/480p/index.m3u8")
        self.assertEqual(response.status_code, 401)

    def test_anonymous_segment_request_is_rejected(self):
        """Reject video segments without a JWT."""
        response = self.client.get("/api/video/1/480p/000.ts/")
        self.assertEqual(response.status_code, 401)
