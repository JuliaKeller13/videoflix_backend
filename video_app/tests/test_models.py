from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.core.exceptions import ValidationError
from django.forms import Select

from video_app.forms import VideoAdminForm
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

    def test_str_returns_video_title(self):
        """Represent a video by its title."""
        video = Video(
            title="Test Movie",
            description="Test Description",
            category="Drama",
        )
        self.assertEqual(str(video), "Test Movie")

    def test_category_has_predefined_choices(self):
        """Preserve existing categories in the fixed choices."""
        choices = Video._meta.get_field("category").choices or []
        self.assertIn(("Nature", "Nature"), choices)
        self.assertIn(("Action", "Action"), choices)
        self.assertIn(("Drama", "Drama"), choices)

    def test_invalid_category_is_rejected(self):
        """Reject arbitrary category names."""
        video = Video(
            title="Demo", description="Test", category="ASD",
        )
        with self.assertRaises(ValidationError):
            video.full_clean()

    def test_admin_category_uses_dropdown(self):
        """Offer a dropdown instead of a free-text input."""
        field = VideoAdminForm.base_fields["category"]
        self.assertIsInstance(field.widget, Select)