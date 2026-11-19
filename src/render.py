import os, json, glob, asyncio, subprocess, textwrap
import edge_tts
from PIL import Image, ImageDraw, ImageFont
from src.drive import services, list_children, download_file, find_job_folder, upload_file

VOICE = os.getenv("TTS_VOICE", "en-US-GuyNeural")

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode: raise RuntimeError(p.stdout[-5000:])

def make_srt(text, duration, path):
    # Basic evenly distributed subtitle timing. For precise word-level sync, supply a timed SRT separately in a future extension.
    chunks = [x.strip() for x in text.replace("!", ".").replace("?", ".").split(".") if x.strip()]
    if not chunks: return
    step = duration / len(chunks)
    def ts(v):
        ms = int(v*1000); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; ms%=1000
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    with open(path,"w",encoding="utf-8") as f:
        for i,c in enumerate(chunks): f.write(f"{i+1}\n{ts(i*step)} --> {ts((i+1)*step)}\n{c}\n\n")

async def narration(text, out):
    await edge_tts.Communicate(text, VOICE, rate="-8%", pitch="-8Hz").save(out)

def main(job_id):
    os.makedirs("work",exist_ok=True)
    drive=services(); folder=find_job_folder(drive,job_id); files=list_children(drive,folder)
    manifest_file=next((x for x in files if x["name"]=="manifest.json"),None)
    if not manifest_file: raise RuntimeError("manifest.json is missing from the Drive job folder")
    download_file(drive,manifest_file["id"],"work/manifest.json")
    with open("work/manifest.json",encoding="utf-8") as f: m=json.load(f)
    clips=sorted([x for x in files if x["name"].lower().endswith(".mp4")],key=lambda x:x["name"])
    if not clips: raise RuntimeError("No scene_*.mp4 clips found in the Drive job folder")
    local=[]
    for i,x in enumerate(clips):
        p=f"work/clip_{i:03}.mp4"; download_file(drive,x["id"],p); local.append(p)
    narration_text=m.get("english_narration","").strip()
    if not narration_text: raise RuntimeError("manifest.json must include english_narration")
    asyncio.run(narration(narration_text,"work/narration.mp3"))
    # Normalize all clips to a common canvas, concatenate, then loop visuals to narration duration.
    vertical=m.get("format","short").lower()=="short"
    w,h=(1080,1920) if vertical else (1920,1080)
    normalized=[]
    for i,p in enumerate(local):
        out=f"work/norm_{i:03}.mp4"; normalized.append(out)
        vf=f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p"
        run(["ffmpeg","-y","-i",p,"-vf",vf,"-an","-c:v","libx264","-preset","veryfast","-crf","22",out])
    with open("work/list.txt","w") as f:
        for p in normalized: f.write(f"file '{os.path.abspath(p)}'\n")
    run(["ffmpeg","-y","-f","concat","-safe","0","-i","work/list.txt","-c","copy","work/sequence.mp4"])
    dur=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1","work/narration.mp3"],text=True).strip())
    # Loop the assembled visuals; cap long-form duration to configured target if longer than narration.
    target=float(m.get("target_minutes",1))*60
    duration=max(dur, min(target, dur+1))
    subtitles=m.get("english_subtitles","").strip()
    if subtitles:
        make_srt(subtitles,dur,"work/subs.srt")
        sub="work/subs.srt"
        vf=f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,subtitles={sub}:force_style='FontName=Arial,FontSize=22,Outline=2,Shadow=1,Alignment=2,MarginV=70'"
        run(["ffmpeg","-y","-stream_loop","-1","-i","work/sequence.mp4","-i","work/narration.mp3","-t",str(dur),"-vf",vf,"-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","veryfast","-crf","22","-c:a","aac","-b:a","192k","-shortest","work/final.mp4"])
    else:
        run(["ffmpeg","-y","-stream_loop","-1","-i","work/sequence.mp4","-i","work/narration.mp3","-t",str(dur),"-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","veryfast","-crf","22","-c:a","aac","-b:a","192k","-shortest","work/final.mp4"])
    uploaded=upload_file(drive,"work/final.mp4",f"{job_id}_final.mp4",os.environ["DRIVE_OUTPUT_FOLDER_ID"])
    print(json.dumps({"title":m.get("title",job_id),"description":m.get("youtube_description",""),"tags":m.get("youtube_tags",[]),"publish":bool(m.get("publish",False)),"format":m.get("format","short"),"telegram_delivery":bool(m.get("telegram_delivery",True)),"drive_file":uploaded},ensure_ascii=False))

if __name__=="__main__":
    import sys; main(sys.argv[1])
