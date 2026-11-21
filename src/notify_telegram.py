
import os
import json
import requests
from pathlib import Path


def load_json_safely(path):
    """Load JSON without crashing if the file is missing or invalid."""
    path = Path(path)

    if not path.exists() or path.stat().st_size == 0:
        print(f"JSON file missing or empty: {path}")
        return {}

    content = path.read_text(encoding="utf-8").strip()

    if not content:
        return {}

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Sometimes command logs appear before the JSON output.
        decoder = json.JSONDecoder()

        for index, character in enumerate(content):
            if character == "{":
                try:
                    data, _ = decoder.raw_decode(content[index:])
                    if isinstance(data, dict):
                        return data
                except json.JSONDecodeError:
                    continue

        print(f"No valid JSON object found in {path}")
        return {}


def send_telegram_message(token, chat, message):
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat,
            "text": message[:4000]
        },
        timeout=30
    )
    response.raise_for_status()

    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram message failed: {data}")

    return data


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat = os.environ["TELEGRAM_CHAT_ID"]

    work = Path("work")

    # Read render information safely.
    result = load_json_safely(work / "render-result.json")

    # Read manifest as a fallback.
    manifest = load_json_safely(work / "manifest.json")

    # Read YouTube result safely.
    yt_data = load_json_safely(work / "youtube-result.json")
    youtube_url = yt_data.get("youtube_url", "")

    if not result and not manifest:
        print("Warning: Render metadata and manifest are unavailable.")

    if (
        result.get("telegram_delivery") is False
        or manifest.get("telegram_delivery") is False
    ):
        print("Telegram delivery disabled.")
        return

    title = (
        result.get("title")
        or manifest.get("title")
        or "English Horror Video"
    )

    drive = result.get("drive_file", {})
    if not isinstance(drive, dict):
        drive = {}

    drive_url = drive.get("webViewLink", "")

    caption = f"🎬 HORROR VIDEO READY\n\n{title}"

    if youtube_url:
        caption += f"\n\n▶ YouTube: {youtube_url}"
    else:
        caption += "\n\nYouTube upload link is not available yet."

    if drive_url:
        caption += f"\n\nGoogle Drive: {drive_url}"
    else:
        caption += "\n\nCheck your Google Drive OUTPUT folder for the backup."

    video = work / "final.mp4"

    # Always try Telegram delivery if the final MP4 exists.
    if not video.exists() or video.stat().st_size == 0:
        message = (
            "⚠️ HORROR VIDEO RENDER ISSUE\n\n"
            f"{title}\n\n"
            "The final MP4 was not found or is empty. "
            "Please check the GitHub Actions render logs."
        )
        send_telegram_message(token, chat, message)
        raise RuntimeError("Final MP4 file not found or empty.")

    size_mb = video.stat().st_size / (1024 * 1024)
    print(f"Final video size: {size_mb:.2f} MB")

    # Telegram hosted Bot API upload limit.
    if video.stat().st_size < 49 * 1024 * 1024:
        with video.open("rb") as file:
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendVideo",
                data={
                    "chat_id": chat,
                    "caption": caption[:1000]
                },
                files={
                    "video": (video.name, file, "video/mp4")
                },
                timeout=300
            )

        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.ok and data.get("ok"):
            print("SUCCESS: Final MP4 sent to Telegram.")
            return

        print("Telegram video upload failed:", response.text[:500])

    else:
        print("Video exceeds Telegram upload size limit.")

    # Fallback: send the available links/details.
    message = (
        caption
        + "\n\n⚠️ MP4 could not be attached directly. "
        "Please check Google Drive OUTPUT folder."
    )

    send_telegram_message(token, chat, message)
    print("Telegram fallback message sent.")


if __name__ == "__main__":
    main()
