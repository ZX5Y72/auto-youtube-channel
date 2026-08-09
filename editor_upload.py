import json
import os
import datetime
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

hashtags = " ".join(f"#{tag}" for tag in meta.get("hashtags", []))
description = (
    f"{meta['description']}\n\n"
    f"🎬 Original creator: {meta['creator_handle']}\n"
    f"🔗 Watch the full video: {meta['original_link']}\n\n"
    f"Follow for more clips!\n\n"
    f"{hashtags}"
)

now = datetime.datetime.utcnow()
publish_time = now.replace(hour=15, minute=0, second=0, microsecond=0)
if now >= publish_time:
    publish_time += datetime.timedelta(days=1)
publish_iso = publish_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")

request_body = {
    "snippet": {
        "title": meta["title"],
        "description": description,
        "tags": meta.get("hashtags", []),
        "categoryId": "24",
    },
    "status": {
        "privacyStatus": "private",
        "publishAt": publish_iso,
        "selfDeclaredMadeForKids": False,
    },
}

media = MediaFileUpload("output/final_clip.mp4", chunksize=-1, resumable=True)
request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
response = request.execute()
video_id = response["id"]

print(f"Uploaded and scheduled for {publish_iso}: https://youtube.com/watch?v={video_id}")

with open("output/editor_upload_result.json", "w") as f:
    json.dump({"url": f"https://youtube.com/watch?v={video_id}", "video_id": video_id,
               "publish_at": publish_iso}, f)
