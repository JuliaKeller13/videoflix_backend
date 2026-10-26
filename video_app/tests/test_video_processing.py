from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings

from video_app import services
from video_app.models import Video
from video_app.services import convert_video_to_hls, process_video


class VideoProcessingTests(SimpleTestCase):
    """Test FFmpeg-based video processing."""

    @patch("video_app.services.subprocess.run")
    def test_convert_video_to_480p(self, mock_run):
        """Build the 480p HLS command and output folder."""
        with TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            source = Path(root) / "original.mp4"
            convert_video_to_hls(source, 1, "480p")
            folder = Path(root) / "hls" / "1" / "480p"
            self.assertTrue(folder.is_dir())
            command = mock_run.call_args.args[0]
            self.assertIn(str(source), command)
            self.assertIn("scale=-2:480", command)
            self.assertIn(str(folder / "%03d.ts"), command)
            self.assertEqual(command[-1], str(folder / "index.m3u8"))
            self.assertTrue(mock_run.call_args.kwargs["check"])

    @patch("video_app.services.subprocess.run")
    def test_rejects_unknown_resolution(self, mock_run):
        """Reject unsupported resolutions without starting FFmpeg."""
        with TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            with self.assertRaises(ValueError):
                convert_video_to_hls("original.mp4", 1, "360p")
        mock_run.assert_not_called()

    @patch("video_app.services.subprocess.run")
    def test_ffmpeg_uses_safe_background_settings(self, mock_run):
        """Use fast encoding and limit execution time."""
        with TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            convert_video_to_hls("original.mp4", 1, "480p")
        command = mock_run.call_args.args[0]
        self.assertIn("-nostdin", command)
        self.assertEqual(command[command.index("-preset") + 1], "veryfast")
        self.assertEqual(command[command.index("-threads") + 1], "2")
        self.assertEqual(mock_run.call_args.kwargs["timeout"], 180)

    @patch("video_app.services.subprocess.run")
    def test_generate_thumbnail(self, mock_run):
        """Extract one JPEG frame from a video."""
        with TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            source = Path(root) / "original.mp4"
            thumbnail = services.generate_thumbnail(source, 1)
            self.assertEqual(thumbnail, Path(root) / "thumbnail" / "1.jpg")
            self.assertTrue(thumbnail.parent.is_dir())
            command = mock_run.call_args.args[0]
            self.assertIn("-nostdin", command)
            self.assertIn(str(source), command)
            self.assertEqual(command[command.index("-frames:v") + 1], "1")
            self.assertEqual(command[-1], str(thumbnail))
            self.assertTrue(mock_run.call_args.kwargs["check"])
            self.assertEqual(mock_run.call_args.kwargs["timeout"], 30)


class VideoJobTests(TestCase):
    """Test video conversion jobs."""

    @patch("video_app.services.convert_video_to_hls")
    def test_process_video_converts_all_resolutions(self, mock_convert):
        """Convert a stored video into three resolutions."""
        video = Video.objects.create(
            title="Demo", description="Test video",
            category="Nature", thumbnail="thumbnail/demo.jpg",
            original_video="videos/demo.mp4",
        )
        process_video(video.pk)
        source = video.original_video.path
        for resolution in ("480p", "720p", "1080p"):
            mock_convert.assert_any_call(source, video.pk, resolution)
        self.assertEqual(mock_convert.call_count, 3)

    @patch("video_app.services.generate_thumbnail")
    @patch("video_app.services.convert_video_to_hls")
    def test_missing_thumbnail_is_generated(self, mock_hls, mock_image):
        """Generate and save a thumbnail when none exists."""
        video = Video.objects.create(
            title="Demo", description="Test",
            category="Nature", original_video="videos/demo.mp4",
        )
        mock_image.return_value = (
            Path(settings.MEDIA_ROOT) / "thumbnail" / f"{video.pk}.jpg"
        )
        process_video(video.pk)
        mock_image.assert_called_once_with(video.original_video.path, video.pk)
        video.refresh_from_db()
        self.assertEqual(video.thumbnail.name, f"thumbnail/{video.pk}.jpg")

    @patch("video_app.services.generate_thumbnail")
    @patch("video_app.services.convert_video_to_hls")
    def test_existing_thumbnail_is_preserved(self, mock_hls, mock_image):
        """Keep an existing thumbnail without generating another."""
        video = Video.objects.create(
            title="Demo", description="Test",
            category="Nature", thumbnail="thumbnail/custom.jpg",
            original_video="videos/demo.mp4",
        )
        process_video(video.pk)
        mock_image.assert_not_called()
        video.refresh_from_db()
        self.assertEqual(video.thumbnail.name, "thumbnail/custom.jpg")
