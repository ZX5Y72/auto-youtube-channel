import json
import os

STATE_PATH = "editor_queue_state.json"

DEFAULT_STATE = {
    "used_video_ids": [],
    "current_video_id": None,
    "current_video_name": None,
    "current_credit": None,
    "release_tag": None,
    "pending_clip_indices": []
}


def load_state():
    if not os.path.exists(STATE_PATH):
        return dict(DEFAULT_STATE)
    with open(STATE_PATH, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
