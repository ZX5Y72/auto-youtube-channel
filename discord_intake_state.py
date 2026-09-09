import json
import os

STATE_PATH = "discord_intake_state.json"

DEFAULT_STATE = {
    "last_message_id": None,
    "creator_buffers": {},
    "all_submitted_video_ids": []
}


def load_state():
    if not os.path.exists(STATE_PATH):
        return dict(DEFAULT_STATE)
    with open(STATE_PATH, "r") as f:
        data = json.load(f)
    for key, val in DEFAULT_STATE.items():
        data.setdefault(key, val)
    return data


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
