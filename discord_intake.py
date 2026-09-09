import os
import re
import json
import requests
from discord_intake_state import load_state, save_state
from youtube_link_utils import extract_video_ids
from editor_queue_state import load_state as load_editor_state, save_state as save_editor_state

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CHANNEL_ID = os.environ["DISCORD_INTAKE_CHANNEL_ID"]
BATCH_TARGET = 20

API_BASE = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
HEADERS = {"Authorization": f"Bot {BOT_TOKEN}"}

CONSENT_PATTERNS = [
    "i consent", "we consent", "give permission", "we give permission",
    "i give permission", "consent to clip", "we authorize", "i authorize",
]

HANDLE_RE = re.compile(r"@(\w+)")


def has_consent(text):
    lowered = text.lower()
    return any(p in lowered for p in CONSENT_PATTERNS)


def extract_handle(text):
    match = HANDLE_RE.search(text)
    return match.group(1) if match else None


def fetch_new_messages(after_id):
    params = {"limit": 100}
    if after_id:
        params["after"] = after_id
    resp = requests.get(API_BASE, headers=HEADERS, params=params)
    resp.raise_for_status()
    messages = resp.json()
    return sorted(messages, key=lambda m: int(m["id"]))


def send_reply(text):
    requests.post(API_BASE, headers=HEADERS, json={"content": text})


def main():
    state = load_state()
    messages = fetch_new_messages(state["last_message_id"])

    if not messages:
        print("No new messages.")
        return

    editor_state = load_editor_state()
    editor_state.setdefault("youtube_creator_batches", [])

    for msg in messages:
        state["last_message_id"] = msg["id"]
        content = msg.get("content", "")

        if not has_consent(content):
            continue

        handle = extract_handle(content)
        if not handle:
            send_reply("Consent noted, but please include the creator's channel handle (e.g. @MrBeast) in the same message.")
            continue

        video_ids = extract_video_ids(content)
        if not video_ids:
            send_reply(f"@{handle} — consent and handle received, but no YouTube links were found in that message.")
            continue

        buffer = state["creator_buffers"].setdefault(handle, [])
        duplicates = []
        added = []

        for vid in video_ids:
            if len(buffer) >= BATCH_TARGET:
                break
            if vid in state["all_submitted_video_ids"]:
                duplicates.append(vid)
                continue
            if vid in buffer:
                continue
            buffer.append(vid)
            state["all_submitted_video_ids"].append(vid)
            added.append(vid)

        if duplicates:
            dup_list = ", ".join(f"https://youtu.be/{v}" for v in duplicates)
            send_reply(f"@{handle} legal team, please send a different link instead of: {dup_list} — already clipped.")

        if added:
            send_reply(f"@{handle}: {len(added)} new link(s) received ({len(buffer)}/{BATCH_TARGET} for this batch).")

        if len(buffer) >= BATCH_TARGET:
            editor_state["youtube_creator_batches"].append({
                "creator": handle,
                "video_ids": buffer[:BATCH_TARGET],
                "status": "pending"
            })
            state["creator_buffers"][handle] = []
            send_reply(f"✅ @{handle}: got {BATCH_TARGET} videos, clipping will begin shortly.")

    save_state(state)
    save_editor_state(editor_state)


if __name__ == "__main__":
    main()
