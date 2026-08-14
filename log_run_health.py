import sys
import json
import os
import datetime

channel = sys.argv[1] if len(sys.argv) > 1 else "unknown"
status = sys.argv[2] if len(sys.argv) > 2 else "unknown"

LOG_FILE = f"{channel}_health_log.json"

log = []
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r") as f:
        log = json.load(f)

log.append({
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    "status": status,
})
log = log[-100:]

with open(LOG_FILE, "w") as f:
    json.dump(log, f, indent=2)

print(f"Logged run: {channel} - {status}")
