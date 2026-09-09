import re
import subprocess

YOUTUBE_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})"
)


def extract_video_ids(text):
    """Return all unique YouTube video IDs found in a block of text, in order."""
    seen = []
    for match in YOUTUBE_URL_RE.finditer(text):
        vid = match.group(1)
        if vid not in seen:
            seen.append(vid)
    return seen


def download_youtube_video(video_id, dest_path):
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--merge-output-format", "mp4",
        "-o", dest_path,
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed for {video_id}: {result.stderr[-1500:]}")
