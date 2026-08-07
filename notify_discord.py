import sys
import os
import requests
import json

webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
if not webhook_url:
    print("No Discord webhook configured, skipping notification.")
    sys.exit(0)

status = sys.argv[1] if len(sys.argv) > 1 else "unknown"

if status == "success":
    video_url = ""
    if os.path.exists("output/upload_result.json"):
        with open("output/upload_result.json", "r") as f:
            result = json.load(f)
            video_url = result.get("url", "")

    title = ""
    if os.path.exists("output/content.json"):
        with open("output/content.json", "r") as f:
            content = json.load(f)
            title = content.get("title", "New video")

    message = f"✅ **New video uploaded!**\n**{title}**\n{video_url}"
else:
    message = "❌ **Daily video pipeline failed.** Check the Actions tab for details."

requests.post(webhook_url, json={"content": message})
print("Discord notification sent.")
