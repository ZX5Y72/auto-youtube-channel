import os
import json
import subprocess
from editor_queue_state import load_state, save_state
from drive_utils import list_queue_videos, download_video, get_video_credit

MAX_CLIP_DURATION = int(os.environ.get("MAX_CLIP_DURATION", "59"))

os.makedirs("output", exist_ok=True)
os.makedirs("output/clip", exist_ok=True)

state = load_state()


def set_output(name, value):
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(f"{name}={value}\n")


def gh(*args):
    result = subprocess.run(["gh"] + list(args), capture_output=True, text=True)
    return result


if state["pending_clip_indices"]:
    idx = state["pending_clip_indices"][0]
    tag = state["release_tag"]

    gh("release", "download", tag, "-p", f"clip_{idx}.mp4", "-D", "output/clip", "--clobber")
    gh("release", "download", tag, "-p", "clips_meta.json", "-D", "output", "--clobber")

    os.replace(f"output/clip/clip_{idx}.mp4", "output/clip/raw_clip.mp4")

    with open("output/clips_meta.json", "r") as f:
        meta = json.load(f)
    entry = next(c for c in meta if c["index"] == idx)

    with open("output/clip_selection.json", "w") as f:
        json.dump(entry, f, indent=2)

    with open("output/queue_context.json", "w") as f:
        json.dump({"mode": "continue", "credit": state["current_video_name_credit"]}, f)

    set_output("mode", "continue")
    set_output("credit", state["current_video_name_credit"])
    print(f"Continuing queue: video={state['current_video_name']}, clip index={idx}")

else:
    videos = list_queue_videos()
    remaining = [v for v in videos if v["id"] not in state["used_video_ids"]]

    if not remaining:
        print("No unused videos left in Drive queue.")
        with open("output/queue_context.json", "w") as f:
            json.dump({"mode": "empty"}, f)
        set_output("mode", "empty")
        exit(0)

    video = remaining[0]
    credit = get_video_credit(video)

    download_video(video["id"], "output/source_video.mp4")

    state["current_video_id"] = video["id"]
    state["current_video_name"] = video["name"]
    state["current_video_name_credit"] = credit
    state["used_video_ids"].append(video["id"])
    state["release_tag"] = f"editorqueue-{video['id']}"
    state["pending_clip_indices"] = []
    save_state(state)

    with open("output/queue_context.json", "w") as f:
        json.dump({"mode": "new_video", "credit": credit}, f)

    set_output("mode", "new_video")
    set_output("credit", credit)
    print(f"Starting new video: {video['name']} (credit: {credit})")
