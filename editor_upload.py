import json
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

with open("output/clip_metadata.json", "r") as f:
    meta = json.load(f)

creds = Credentials(
    token=None,
    refresh_token=os.environ["EDITOR_YT_REFRESH_TOKEN"],
    client_id=os.environ["YT_CLIENT_ID"],
    client_secret=os.environ["YT_CLIENT_SECRET"],
    token_uri="https://oauth2.googleapis.com/token",
)

youtube = build("youtube", "v3", credentials=creds)

gemini_hashtags = [t for t in meta.get("hashtags", []) if t.lower() != "shorts"]
hashtags = "#Shorts " + " ".join(f"#{tag}" for tag in gemini_hashtags)
description = (
    f"{meta['description']}\n\n"
    f"🎬 Original creator: {meta['creator_handle']}\n"
    f"🔗 Watch the full video: {meta['original_link']}\n\n"
    f"Follow for more clips!\n\n"
    f"{hashtags}"
)

request_body = {
    "snippet": {
        "title": meta["title"],
        "description": description,
        "tags": meta.get("hashtags", []),
        "categoryId": "24",
    },
    "status": {
        "privacyStatus": "public",
        "selfDeclaredMadeForKids": False,
    },
}

media = MediaFileUpload("output/final_clip.mp4", chunksize=-1, resumable=True)
request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
response = request.execute()
video_id = response["id"]

print(f"Uploaded and published: https://youtube.com/watch?v={video_id}")

with open("output/editor_upload_result.json", "w") as f:
    json.dump({"url": f"https://youtube.com/watch?v={video_id}", "video_id": video_id}, f)

try:
    youtube.commentThreads().insert(
        part="snippet",
        body={
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {
                        "textOriginal": f"Credit to {meta['creator_handle']} for the original content! Full video linked in the description."
                    }
                },
            }
        },
    ).execute()
    print("Comment posted.")
except Exception as e:
    print(f"Auto-comment failed (non-critical): {e}")

def get_or_create_playlist(youtube, creator_handle):
    clean_name = creator_handle.lstrip("@").strip() or "Uncredited"
    playlists = youtube.playlists().list(part="snippet", mine=True, maxResults=50).execute()
    for pl in playlists.get("items", []):
        if pl["snippet"]["title"].lower() == clean_name.lower():
            return pl["id"]
    new_playlist = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {"title": clean_name, "description": f"Clips featuring {creator_handle}"},
            "status": {"privacyStatus": "public"},
        },
    ).execute()
    return new_playlist["id"]

try:
    playlist_id = get_or_create_playlist(youtube, meta["creator_handle"])
    youtube.playlistItems().insert(
        part="snippet",
        body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}},
    ).execute()
    print(f"Added to playlist: {meta['creator_handle']}")
except Exception as e:
    print(f"Playlist step failed (non-critical): {e}")
