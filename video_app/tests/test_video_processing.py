
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from video_app.services import convert_video_to_hls


class VideoProcessingTests(SimpleTestCase):
    """Test FFmpeg-based HLS video processing."""

    @patch("video_app.services.subprocess.run")
    def test_convert_video_to_480p(self, mock_run):
        """Build the 480p HLS command and output folder."""
        with TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            source = Path(root) / "original.mp4"
            convert_video_to_hls(source, 1, "480p")
            folder = Path(root) / "hls" / "1" / "480p"
            self.assertTrue(folder.is_dir())
            command = mock_run.call_args.args[0]
            self.assertEqual(command[:4], ["ffmpeg", "-y", "-i", str(source)])
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
