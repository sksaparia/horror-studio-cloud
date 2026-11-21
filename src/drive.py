
import os
import re
import tempfile
from pathlib import Path

import requests

from src.drive import (
    services,
    find_job_folder,
    list_children,
    upload_file,
)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
JOB_ID = os.environ["JOB_ID"]
FILE_ID = os.environ["TELEGRAM_FILE_ID"]
SCENE_NUMBER = os.environ["SCENE_NUMBER"]


def validate_inputs():
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", JOB_ID):
        raise ValueError("Invalid job ID.")

    if not SCENE_NUMBER.isdigit():
        raise ValueError("Scene number must be numeric.")

    scene = int(SCENE_NUMBER)

    if scene < 1 or scene > 5:
        raise ValueError("Scene number must be between 1 and 5.")

    if not FILE_ID:
        raise ValueError("Telegram file ID is missing.")

    return scene


def get_telegram_file():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile"

    response = requests.get(
        url,
        params={"file_id": FILE_ID},
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(f"Telegram getFile failed: {data}")

    file_info = data["result"]
    file_path = file_info["file_path"]
    file_size = int(file_info.get("file_size", 0))

    # Telegram hosted Bot API download limit is 20 MB.
    if file_size > 20 * 1024 * 1024:
        raise RuntimeError(
            "This clip exceeds Telegram's hosted Bot API download limit "
            "of 20 MB. Use a smaller export or another transfer method."
        )

    return file_path


def download_telegram_video(file_path, destination):
    url = (
        f"https://api.telegram.org/file/bot"
        f"{BOT_TOKEN}/{file_path}"
    )

    total = 0
    max_bytes = 20 * 1024 * 1024

    with requests.get(url, stream=True, timeout=(30, 180)) as response:
        response.raise_for_status()

        with open(destination, "wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue

                total += len(chunk)

                if total > max_bytes:
                    raise RuntimeError("Downloaded clip exceeds 20 MB.")

                output.write(chunk)

    if total == 0:
        raise RuntimeError("Downloaded video is empty.")


def save_to_drive(scene, local_path):
    drive = services()
    folder_id = find_job_folder(drive, JOB_ID)

    filename = f"scene_{scene:02d}.mp4"

    # Replace an existing upload of the same scene.
    for item in list_children(drive, folder_id):
        if item["name"] == filename:
            drive.files().delete(fileId=item["id"]).execute()

    result = upload_file(
        drive,
        str(local_path),
        filename,
        folder_id,
        mime="video/mp4",
    )

    return filename, result


def main():
    scene = validate_inputs()
    telegram_path = get_telegram_file()

    with tempfile.TemporaryDirectory() as temp_dir:
        local_path = Path(temp_dir) / f"scene_{scene:02d}.mp4"

        download_telegram_video(telegram_path, local_path)

        filename, result = save_to_drive(scene, local_path)

    print(
        f"SUCCESS: {filename} uploaded to "
        f"INBOX/{JOB_ID}/ (Drive file ID: {result['id']})"
    )


if __name__ == "__main__":
    main()
