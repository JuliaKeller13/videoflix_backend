import subprocess
from pathlib import Path

from django.conf import settings

from video_app.models import Video


def convert_video_to_hls(source, movie_id, resolution):
    """Convert a video into an HLS playlist and TS segments."""
    heights = {"480p": 480, "720p": 720, "1080p": 1080}
    if resolution not in heights:
        raise ValueError("Unsupported resolution.")
    folder = Path(settings.MEDIA_ROOT) / "hls" / str(movie_id) / resolution
    folder.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-nostdin", "-y", "-i", str(source),
        "-vf", f"scale=-2:{heights[resolution]}", "-c:v", "libx264",
        "-preset", "veryfast", "-threads", "2", "-c:a", "aac",
        "-f", "hls", "-hls_time", "4", "-hls_playlist_type", "vod",
        "-hls_segment_filename", str(folder / "%03d.ts"),
        str(folder / "index.m3u8"),
    ]
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


def process_video(movie_id):
    """Generate a missing thumbnail and convert the video to HLS."""
    video = Video.objects.get(pk=movie_id)
    if not video.thumbnail:
        thumbnail = generate_thumbnail(video.original_video.path, movie_id)
        video.thumbnail = Path(thumbnail).relative_to(
            settings.MEDIA_ROOT
        ).as_posix()
        video.save(update_fields=["thumbnail"])
    for resolution in ("480p", "720p", "1080p"):
        convert_video_to_hls(
            video.original_video.path, movie_id, resolution
        )
