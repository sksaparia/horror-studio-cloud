import os, re, uuid, requests, xml.etree.ElementTree as ET
from urllib.parse import quote

def main():
    # Pull English-language trend ideas from the US, UK and Ireland. The approved
    # creative brief always targets English-speaking audiences in the US + Europe.
    geos=[("US","United States"),("GB","United Kingdom"),("IE","Ireland")]
    picks=[]
    for geo, label in geos:
        url=f"https://trends.google.com/trending/rss?geo={geo}"
        try:
            r=requests.get(url,timeout=25,headers={"User-Agent":"Mozilla/5.0"}); r.raise_for_status()
            root=ET.fromstring(r.content)
            for item in root.findall(".//item")[:12]:
                title=(item.findtext("title") or "").strip()
                # Keep mostly English/Latin-script topic titles; no India/South Asia feed.
                if title and re.search(r"[A-Za-z]",title) and not re.search(r"[\u0900-\u097F]",title):
                    picks.append((title,label))
        except Exception as e:
            print(f"Trend feed {geo} unavailable: {e}")
    # Deduplicate and cap suggestions; trending terms are inspiration, not verified horror news.
    seen=set(); unique=[]
    for title, region in picks:
        key=title.casefold()
        if key not in seen:
            seen.add(key); unique.append((title,region))
        if len(unique)>=5: break
    if not unique:
        unique=[("The abandoned motel on a lonely American highway","United States"),
                ("The last night train through the Scottish Highlands","United Kingdom"),
                ("The locked room in an old European hotel","Europe")]
    token=os.environ["TELEGRAM_BOT_TOKEN"]; chat=os.environ["TELEGRAM_CHAT_ID"]
    worker=os.environ["CLOUDFLARE_WORKER_URL"].rstrip("/")
    for title,region in unique:
        tid=uuid.uuid4().hex[:10]
        title=f"{title} — {region} inspiration"
        requests.post(worker+"/topic",headers={"x-topic-ingest-secret":os.environ["TOPIC_INGEST_SECRET"]},json={"id":tid,"title":title},timeout=20).raise_for_status()
        kb={"inline_keyboard":[[{"text":"✅ Approve & create English story pack","callback_data":"approve:"+tid},{"text":"Skip","callback_data":"skip:"+tid}]]}
        msg=f"US / EUROPE TREND INSPIRATION — APPROVAL REQUIRED\n\n{title}\n\nAll scripts, narration, subtitles and metadata will be English, with settings in the United States or Europe. These are creative prompts, not verified horror trends. Nothing is generated or published until you approve and later upload Flow clips."
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",json={"chat_id":chat,"text":msg,"reply_markup":kb},timeout=20).raise_for_status()
if __name__=="__main__": main()
