from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from video_app.models import Video
from video_app.services import process_video


class VideoAdminTests(TestCase):
    """Test video management in Django Admin."""

    def setUp(self):
        """Log in as admin and isolate media files."""
        self.media_dir = TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        user = get_user_model().objects.create_superuser(
            username="admin@example.com",
            email="admin@example.com",
            password="SecurePassword123!",
        )
        self.client.force_login(user)

    def _create_saved_video(self):
        """Create a ready video with a custom thumbnail."""
        return Video.objects.create(
            title="Demo", description="Test video",
            category="Nature", thumbnail="thumbnail/custom.jpg",
            original_video="videos/old.mp4",
            processing_status=Video.ProcessingStatus.READY,
        )

    def _write_media(self, video):
        """Create isolated original, thumbnail, and HLS files."""
        root = Path(self.media_dir.name)
        original = root / video.original_video.name
        thumbnail = root / video.thumbnail.name
        segment = root / "hls" / str(video.pk) / "480p" / "000.ts"
        for path in (original, thumbnail, segment):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"test")
        return original, thumbnail, segment

    def _save_change(self, video, form=None, execute=True):
        """Save an edited video and capture commit callbacks."""
        with self.captureOnCommitCallbacks(execute=execute) as callbacks:
            admin.site._registry[Video].save_model(
                None, video, form, True
            )
        return callbacks

    def test_video_model_is_registered(self):
        """Make the Video model available in Django Admin."""
        self.assertTrue(admin.site.is_registered(Video))

    def test_admin_form_contains_video_fields(self):
        """Display the metadata and upload fields."""
        response = self.client.get(reverse("admin:video_app_video_add"))
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

    @patch("django_rq.get_queue")
    def test_metadata_update_does_not_enqueue(self, mock_get_queue):
        """Do not reconvert when only metadata changes."""
        video = self._create_saved_video()
        video.title = "New title"
        self._save_change(video)
        mock_get_queue.assert_not_called()

    @patch("django_rq.get_queue")
    def test_replacing_source_enqueues_processing(self, mock_get_queue):
        """Reconvert when the original video changes."""
        video = self._create_saved_video()
        video.original_video = "videos/new.mp4"
        self._save_change(video)
        mock_get_queue.return_value.enqueue.assert_called_once_with(
            process_video, video.pk
        )

    @patch("django_rq.get_queue")
    def test_replacement_cleans_old_media(self, mock_get_queue):
        """Remove obsolete source and HLS, preserving custom images."""
        video = self._create_saved_video()
        original, thumbnail, segment = self._write_media(video)
        video.original_video = "videos/new.mp4"
        self._save_change(video)
        video.refresh_from_db()
        self.assertEqual(video.processing_status, "pending")
        self.assertFalse(original.exists())
        self.assertFalse(segment.exists())
        self.assertTrue(thumbnail.exists())
        self.assertEqual(video.thumbnail.name, "thumbnail/custom.jpg")

    @patch("django_rq.get_queue")
    def test_replacement_resets_generated_thumbnail(self, mock_get_queue):
        """Regenerate an automatically created thumbnail."""
        video = self._create_saved_video()
        video.thumbnail = f"thumbnail/{video.pk}.jpg"
        video.save(update_fields=["thumbnail"])
        _, thumbnail, _ = self._write_media(video)
        video.original_video = "videos/new.mp4"
        self._save_change(video)
        video.refresh_from_db()
        self.assertFalse(video.thumbnail)
        self.assertFalse(thumbnail.exists())

    @patch("django_rq.get_queue")
    def test_removing_source_cleans_without_queue(self, mock_get_queue):
        """Remove obsolete media when the original is cleared."""
        video = self._create_saved_video()
        original, _, segment = self._write_media(video)
        video.original_video = ""
        self._save_change(video)
        video.refresh_from_db()
        self.assertEqual(video.processing_status, "pending")
        self.assertFalse(original.exists())
        self.assertFalse(segment.exists())
        mock_get_queue.assert_not_called()

    @patch("django_rq.get_queue")
    def test_replacement_cleanup_waits_for_commit(self, mock_get_queue):
        """Do not delete files before a transaction commits."""
        video = self._create_saved_video()
        original, _, segment = self._write_media(video)
        video.original_video = "videos/new.mp4"
        callbacks = self._save_change(video, execute=False)
        self.assertEqual(len(callbacks), 1)
        self.assertTrue(original.exists())
        self.assertTrue(segment.exists())
        mock_get_queue.assert_not_called()

    @patch("django_rq.get_queue")
    def test_same_filename_upload_starts_processing(self, mock_get_queue):
        """Detect replacements even when the filename is unchanged."""
        video = self._create_saved_video()
        original, _, segment = self._write_media(video)
        form = SimpleNamespace(changed_data=["original_video"])
        self._save_change(video, form=form)
        video.refresh_from_db()
        self.assertEqual(video.processing_status, "pending")
        self.assertTrue(original.exists())
        self.assertFalse(segment.exists())
        mock_get_queue.return_value.enqueue.assert_called_once_with(
            process_video, video.pk
        )

    @patch("django_rq.get_queue")
    def test_clearing_thumbnail_queues_regeneration(self, mock_queue):
        """Regenerate a removed thumbnail without resetting HLS."""
        video = self._create_saved_video()
        url = reverse("admin:video_app_video_change", args=[video.pk])
        data = {
            "title": video.title, "description": video.description,
            "category": video.category, "thumbnail-clear": "on",
            "_save": "Save",
        }
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        mock_queue.return_value.enqueue.assert_called_once()
        video.refresh_from_db()
        self.assertFalse(video.thumbnail)
        self.assertEqual(video.processing_status, "ready")

    @patch("django_rq.get_queue")
    def test_thumbnail_clear_without_source_skips_queue(self, mock_queue):
        """Avoid regeneration when no original video exists."""
        video = Video.objects.create(
            title="Demo", description="Test", category="Nature",
            thumbnail="thumbnail/custom.jpg",
        )
        video.thumbnail = ""
        form = SimpleNamespace(changed_data=["thumbnail"])
        self._save_change(video, form=form)
        mock_queue.assert_not_called()

    @patch("django_rq.get_queue")
    def test_thumbnail_replacement_skips_regeneration(self, mock_queue):
        """Keep a newly selected custom thumbnail."""
        video = self._create_saved_video()
        video.thumbnail = "thumbnail/replacement.jpg"
        form = SimpleNamespace(changed_data=["thumbnail"])
        self._save_change(video, form=form)
        mock_queue.assert_not_called()
