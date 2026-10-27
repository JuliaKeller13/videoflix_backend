from subprocess import CalledProcessError, TimeoutExpired
from unittest.mock import patch

from django.test import TestCase

from video_app.models import Video
from video_app.services import process_video


class VideoFailureTests(TestCase):
    """Test video processing status and error handling."""

    def setUp(self):
        """Create a video for processing tests."""
        self.video = Video.objects.create(
            title="Test Video", description="Test",
            category="Nature", thumbnail="thumbnail/custom.jpg",
            original_video="videos/test.mp4",
        )

    @patch("video_app.services.convert_video_to_hls")
    def test_ffmpeg_failure_sets_failed_status(self, mock_convert):
        """Save failed status without hiding the FFmpeg error."""
        mock_convert.side_effect = CalledProcessError(1, "ffmpeg")
        with self.assertRaises(CalledProcessError):
            process_video(self.video.pk)
        self.video.refresh_from_db()
        self.assertEqual(self.video.processing_status, "failed")

    @patch("video_app.services.convert_video_to_hls")
    def test_timeout_sets_failed_status(self, mock_convert):
        """Save failed status when FFmpeg exceeds its timeout."""
        mock_convert.side_effect = TimeoutExpired("ffmpeg", 180)
        with self.assertRaises(TimeoutExpired):
            process_video(self.video.pk)
        self.video.refresh_from_db()
        self.assertEqual(self.video.processing_status, "failed")

    @patch("video_app.services._process_video_files")
    def test_successful_status_transitions(self, mock_files):
        """Track pending, processing, and ready states."""
        statuses = [self.video.processing_status]

        def capture_processing(video):
            video.refresh_from_db()
            statuses.append(video.processing_status)

        mock_files.side_effect = capture_processing
        process_video(self.video.pk)
        self.video.refresh_from_db()
        statuses.append(self.video.processing_status)
        self.assertEqual(statuses, ["pending", "processing", "ready"])
