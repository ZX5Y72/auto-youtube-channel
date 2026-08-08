import os
import requests
import datetime

GH_TOKEN = os.environ["GH_TOKEN"]
REPO = os.environ["REPO"]
WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]

since = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

url = f"https://api.github.com/repos/{REPO}/actions/workflows/daily.yml/runs"
headers = {"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json"}
params = {"created": f">={since}", "per_page": 50}

response = requests.get(url, headers=headers, params=params)
runs = response.json().get("workflow_runs", [])

success = sum(1 for r in runs if r.get("conclusion") == "success")
failed = sum(1 for r in runs if r.get("conclusion") == "failure")
total = len(runs)

message = (
    f"📊 **Weekly Channel Digest**\n"
    f"Runs this week: {total}\n"
    f"✅ Successful: {success}\n"
    f"❌ Failed: {failed}"
)

requests.post(WEBHOOK, json={"content": message})
print("Weekly digest sent.")
