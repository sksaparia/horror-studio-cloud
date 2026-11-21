
import os
import uuid
import random
import hashlib
import requests
from datetime import datetime, timezone

IDEAS = [
    ("The Hotel Room That Appears Only at 3:17 AM",
     "United States",
     "A night receptionist discovers a hotel room that appears on CCTV but does not exist on any floor plan."),

    ("The Last Train from the Scottish Highlands",
     "United Kingdom",
     "A passenger boards the final train home and discovers that every other passenger disappeared decades ago."),

    ("The Voice Calling from Apartment 13",
     "United States",
     "A tenant hears a child calling through a sealed apartment wall, although the building has no thirteenth floor."),

    ("The Village That Disappears from Every Map",
     "Europe",
     "A travel photographer finds a forgotten village where residents insist that nobody has ever visited before."),

    ("The Night Shift at Blackwood Hospital",
     "United Kingdom",
     "A security guard receives instructions from a hospital ward that was permanently closed thirty years ago."),

    ("Something Is Living Beneath the Ice",
     "Iceland",
     "Researchers at a remote research station hear knocking from beneath several metres of frozen ice."),

    ("The Woman in the Empty Highway Diner",
     "United States",
     "A truck driver meets a woman at a roadside diner, then discovers that the diner burned down years earlier."),

    ("The Lighthouse That Sends Signals to Nobody",
     "Ireland",
     "A new lighthouse keeper notices a mysterious signal coming from the sea, answered by something beneath the waves."),

    ("The Locked Basement of the Old Manor",
     "United Kingdom",
     "A family renovating an old manor finds fresh footprints leading into a basement that has been locked for a century."),

    ("The Hotel Guests Who Never Check Out",
     "France",
     "A night manager discovers that several guests have occupied the same rooms for over fifty years."),

    ("The Forest Road That Loops Forever",
     "Germany",
     "A couple driving through a forest repeatedly passes the same abandoned car, with someone waving from inside."),

    ("The Missing Children of Briarwood",
     "United States",
     "A small town's old school photographs reveal the same mysterious child appearing in every graduating class."),

    ("The Midnight Ferry to Nowhere",
     "Norway",
     "Passengers on a midnight ferry realise the coastline has vanished and the captain refuses to stop."),

    ("The Apartment Above the Ceiling",
     "United States",
     "A woman hears furniture moving above her ceiling, despite living on the top floor of the building."),

    ("The Village Bell That Rings Underground",
     "Europe",
     "Every night at midnight, villagers hear a church bell ringing beneath the cemetery.")
]


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat = os.environ["TELEGRAM_CHAT_ID"]
    worker = os.environ["CLOUDFLARE_WORKER_URL"].rstrip("/")
    ingest_secret = os.environ["TOPIC_INGEST_SECRET"]

    # Select the same five ideas throughout each UTC day.
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    seed = int(hashlib.sha256(today.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    selected = rng.sample(IDEAS, 5)

    for story, region, premise in selected:
        tid = uuid.uuid4().hex[:10]
        title = f"{story} — {region}"

        r = requests.post(
            worker + "/topic",
            headers={"x-topic-ingest-secret": ingest_secret},
            json={"id": tid, "title": title},
            timeout=20
        )
        r.raise_for_status()

        keyboard = {
            "inline_keyboard": [[
                {
                    "text": "✅ Approve & create story pack",
                    "callback_data": "approve:" + tid
                },
                {
                    "text": "Skip",
                    "callback_data": "skip:" + tid
                }
            ]]
        }

        message = (
            "DAILY HORROR STORY IDEAS\n"
            "US / UK / EUROPE\n\n"
            f"TITLE: {story}\n"
            f"SETTING: {region}\n\n"
            f"STORY CONCEPT:\n{premise}\n\n"
            "Original fictional horror concept. "
            "English story, narration and subtitles. "
            "Nothing is generated or published until you approve."
        )

        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat,
                "text": message,
                "reply_markup": keyboard
            },
            timeout=20
        )
        response.raise_for_status()

    print(f"Successfully sent {len(selected)} horror ideas to Telegram.")


if __name__ == "__main__":
    main()
