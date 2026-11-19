import os, json, requests
from pathlib import Path

def main():
    token=os.environ["TELEGRAM_BOT_TOKEN"]
    chat=os.environ["TELEGRAM_CHAT_ID"]
    result=json.load(open("work/render-result.json",encoding="utf-8"))
    publish=json.load(open("work/youtube-result.json",encoding="utf-8")) if Path("work/youtube-result.json").exists() else {}
    yt=publish.get("youtube_url")
    if not yt:
        print("No YouTube URL; skipping post-upload Telegram delivery.")
        return
    if result.get("format","short")!="short" or not result.get("telegram_delivery",True):
        print("Telegram video delivery disabled for this format/job.")
        return
    drive=result.get("drive_file",{})
    drive_url=drive.get("webViewLink", "")
    caption=(f"YouTube upload complete\n{result.get('title','Horror Short')}\n\nWatch: {yt}\n\nDrive copy: {drive_url or 'Available in your OUTPUT folder'}")[:1000]
    video=Path("work/final.mp4")
    # Telegram Bot API cloud upload limit is typically 50 MB. Attach smaller Shorts;
    # for larger files send the authenticated Drive link instead.
    if video.exists() and video.stat().st_size < 49*1024*1024:
        with video.open("rb") as f:
            r=requests.post(f"https://api.telegram.org/bot{token}/sendVideo",data={"chat_id":chat,"caption":caption},files={"video":("short.mp4",f,"video/mp4")},timeout=180)
        if r.ok and r.json().get("ok"):
            print("Short sent to Telegram.")
            return
        print("Telegram video attachment failed; sending links instead:",r.text[:500])
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage",json={"chat_id":chat,"text":caption},timeout=30).raise_for_status()

if __name__=="__main__": main()
