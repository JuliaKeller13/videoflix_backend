from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from video_app.models import Video


class VideoVisibilityTests(APITestCase):
    """Test visibility of videos in the API."""

    def setUp(self):
        """Authenticate a user for API requests."""
        user = get_user_model().objects.create_user(
            username="viewer@example.com",
            email="viewer@example.com",
            password="SecurePassword123!",
        )
        self.client.force_authenticate(user=user)

    def create_video(self, status):
        """Create a video with a specific processing status."""
        return Video.objects.create(
            title=f"Video {status}",
            description="Test video",
            category="Nature",
            thumbnail="thumbnail/demo.jpg",
            original_video="videos/demo.mp4",
            processing_status=status,
        )

    def test_list_only_returns_ready_videos(self):
        """Hide videos that are not ready for playback."""
        ready = self.create_video(Video.ProcessingStatus.READY)
        for status in ("pending", "processing", "failed"):
            self.create_video(status)
        response = self.client.get("/api/video/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item["id"] for item in response.data},
            {ready.pk},
        )
