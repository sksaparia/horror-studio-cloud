
import os
import json
import requests
from pathlib import Path

def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat = os.environ["TELEGRAM_CHAT_ID"]

    with open("work/render-result.json", encoding="utf-8") as f:
        result = json.load(f)

    youtube_file = Path("work/youtube-result.json")
    yt = ""

    if youtube_file.exists():
        with open(youtube_file, encoding="utf-8") as f:
            yt = json.load(f).get("youtube_url", "")

    if not result.get("telegram_delivery", True):
        print("Telegram delivery disabled in manifest.")
        return

    title = result.get("title", "English Horror Video")
    drive = result.get("drive_file", {})
    drive_url = drive.get("webViewLink", "")

    caption = f"🎬 HORROR VIDEO READY\n\n{title}"

    if yt:
        caption += f"\n\n▶ YouTube: {yt}"
    else:
        caption += "\n\nYouTube upload link not available."

    if drive_url:
        caption += f"\n\nGoogle Drive: {drive_url}"
    else:
        caption += "\n\nVideo copy saved in your Google Drive OUTPUT folder."

    video = Path("work/final.mp4")

    if not video.exists():
        raise RuntimeError("Final MP4 file not found.")

    # Telegram cloud Bot API upload limit: approximately 50 MB.
    if video.stat().st_size < 49 * 1024 * 1024:
        with video.open("rb") as f:
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendVideo",
                data={
                    "chat_id": chat,
                    "caption": caption[:1000]
                },
                files={
                    "video": (video.name, f, "video/mp4")
                },
                timeout=300
            )

        if response.ok and response.json().get("ok"):
            print("Final MP4 successfully sent to Telegram.")
            return

        print("Telegram video upload failed:", response.text[:500])

    else:
        print("Video exceeds Telegram upload size limit.")

    # Send links/details if direct MP4 upload is not possible.
    message = caption + "\n\n⚠️ MP4 could not be attached. Check Google Drive OUTPUT folder."
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat, "text": message[:4000]},
        timeout=30
    ).raise_for_status()

if __name__ == "__main__":
    main()
