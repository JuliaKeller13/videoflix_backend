from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from video_app.models import Video


class VideoListTests(APITestCase):
    """Test the authenticated video list endpoint."""

    def setUp(self):
        """Prepare an authenticated test client."""
        self.url = "/api/video/"
        user = get_user_model().objects.create_user(
            username="viewer@example.com",
            password="SecurePassword123!",
        )
        token = RefreshToken.for_user(user).access_token
        self.client.cookies["access_token"] = str(token)

    def test_video_list_requires_authentication(self):
        """Reject requests without authentication."""
        self.client.cookies.clear()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_video_list_is_empty(self):
        """Return an empty list when no videos exist."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_video_list_returns_metadata(self):
        """Return the documented video fields."""
        Video.objects.create(
            title="Test Movie", description="Test Description",
            category="Drama", thumbnail="thumbnail/test.jpg",
            processing_status=Video.ProcessingStatus.READY,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        expected = {
            "id", "created_at", "title", "description",
            "thumbnail_url", "category",
        }
        self.assertEqual(set(response.data[0]), expected)

    def test_video_list_returns_thumbnail_url(self):
        """Return an absolute URL for the thumbnail."""
        Video.objects.create(
            title="Test Movie", description="Test Description",
            category="Drama", thumbnail="thumbnail/test.jpg",
            processing_status=Video.ProcessingStatus.READY,
        )
        response = self.client.get(self.url)
        self.assertEqual(
            response.data[0]["thumbnail_url"],
            "http://testserver/media/thumbnail/test.jpg",
        )

    def test_missing_thumbnail_uses_fallback(self):
        """Return a default image when no thumbnail exists."""
        Video.objects.create(
            title="Demo", description="Test", category="Nature",
            processing_status=Video.ProcessingStatus.READY,
        )
        response = self.client.get(self.url)
        self.assertEqual(
            response.data[0]["thumbnail_url"],
            "http://testserver/static/default_thumbnail.svg",
        )

    def test_cleared_thumbnail_uses_fallback(self):
        """Return a default image after clearing the thumbnail."""
        video = Video.objects.create(
            title="Demo", description="Test", category="Nature",
            thumbnail="thumbnail/old.jpg",
            processing_status=Video.ProcessingStatus.READY,
        )
        video.thumbnail = ""
        video.save(update_fields=["thumbnail"])
        response = self.client.get(self.url)
        self.assertEqual(
            response.data[0]["thumbnail_url"],
            "http://testserver/static/default_thumbnail.svg",
        )

    def test_fallback_thumbnail_exists(self):
        """Ensure the fallback is shipped with the backend."""
        self.assertIsNotNone(
            finders.find("default_thumbnail.svg")
        )
