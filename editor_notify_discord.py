import sys
import os
import json
import requests

webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
if not webhook_url:
    print("No Discord webhook configured, skipping notification.")
    sys.exit(0)

status = sys.argv[1] if len(sys.argv) > 1 else "unknown"

if status == "duplicate":
    message = "⚠️ **Skipped** — this source video was already clipped before (duplicate original link)."
    requests.post(webhook_url, json={"content": message})
    print("Discord duplicate notification sent.")
    sys.exit(0)

if status == "success":
    url = ""
    publish_at = ""
    if os.path.exists("output/editor_upload_result.json"):
        with open("output/editor_upload_result.json", "r") as f:
            r = json.load(f)
            url = r.get("url", "")
            publish_at = r.get("publish_at", "")

    creator = ""
    original_link = ""
    if os.path.exists("output/clip_metadata.json"):
        with open("output/clip_metadata.json", "r") as f:
            m = json.load(f)
            creator = m.get("creator_handle", "")
            original_link = m.get("original_link", "")

    message = (
        f"✅ **New clip published!**\n"
        f"{url}\n"
        f"Creator: {creator}\n"
        f"Original: {original_link}"
    )
else:
    message = "❌ **Editor clip pipeline failed.** Check the Actions tab for details."

requests.post(webhook_url, json={"content": message})
print("Discord notification sent.")
