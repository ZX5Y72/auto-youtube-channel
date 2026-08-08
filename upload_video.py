import json
import os
import subprocess
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

with open("output/content.json", "r") as f:
    data = json.load(f)

# --- Duration sanity check ---
file_size = os.path.getsize("output/final_video.mp4") if os.path.exists("output/final_video.mp4") else 0
print(f"final_video.mp4 size: {file_size} bytes")

probe = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrapper=1:nokey=1", "output/final_video.mp4"],
    capture_output=True, text=True
)
print(f"ffprobe stdout: '{probe.stdout.strip()}'")
print(f"ffprobe stderr: '{probe.stderr.strip()}'")

try:
    duration = float(probe.stdout.strip())
except (ValueError, TypeError):
    duration = 0

# Fall back to file size as a sanity check if ffprobe couldn't read duration
if duration == 0 and file_size > 500_000:
    print("ffprobe couldn't read duration but file size looks reasonable, proceeding anyway.")
elif duration < 15 or duration > 180:
    raise RuntimeError(f"Final video duration ({duration:.1f}s, file size {file_size} bytes) is outside sane bounds, aborting upload.")
else:
    print(f"Duration check passed: {duration:.1f}s")

creds = Credentials(
    token=None,
    refresh_token=os.environ["YT_REFRESH_TOKEN"],
    client_id=os.environ["YT_CLIENT_ID"],
    client_secret=os.environ["YT_CLIENT_SECRET"],
    token_uri="https://oauth2.googleapis.com/token",
)

youtube = build("youtube", "v3", credentials=creds)

hashtags = " ".join(f"#{tag}" for tag in data["hashtags"])
transcript_note = f"\n\nFull transcript:\n{data['script']}"
engagement_note = "\n\nWhich civilization should I cover next? Let me know in the comments!"
description = f"{data['description']}{engagement_note}\n\n{hashtags}{transcript_note}"

request_body = {
    "snippet": {
        "title": data["title"],
        "description": description,
        "tags": data["hashtags"],
        "categoryId": "27",
    },
    "status": {
        "privacyStatus": "public",
        "selfDeclaredMadeForKids": False,
    },
}

media = MediaFileUpload("output/final_video.mp4", chunksize=-1, resumable=True)
request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
response = request.execute()
video_id = response["id"]
print(f"Uploaded! https://youtube.com/watch?v={video_id}")

with open("output/upload_result.json", "w") as f:
    json.dump({"url": f"https://youtube.com/watch?v={video_id}", "video_id": video_id}, f)

try:
    youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload("output/thumbnail.jpg")
    ).execute()
    print("Thumbnail set.")
except Exception as e:
    print(f"Thumbnail upload skipped/failed (this is OK): {e}")

def get_or_create_playlist(youtube, civilization_name):
    playlists = youtube.playlists().list(part="snippet", mine=True, maxResults=50).execute()
    for pl in playlists.get("items", []):
        if pl["snippet"]["title"].lower() == civilization_name.lower():
            return pl["id"]
    new_playlist = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {"title": civilization_name, "description": f"History of {civilization_name}"},
            "status": {"privacyStatus": "public"},
        },
    ).execute()
    return new_playlist["id"]

try:
    playlist_id = get_or_create_playlist(youtube, data["civilization"])
    youtube.playlistItems().insert(
        part="snippet",
        body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}},
    ).execute()
    print(f"Added to playlist: {data['civilization']}")
except Exception as e:
    print(f"Playlist step failed (non-critical): {e}")

# --- Auto comment (not pinned - YouTube API doesn't support pinning) ---
try:
    youtube.commentThreads().insert(
        part="snippet",
        body={
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {"textOriginal": "Subscribe for a new ancient history fact every day! 🏛️"}
                },
            }
        },
    ).execute()
    print("Comment posted.")
except Exception as e:
    print(f"Auto-comment failed (non-critical): {e}")
