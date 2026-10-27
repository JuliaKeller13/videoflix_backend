from io import BytesIO

from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from video_app.forms import VideoAdminForm
from video_app.models import Video


class UploadValidationTests(TestCase):
    """Test video and thumbnail uploads in Django Admin."""

    def _form(self, video=None, thumbnail=None):
        """Create a bound video form with optional uploads."""
        files = {}
        if video is not None:
            files["original_video"] = video
        if thumbnail is not None:
            files["thumbnail"] = thumbnail
        data = {
            "title": "Demo", "description": "Test", "category": "Nature",
        }
        return VideoAdminForm(data=data, files=files)

    def _video(self, name="demo.mp4", content=b"\x00\x00\x00\x18ftypisom"):
        """Create a small simulated MP4 upload."""
        return SimpleUploadedFile(
            name, content, content_type="video/mp4"
        )

    def _thumbnail(self, name="poster.png"):
        """Create a valid PNG image in memory."""
        buffer = BytesIO()
        Image.new("RGB", (2, 2)).save(buffer, format="PNG")
        return SimpleUploadedFile(
            name, buffer.getvalue(), content_type="image/png"
        )

    def test_admin_uses_upload_validation_form(self):
        """Register the validating form in Django Admin."""
        self.assertIs(admin.site._registry[Video].form, VideoAdminForm)

    def test_processing_status_cannot_be_edited(self):
        """Reserve processing status for background jobs."""
        self.assertNotIn("processing_status", VideoAdminForm.base_fields)

    def test_uploads_are_optional(self):
        """Allow video metadata without uploaded files."""
        form = self._form()
        self.assertTrue(form.is_valid(), form.errors)

    def test_accepts_mp4(self):
        """Accept a video with an MP4 filename and header."""
        form = self._form(video=self._video())
        self.assertTrue(form.is_valid(), form.errors)

    def test_accepts_uppercase_mp4_extension(self):
        """Treat video extensions case-insensitively."""
        form = self._form(video=self._video(name="demo.MP4"))
        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_wrong_video_extension(self):
        """Reject files that are not named MP4."""
        form = self._form(video=self._video(name="demo.exe"))
        self.assertIn("original_video", form.errors)

    def test_rejects_invalid_mp4_header(self):
        """Reject renamed files without an MP4 header."""
        video = self._video(content=b"not a real mp4 file")
        form = self._form(video=video)
        self.assertIn("original_video", form.errors)

    def test_rejects_oversized_video(self):
        """Limit original video uploads to 200 MiB."""
        video = self._video()
        video.size = 200 * 1024 * 1024 + 1
        form = self._form(video=video)
        self.assertIn("original_video", form.errors)

    def test_video_validation_preserves_file_position(self):
        """Restore the upload position after reading the header."""
        video = self._video()
        video.seek(3)
        form = self._form(video=video)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(video.tell(), 3)

    def test_accepts_valid_thumbnail(self):
        """Accept a valid PNG thumbnail."""
        form = self._form(thumbnail=self._thumbnail())
        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_unsupported_thumbnail_extension(self):
        """Reject thumbnail formats outside the allowlist."""
        form = self._form(thumbnail=self._thumbnail("poster.gif"))
        self.assertIn("thumbnail", form.errors)

    def test_rejects_oversized_thumbnail(self):
        """Limit uploaded thumbnails to 5 MiB."""
        thumbnail = self._thumbnail()
        thumbnail.size = 5 * 1024 * 1024 + 1
        form = self._form(thumbnail=thumbnail)
        self.assertIn("thumbnail", form.errors)

    def test_rejects_corrupt_thumbnail(self):
        """Reject image uploads with invalid contents."""
        thumbnail = SimpleUploadedFile(
            "poster.png", b"not an image", content_type="image/png"
        )
        form = self._form(thumbnail=thumbnail)
        self.assertIn("thumbnail", form.errors)
