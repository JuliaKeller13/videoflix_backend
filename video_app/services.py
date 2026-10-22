
import subprocess
from pathlib import Path

from django.conf import settings


def convert_video_to_hls(source, movie_id, resolution):
    """Convert a video into an HLS playlist and TS segments."""
    heights = {"480p": 480, "720p": 720, "1080p": 1080}
    if resolution not in heights:
        raise ValueError("Unsupported resolution.")
    folder = Path(settings.MEDIA_ROOT) / "hls" / str(movie_id) / resolution
    folder.mkdir(parents=True, exist_ok=True)
    command = ["ffmpeg", "-y", "-i", str(source), "-vf",
               f"scale=-2:{heights[resolution]}", "-c:v", "libx264",
               "-c:a", "aac", "-f", "hls", "-hls_time", "4",
               "-hls_playlist_type", "vod",
               "-hls_segment_filename", str(folder / "%03d.ts"),
               str(folder / "index.m3u8")]
    subprocess.run(command, check=True)
