from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from video_app.models import Video


class VideoModelTests(TestCase):
    """Test storage of original videos and thumbnails."""

    def setUp(self):
        """Use isolated storage for uploaded test files."""
        self.media_dir = TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

    def test_video_saves_original_file(self):
        """Store an uploaded video in the videos directory."""
        upload = SimpleUploadedFile(
            "sample.mp4", b"test video data", content_type="video/mp4"
        )
        video = Video.objects.create(
            title="Test Movie", description="Test Description",
            category="Drama", thumbnail="thumbnail/test.jpg",
            original_video=upload,
        )
        self.assertEqual(video.original_video.name, "videos/sample.mp4")
        self.assertTrue(
            video.original_video.storage.exists(video.original_video.name)
        )

    def test_original_video_is_optional(self):
        """Allow existing video records without an original file."""
        video = Video.objects.create(
            title="Test Movie", description="Test Description",
            category="Drama", thumbnail="thumbnail/test.jpg",
        )
        self.assertFalse(video.original_video)

    def test_thumbnail_can_be_omitted(self):
        """Allow videos without an uploaded thumbnail."""
        video = Video(
            title="Test Movie",
            description="Thumbnail will be generated",
            category="Nature",
            original_video="videos/demo.mp4",
        )
        video.full_clean()
        self.assertFalse(video.thumbnail)
