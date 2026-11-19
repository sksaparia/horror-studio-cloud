import os, json, sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
SCOPES=["https://www.googleapis.com/auth/youtube.upload"]
def main(path, meta_path):
    with open(meta_path,encoding="utf-8") as f: m=json.load(f)
    creds=Credentials(None,refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],token_uri="https://oauth2.googleapis.com/token",client_id=os.environ["GOOGLE_CLIENT_ID"],client_secret=os.environ["GOOGLE_CLIENT_SECRET"],scopes=SCOPES); creds.refresh(Request())
    yt=build("youtube","v3",credentials=creds,cache_discovery=False)
    body={"snippet":{"title":m.get("title","English Horror Story")[:100],"description":m.get("youtube_description",""),"tags":m.get("youtube_tags",[])[:30],"categoryId":"24"},"status":{"privacyStatus":os.getenv("YOUTUBE_PRIVACY_STATUS","private"),"selfDeclaredMadeForKids":False}}
    req=yt.videos().insert(part="snippet,status",body=body,media_body=MediaFileUpload(path,chunksize=-1,resumable=True))
    response=None
    while response is None: status,response=req.next_chunk()
    url="https://www.youtube.com/watch?v="+response["id"]
    print(url)
    return url
if __name__=="__main__": main(sys.argv[1],sys.argv[2])
