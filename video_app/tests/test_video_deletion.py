from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings

from video_app.models import Video


class VideoDeletionTests(TestCase):
    """Test cleanup of files belonging to deleted videos."""

    def setUp(self):
        """Create a video using temporary media storage."""
        self.media_dir = TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.video = Video.objects.create(
            title="Demo", description="Test", category="Nature",
            thumbnail="thumbnail/demo.jpg",
            original_video="videos/demo.mp4",
        )

    def create_media_files(self):
        """Create original, thumbnail, and HLS test files."""
        root = Path(self.media_dir.name)
        paths = (
            root / self.video.original_video.name,
            root / self.video.thumbnail.name,
            root / "hls" / str(self.video.pk) / "480p" / "000.ts",
        )
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"test data")
        return paths

    def test_deletion_removes_media_files(self):
        """Remove video files after a successful deletion."""
        paths = self.create_media_files()
        with self.captureOnCommitCallbacks(execute=True):
            self.video.delete()
        for path in paths:
            self.assertFalse(path.exists())

    def test_cleanup_waits_for_commit(self):
        """Keep files until the transaction is committed."""
        paths = self.create_media_files()
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            self.video.delete()
        self.assertEqual(len(callbacks), 1)
        for path in paths:
            self.assertTrue(path.exists())

    def test_deletion_without_files_succeeds(self):
        """Allow deletion when no media files are assigned."""
        self.video.original_video = ""
        self.video.thumbnail = ""
        self.video.save(update_fields=["original_video", "thumbnail"])
        with self.captureOnCommitCallbacks(execute=True):
            self.video.delete()
        self.assertFalse(Video.objects.filter(pk=self.video.pk).exists())
