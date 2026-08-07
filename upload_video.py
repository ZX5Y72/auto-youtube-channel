import json
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

with open("output/content.json", "r") as f:
    data = json.load(f)

creds = Credentials(
    token=None,
    refresh_token=os.environ["YT_REFRESH_TOKEN"],
    client_id=os.environ["YT_CLIENT_ID"],
    client_secret=os.environ["YT_CLIENT_SECRET"],
    token_uri="https://oauth2.googleapis.com/token",
)

youtube = build("youtube", "v3", credentials=creds)

hashtags = " ".join(f"#{tag}" for tag in data["hashtags"])
description = f"{data['description']}\n\n{hashtags}"

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

request = youtube.videos().insert(
    part="snippet,status",
    body=request_body,
    media_body=media,
)

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
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        },
    ).execute()
    print(f"Added to playlist: {data['civilization']}")
except Exception as e:
    print(f"Playlist step failed (non-critical): {e}")
