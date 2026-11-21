
import os
import io
import json

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload


SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/youtube.upload",
]


def services():
    creds = Credentials(
        None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=SCOPES,
    )

    creds.refresh(Request())

    return build(
        "drive",
        "v3",
        credentials=creds,
        cache_discovery=False,
    )


def list_children(service, folder_id):
    query = f"'{folder_id}' in parents and trashed=false"

    output = []
    page_token = None

    while True:
        response = service.files().list(
            q=query,
            fields="nextPageToken,files(id,name,mimeType,size)",
            pageSize=1000,
            pageToken=page_token,
        ).execute()

        output.extend(response.get("files", []))
        page_token = response.get("nextPageToken")

        if not page_token:
            return output


def find_job_folder(service, job_id):
    inbox = os.environ["DRIVE_INBOX_FOLDER_ID"]

    for item in list_children(service, inbox):
        if (
            item["name"] == job_id
            and item["mimeType"] == "application/vnd.google-apps.folder"
        ):
            return item["id"]

    raise RuntimeError(
        f"Drive folder INBOX/{job_id} not found"
    )


def download_file(service, file_id, path):
    request = service.files().get_media(fileId=file_id)

    with open(path, "wb") as file:
        downloader = MediaIoBaseDownload(file, request)

        done = False

        while not done:
            _, done = downloader.next_chunk()


def upload_file(
    service,
    path,
    name,
    parent_id,
    mime="video/mp4",
):
    media = MediaFileUpload(
        path,
        mimetype=mime,
        resumable=True,
    )

    result = service.files().create(
        body={
            "name": name,
            "parents": [parent_id],
        },
        media_body=media,
        fields="id,name,webViewLink",
    ).execute()

    return result


def create_folder(service, name, parent_id):
    for item in list_children(service, parent_id):
        if (
            item["name"] == name
            and item["mimeType"] == "application/vnd.google-apps.folder"
        ):
            return item["id"]

    return service.files().create(
        body={
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        },
        fields="id",
    ).execute()["id"]


def upload_json(service, data, name, parent_id):
    from googleapiclient.http import MediaInMemoryUpload

    media = MediaInMemoryUpload(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
        mimetype="application/json",
        resumable=False,
    )

    # Replace an existing file with the same name.
    for item in list_children(service, parent_id):
        if item["name"] == name:
            service.files().delete(
                fileId=item["id"]
            ).execute()

    return service.files().create(
        body={
            "name": name,
            "parents": [parent_id],
        },
        media_body=media,
        fields="id,name",
    ).execute()
