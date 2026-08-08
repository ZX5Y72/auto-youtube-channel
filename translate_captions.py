import json
import os
import re
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

if not os.path.exists("output/upload_result.json") or not os.path.exists("output/captions_en.srt"):
    print("Missing upload result or English captions, skipping translation.")
    exit(0)

with open("output/upload_result.json", "r") as f:
    upload_result = json.load(f)
video_id = upload_result["video_id"]

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-flash-latest")

with open("output/captions_en.srt", "r") as f:
    srt_content = f.read()

TARGET_LANG_CODE = "es"
TARGET_LANG_NAME = "Spanish"

translate_prompt = (
    f"Translate the spoken text lines in this SRT subtitle file into {TARGET_LANG_NAME}. "
    "Keep the numbering, timestamps, and format EXACTLY the same - only translate the actual "
    "subtitle text lines. Return ONLY the translated SRT file content, nothing else.\n\n"
    + srt_content
)

try:
    response = model.generate_content(translate_prompt)
    translated_srt = response.text.strip()
    translated_srt = re.sub(r"^```.*?\n", "", translated_srt)
    translated_srt = re.sub(r"\n```$", "", translated_srt)

    translated_path = f"output/captions_{TARGET_LANG_CODE}.srt"
    with open(translated_path, "w") as f:
        f.write(translated_srt)

    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    youtube = build("youtube", "v3", credentials=creds)

    youtube.captions().insert(
        part="snippet",
        body={
            "snippet": {
                "videoId": video_id,
                "language": TARGET_LANG_CODE,
                "name": TARGET_LANG_NAME,
                "isDraft": False,
            }
        },
        media_body=MediaFileUpload(translated_path),
    ).execute()

    print(f"{TARGET_LANG_NAME} captions uploaded successfully.")
except Exception as e:
    print(f"Caption translation/upload failed (non-critical): {e}")
