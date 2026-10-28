import subprocess
from pathlib import Path

from django.conf import settings

from video_app.models import Video


def _hls_command(source, folder, height):
    """Build the FFmpeg command for one HLS resolution."""
    return [
        "ffmpeg", "-nostdin", "-y", "-i", str(source),
        "-vf", f"scale=-2:{height}", "-c:v", "libx264",
        "-preset", "veryfast", "-threads", "2", "-c:a", "aac",
        "-f", "hls", "-hls_time", "4", "-hls_playlist_type", "vod",
        "-hls_segment_filename", str(folder / "%03d.ts"),
        str(folder / "index.m3u8"),
    ]


def convert_video_to_hls(source, movie_id, resolution):
    """Convert a video into an HLS playlist and TS segments."""
    heights = {"480p": 480, "720p": 720, "1080p": 1080}
    if resolution not in heights:
        raise ValueError("Unsupported resolution.")
    folder = Path(settings.MEDIA_ROOT) / "hls" / str(movie_id) / resolution
    folder.mkdir(parents=True, exist_ok=True)
    command = _hls_command(source, folder, heights[resolution])
    subprocess.run(command, check=True, timeout=180)


def generate_thumbnail(source, movie_id):
    """Extract a JPEG thumbnail from the video at second one."""
    folder = Path(settings.MEDIA_ROOT) / "thumbnail"
    folder.mkdir(parents=True, exist_ok=True)
    thumbnail = folder / f"{movie_id}.jpg"
    command = [
        "ffmpeg", "-nostdin", "-y", "-ss", "1",
        "-i", str(source), "-frames:v", "1", str(thumbnail),
    ]
    subprocess.run(command, check=True, timeout=30)
    return thumbnail

def regenerate_missing_thumbnail(movie_id):
    """Restore a missing thumbnail without converting HLS streams."""
    video = Video.objects.get(pk=movie_id)
    if not video.original_video or video.thumbnail:
        return
    thumbnail = generate_thumbnail(video.original_video.path, video.pk)
    video.thumbnail = Path(thumbnail).relative_to(
        settings.MEDIA_ROOT
    ).as_posix()
    video.save(update_fields=["thumbnail"])


def _process_video_files(video):
    """Generate a missing thumbnail and all HLS resolutions."""
    if not video.thumbnail:
        thumbnail = generate_thumbnail(video.original_video.path, video.pk)
        video.thumbnail = Path(thumbnail).relative_to(
            settings.MEDIA_ROOT
        ).as_posix()
        video.save(update_fields=["thumbnail"])
    for resolution in ("480p", "720p", "1080p"):
        convert_video_to_hls(video.original_video.path, video.pk, resolution)


def process_video(movie_id):
    """Track processing status and propagate conversion errors."""
    video = Video.objects.get(pk=movie_id)
    video.processing_status = Video.ProcessingStatus.PROCESSING
    video.save(update_fields=["processing_status"])
    try:
        _process_video_files(video)
    except Exception:
        video.processing_status = Video.ProcessingStatus.FAILED
        video.save(update_fields=["processing_status"])
        raise
    video.processing_status = Video.ProcessingStatus.READY
    video.save(update_fields=["processing_status"])
