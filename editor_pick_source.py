import os
import json
import subprocess
from editor_queue_state import load_state
from editor_batch_prepare import run_batch_prepare

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "10"))

os.makedirs("output", exist_ok=True)
os.makedirs("output/clip", exist_ok=True)


def set_output(name, value):
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(f"{name}={value}\n")


def gh(*args):
    return subprocess.run(["gh"] + list(args), capture_output=True, text=True)


state = load_state()

if not state.get("pending_clips"):
    print("Queue is empty, checking Drive for new videos...")
    added = run_batch_prepare(batch_size=BATCH_SIZE)
    if added > 0:
        state = load_state()

pending = state.get("pending_clips", [])

if not pending:
    print("No new videos found in Drive. Nothing to post today.")
    with open("output/queue_context.json", "w") as f:
        json.dump({"mode": "empty"}, f)
    set_output("mode", "empty")
    exit(0)

entry = pending[0]
video_id = entry["video_id"]
tag = entry["release_tag"]
idx = entry["clip_index"]
credit = state.get("video_credits", {}).get(video_id, "Unknown Creator")

gh("release", "download", tag, "-p", f"clip_{idx}.mp4", "-D", "output/clip", "--clobber")
gh("release", "download", tag, "-p", "clips_meta.json", "-D", "output", "--clobber")

os.replace(f"output/clip/clip_{idx}.mp4", "output/clip/raw_clip.mp4")

with open("output/clips_meta.json", "r") as f:
    meta = json.load(f)
clip_entry = next(c for c in meta if c["index"] == idx)

with open("output/clip_selection.json", "w") as f:
    json.dump(clip_entry, f, indent=2)

with open("output/queue_context.json", "w") as f:
    json.dump({"mode": "post", "credit": credit}, f)

set_output("mode", "post")
set_output("credit", credit)
print(f"Posting clip {idx} from video {video_id} (credit: {credit})")
