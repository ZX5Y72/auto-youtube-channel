import json
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta

creds = Credentials(
    token=None,
    refresh_token=os.environ["YT_REFRESH_TOKEN"],
    client_id=os.environ["YT_CLIENT_ID"],
    client_secret=os.environ["YT_CLIENT_SECRET"],
    token_uri="https://oauth2.googleapis.com/token",
)

youtube = build("youtube", "v3", credentials=creds)
youtube_analytics = build("youtubeAnalytics", "v2", credentials=creds)

# Get your channel's uploaded videos (most recent 20)
channels_response = youtube.channels().list(part="contentDetails", mine=True).execute()
uploads_playlist_id = channels_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

playlist_response = youtube.playlistItems().list(
    part="snippet",
    playlistId=uploads_playlist_id,
    maxResults=20
).execute()

video_data = []
for item in playlist_response.get("items", []):
    video_id = item["snippet"]["resourceId"]["videoId"]
    title = item["snippet"]["title"]

    try:
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
        start_date = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")

        stats = youtube_analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="views,averageViewPercentage",
            dimensions="video",
            filters=f"video=={video_id}"
        ).execute()

        rows = stats.get("rows", [])
        if rows:
            views = rows[0][1]
            avg_pct = rows[0][2]
            video_data.append({"title": title, "views": views, "avg_view_percentage": avg_pct})
    except Exception as e:
        print(f"Could not fetch stats for '{title}': {e}")

# Sort by performance (views), best first
video_data.sort(key=lambda x: x["views"], reverse=True)

with open("video_performance.json", "w") as f:
    json.dump(video_data, f, indent=2)

print(f"Saved performance data for {len(video_data)} videos")
print(json.dumps(video_data[:5], indent=2))
