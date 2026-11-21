
import os
import uuid
import time
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
WORKER = os.environ["CLOUDFLARE_WORKER_URL"].rstrip("/")
INGEST_SECRET = os.environ["TOPIC_INGEST_SECRET"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 HorrorStudioCloud/1.0"
}

COUNTRIES = [
    ("US", "United States", "en-US", "US:en"),
    ("GB", "United Kingdom", "en-GB", "GB:en"),
    ("DE", "Germany", "en-GB", "DE:en"),
    ("FR", "France", "en-GB", "FR:en"),
    ("IT", "Italy", "en-GB", "IT:en"),
    ("ES", "Spain", "en-GB", "ES:en"),
]

HORROR_TERMS = [
    "horror", "haunted", "ghost", "paranormal",
    "mystery", "mysterious", "abandoned",
    "missing", "disappearance", "creepy",
    "serial killer", "unsolved", "dark web",
    "urban legend", "supernatural", "witch",
    "demon", "exorcism", "cemetery", "eerie",
    "haunting", "nightmare", "cryptid"
]

def get_feed(url):
    try:
        response = requests.get(
            url, headers=HEADERS, timeout=20
        )
        response.raise_for_status()

        root = ET.fromstring(response.content)
        items = []

        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            pub_date = item.findtext("pubDate", "").strip()

            if title and link:
                items.append({
                    "title": title,
                    "link": link,
                    "date": pub_date
                })

        return items

    except Exception as error:
        print(f"Feed error: {error}")
        return []

def is_horror_relevant(text):
    text = text.lower()
    return any(term in text for term in HORROR_TERMS)

def get_trends():
    results = []

    for code, country, _, _ in COUNTRIES:
        url = (
            "https://trends.google.com/trending/rss"
            f"?geo={code}"
        )

        for item in get_feed(url):
            if is_horror_relevant(item["title"]):
                item["country"] = country
                item["source"] = "Google Trends"
                results.append(item)

        time.sleep(1)

    return results

def get_horror_news():
    results = []

    queries = [
        '"haunted" OR "paranormal" OR "ghost"',
        '"horror mystery" OR "unsolved mystery"',
        '"abandoned place" OR "urban legend"',
        '"strange disappearance" OR "creepy discovery"'
    ]

    for code, country, language, edition in COUNTRIES:
        for query in queries:
            url = (
                "https://news.google.com/rss/search?q="
                + quote(query)
                + f"&hl={language}&gl={code}&ceid={edition}"
            )

            for item in get_feed(url):
                if is_horror_relevant(item["title"]):
                    item["country"] = country
                    item["source"] = "Google News"
                    results.append(item)

            time.sleep(1)

    return results

def make_concept(item):
    title = item["title"].split(" - ")[0].strip()
    return (
        f"A fictional horror story inspired by this current "
        f"real-world topic: {title}. "
        f"Create an original suspenseful mystery set in "
        f"{item['country']}, with an unexplained event, "
        f"a disturbing discovery, and a shocking final reveal. "
        f"Do not present fictional events as real."
    )

def send_telegram(item):
    tid = uuid.uuid4().hex[:10]
    title = item["title"][:180]

    response = requests.post(
        WORKER + "/topic",
        headers={
            "x-topic-ingest-secret": INGEST_SECRET
        },
        json={
            "id": tid,
            "title": title
        },
        timeout=20
    )
    response.raise_for_status()

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
        "LIVE HORROR TREND SIGNAL\n"
        "US / UK / EUROPE\n\n"
        f"COUNTRY: {item['country']}\n"
        f"SOURCE: {item['source']}\n\n"
        f"CURRENT TOPIC:\n{title}\n\n"
        f"STORY CONCEPT:\n{make_concept(item)}\n\n"
        f"SOURCE LINK:\n{item['link']}\n\n"
        "This is a fictional story concept inspired by "
        "a live source. Verify the source before publishing."
    )

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": message,
            "reply_markup": keyboard
        },
        timeout=20
    )
    response.raise_for_status()

def main():
    print("Collecting Google Trends signals...")
    trends = get_trends()

    print("Collecting Google News results...")
    news = get_horror_news()

    combined = trends + news

    unique = {}
    for item in combined:
        key = item["title"].lower()
        if key not in unique:
            unique[key] = item

    selected = list(unique.values())[:10]

    if not selected:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": (
                    "No relevant live horror signals were found "
                    "in this run. No fixed or invented trending "
                    "topics have been substituted."
                )
            },
            timeout=20
        )
        print("No relevant live results found.")
        return

    for item in selected:
        send_telegram(item)
        time.sleep(1)

    print(f"Successfully sent {len(selected)} live-source ideas.")

if __name__ == "__main__":
    main()
