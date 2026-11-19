import os, json, requests
from src.drive import services, create_folder, upload_json

def telegram(message):
    token=os.environ['TELEGRAM_BOT_TOKEN']; chat=os.environ['TELEGRAM_CHAT_ID']
    requests.post(f'https://api.telegram.org/bot{token}/sendMessage',json={'chat_id':chat,'text':message[:4000]},timeout=25).raise_for_status()

def make_pack(job_id, topic):
    title=topic.strip()[:120]
    fmt=os.getenv('FORMAT','short')
    pack={
      'job_id':job_id,'title':title,'format':fmt,
      'language':'English','target_audience':'English-speaking viewers in the United States and Europe',
      'story_outline':f'Create an original English-language horror story for viewers in the United States and Europe, inspired by: {title}. Set it in a recognisable US or European location, never India or South Asia. Start with a compelling 2-second hook, escalate dread, deliver a clear supernatural reveal and a memorable final twist. Do not copy existing films, stories or creators.',
      'visual_style':'Photorealistic cinematic US or European setting, culturally authentic locations, natural contemporary English dialogue, grounded performances, atmospheric practical lighting, realistic camera movement, no on-screen text, no watermark, consistent faces, accents, hairstyles and wardrobe.',
      'scene_prompts':[
        'Scene 1 (0-8s): Establish an eerie American or European location at night; slow cinematic push-in; include one subtle unexplained detail.',
        'Scene 2 (8-16s): Introduce the protagonist in a medium close-up; natural English dialogue or silent reaction; tension rises.',
        'Scene 3 (16-24s): Reveal an impossible clue in the background; restrained camera movement; authentic location ambience.',
        'Scene 4 (24-32s): The protagonist discovers the threat; believable reaction; maintain identical face, accent, hairstyle and wardrobe.',
        'Scene 5 (32-40s): Deliver the final supernatural reveal and twist; end on a disturbing visual beat, no text.'
      ],
      'generation_note':'Generate clips manually in Google Flow. Upload as scene_01.mp4 etc. to Drive INBOX/<JOB_ID>/. Complete english_narration and english_subtitles in manifest.json before rendering. All spoken dialogue, narration, subtitles, titles and metadata must be English.'
    }
    drive=services()
    folder_id=create_folder(drive,job_id,os.environ['DRIVE_INBOX_FOLDER_ID'])
    manifest={'title':title,'format':fmt,'language':'English','target_audience':'United States and Europe','target_minutes':8 if fmt=='long' else 1,'english_narration':'','english_subtitles':'','youtube_description':'An original English-language cinematic horror story for viewers in the United States and Europe. Fictional entertainment.','youtube_tags':['horror story','scary stories','paranormal','supernatural horror','short horror film'],'publish':True,'telegram_delivery':True}
    upload_json(drive,manifest,'manifest.json',folder_id)
    os.makedirs('work',exist_ok=True)
    with open(f'work/{job_id}_prompt_pack.json','w',encoding='utf-8') as f: json.dump(pack,f,ensure_ascii=False,indent=2)
    telegram('APPROVED TOPIC — ENGLISH US & EUROPE HORROR STORY / FLOW PROMPT PACK\n\n'+json.dumps(pack,ensure_ascii=False,indent=2)[:2400]+f'\n\nDrive folder: INBOX/{job_id}. Edit manifest.json, fill english_narration and english_subtitles, upload scene_01.mp4 etc., then run Horror production with action=render.')
    return pack

if __name__=='__main__':
    make_pack(os.environ['JOB_ID'],os.environ.get('TOPIC_TITLE') or os.environ['JOB_ID'])
