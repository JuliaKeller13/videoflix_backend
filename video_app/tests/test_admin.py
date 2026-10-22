from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from video_app.models import Video
from video_app.services import process_video


class VideoAdminTests(TestCase):
    """Test video management in Django Admin."""

    def setUp(self):
        """Log in as an administrator."""
        user = get_user_model().objects.create_superuser(
            username="admin@example.com",
            email="admin@example.com",
            password="SecurePassword123!",
        )
        self.client.force_login(user)

    def test_video_model_is_registered(self):
        """Make the Video model available in Django Admin."""
        self.assertTrue(admin.site.is_registered(Video))

    def test_admin_form_contains_video_fields(self):
        """Display the metadata and upload fields."""
        url = reverse("admin:video_app_video_add")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        for field in ("title", "description", "category",
                      "thumbnail", "original_video"):
            self.assertContains(response, f'name="{field}"')

    @patch("django_rq.get_queue")
    def test_new_video_enqueues_processing(self, mock_get_queue):
        """Queue processing after saving a new video."""
        video = Video(
            title="Demo", description="Test video",
            category="Nature", thumbnail="thumbnail/demo.jpg",
            original_video="videos/demo.mp4",
        )
        video_admin = admin.site._registry[Video]
        with self.captureOnCommitCallbacks(execute=True):
            video_admin.save_model(None, video, None, False)
        mock_get_queue.assert_called_once_with("default")
        mock_get_queue.return_value.enqueue.assert_called_once_with(
            process_video, video.pk
        )

    @patch("django_rq.get_queue")
    def test_video_without_source_is_not_queued(self, mock_get_queue):
        """Skip processing when no original video exists."""
        video = Video(
            title="Demo", description="Test video",
            category="Nature", thumbnail="thumbnail/demo.jpg",
        )
        video_admin = admin.site._registry[Video]
        with self.captureOnCommitCallbacks(execute=True):
            video_admin.save_model(None, video, None, False)
        mock_get_queue.assert_not_called()