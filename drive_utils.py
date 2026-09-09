import os
import io
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service():
    creds_json = os.environ["GDRIVE_SERVICE_ACCOUNT_JSON"]
    creds_info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def list_queue_videos():
    service = get_drive_service()
    folder_id = os.environ["GDRIVE_FOLDER_ID"]
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed = false and mimeType contains 'video/'",
        fields="files(id, name, description, createdTime)",
        orderBy="createdTime",
        pageSize=1000,
    ).execute()
    return results.get("files", [])


def download_video(file_id, dest_path):
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(dest_path, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.close()


def get_video_credit(file_meta):
    desc = (file_meta.get("description") or "").strip()
    if desc:
        return desc
    name = file_meta.get("name", "")
    base = os.path.splitext(name)[0]
    return base if base else "Unknown Creator"
