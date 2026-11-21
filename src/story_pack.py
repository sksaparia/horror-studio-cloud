
import os
import json
import requests
from src.drive import services, create_folder, upload_json

SCENE_LIMITS = {"short": 5, "long": 48}

VISUAL_STYLE = (
    "Photorealistic cinematic horror, realistic modern American coastal city, "
    "Vice City-inspired atmosphere, night-time neon lighting, believable "
    "performances, subtle film grain, realistic camera movement. "
    "No text, no captions, no logos, no watermark. "
    "Maintain exactly the same protagonist face, age, hairstyle, clothing "
    "and voice throughout every scene."
)

# Each beat contains a narration line and its matching visual action.
STORY_BEATS = [
    ("At 2:13 AM, a hotel appeared on the road where no building had existed before.",
     "A lone driver approaches a mysterious hotel appearing beside an empty coastal road."),

    ("Its sign flickered between two names, although nobody could read the second one.",
     "Show an old neon hotel sign flickering strangely above the entrance."),

    ("Daniel Reed stopped his car and noticed every window was glowing.",
     "Introduce Daniel Reed, a  thirty-year-old American man with short dark hair, wearing a black leather jacket."),

    ("He had been driving through the city for hours, searching for a place to sleep.",
     "Daniel steps out of his car and looks exhausted beneath the hotel lights."),

    ("The lobby doors opened before he touched them.",
     "The hotel entrance opens by itself as Daniel approaches."),

    ("Inside, an old receptionist greeted him using a name Daniel had never shared.",
     "An elderly receptionist stands behind a dusty wooden desk and quietly addresses Daniel."),

    ("The guestbook already contained his signature, dated thirty years earlier.",
     "Close-up of an old guestbook showing Daniel's signature on a page covered in dust."),

    ("Daniel laughed nervously and asked for a room on the highest floor.",
     "Daniel tries to remain calm while asking for a room key."),

    ("The receptionist handed him key number 213 without looking up.",
     "A pale hand slides an old brass key marked 213 across the desk."),

    ("The elevator had no buttons, only a mirror covered in fingerprints.",
     "Daniel enters a vintage elevator with a large scratched mirror."),

    ("As the doors closed, another reflection remained standing behind him.",
     "In the elevator mirror, a dark human silhouette stands behind Daniel."),

    ("Daniel turned around, but the elevator was completely empty.",
     "Daniel spins around in fear and finds nobody inside the elevator."),

    ("The doors opened on a corridor smelling of seawater and wet concrete.",
     "Reveal a long, dim hotel corridor with damp walls and flickering lights."),

    ("Room 213 stood at the very end, its door slightly open.",
     "Slow camera push toward a half-open hotel room door marked 213."),

    ("Inside, a television showed live footage of Daniel entering the hotel.",
     "An old television displays a surveillance view of Daniel entering the hotel moments earlier."),

    ("He switched it off, but the screen continued showing him.",
     "Daniel presses the television power button; the image remains active."),

    ("Then the television showed him standing behind himself.",
     "The screen reveals a second Daniel standing directly behind the real Daniel."),

    ("A phone began ringing inside the bedside drawer.",
     "A vintage telephone rings inside a wooden bedside drawer."),

    ("A woman's voice whispered, 'You came back exactly as promised.'",
     "Daniel holds the telephone to his ear, listening in terror."),

    ("He demanded to know who she was, but she only started crying.",
     "Daniel speaks into the phone while a faint sob echoes through the room."),

    ("Outside the window, the city had disappeared beneath black water.",
     "Show the hotel window overlooking a flooded city under a dark sky."),

    ("Streetlights floated upside down, like stars trapped beneath the ocean.",
     "Unnatural streetlights glow beneath the surface of the black water."),

    ("Daniel ran into the corridor and found every door standing open.",
     "Daniel rushes into the corridor as multiple hotel room doors slowly open."),

    ("Every room contained the same furniture, the same television, and the same photograph.",
     "A series of identical hotel rooms reveal the same television and framed photograph."),

    ("The photograph showed Daniel as a child, standing beside the receptionist.",
     "Close-up of a framed photograph showing a young boy resembling Daniel beside the old receptionist."),

    ("He remembered a childhood holiday his family had refused to discuss.",
     "Daniel stares at the photograph as a forgotten childhood memory returns."),

    ("A bell rang downstairs, followed by dozens of footsteps.",
     "A hotel service bell rings while heavy footsteps echo from below."),

    ("The elevator opened, revealing a crowded lobby full of motionless guests.",
     "The elevator doors open onto silent guests standing perfectly still in the lobby."),

    ("Their faces were hidden, but every one of them held a room key.",
     "Show rows of motionless guests holding identical brass room keys."),

    ("The receptionist looked up and said, 'Your family has been waiting.'",
     "The elderly receptionist looks directly at Daniel and speaks with a cold expression."),

    ("Daniel saw a woman near the staircase wearing his mother's wedding ring.",
     "A mysterious woman stands near the staircase wearing a distinctive wedding ring."),

    ("She looked exactly like his mother, who had vanished when he was seven.",
     "Daniel recognizes the woman and freezes in disbelief."),

    ("She raised one finger to her lips and pointed toward the basement.",
     "The woman silently gestures for Daniel to follow her downstairs."),

    ("Behind the basement door, hundreds of clocks ticked at different speeds.",
     "Reveal a basement filled with hundreds of clocks showing different times."),

    ("One clock showed the date of his mother's disappearance.",
     "Close-up of a clock displaying the exact date Daniel's mother disappeared."),

    ("Another showed tomorrow's date, with Daniel's name written beneath it.",
     "Daniel discovers a clock marked with tomorrow's date and his name."),

    ("The receptionist appeared behind him and locked the basement door.",
     "The receptionist emerges from the shadows and closes the basement door."),

    ("He finally explained that the hotel only appeared to people who had escaped it.",
     "The receptionist reveals the hotel's supernatural secret in the dim basement."),

    ("Daniel had visited this place as a child, but his memory had been erased.",
     "Daniel experiences fragmented childhood memories of the same hotel."),

    ("His mother had stayed behind to keep the hotel from following him.",
     "A memory shows Daniel's mother protecting her young son inside the hotel."),

    ("Now the hotel wanted its missing guest to complete the reservation.",
     "The receptionist holds out the old guestbook and gestures toward Daniel's signature."),

    ("Daniel refused and smashed the clock marked with tomorrow's date.",
     "Daniel violently smashes the clock as glass and gears scatter."),

    ("Every light in the building went out at once.",
     "The entire hotel plunges into darkness with a sudden electrical blackout."),

    ("In the darkness, his mother's voice called him by his childhood nickname.",
     "Daniel hears a familiar voice calling from the darkness and turns."),

    ("A hand reached through the wall and grabbed his wrist.",
     "A pale hand emerges unnaturally from the wall and grabs Daniel."),

    ("He pulled free and ran toward the entrance as the walls began to collapse.",
     "Daniel runs through a collapsing corridor toward the hotel entrance."),

    ("Outside, his car was waiting, but the passenger seat was occupied.",
     "Daniel reaches his car and sees a mysterious figure sitting in the passenger seat."),

    ("The figure turned slowly. It was Daniel, still standing inside the hotel.",
     "The passenger turns toward camera, revealing an identical version of Daniel.")
]


def telegram(message):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat = os.environ["TELEGRAM_CHAT_ID"]

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Split long messages without exceeding Telegram's message limit.
    chunks = []
    while len(message) > 3800:
        split_at = message.rfind("\n", 0, 3800)
        if split_at < 500:
            split_at = 3800
        chunks.append(message[:split_at])
        message = message[split_at:].lstrip()

    if message:
        chunks.append(message)

    for chunk in chunks:
        response = requests.post(
            url,
            json={"chat_id": chat, "text": chunk},
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        if not result.get("ok"):
            raise RuntimeError(f"Telegram message failed: {result}")


def build_scene_prompt(number, narration, visual):
    start = (number - 1) * 10
    end = number * 10

    return (
        f"SCENE {number:02d} | EXACT DURATION: 10 SECONDS | "
        f"TIMELINE: {start}-{end} seconds\n\n"
        f"VISUAL ACTION: {visual}\n\n"
        f"VISUAL STYLE: {VISUAL_STYLE}\n\n"
        f"STORY NARRATION CONTEXT: {narration}\n\n"
        "Continuity: This is one continuous story. Preserve the same "
        "protagonist identity, face, hairstyle, age and wardrobe. "
        "Use natural realistic movement and cinematic framing. "
        "No visible text, no subtitles, no watermark. "
        "Do not introduce unrelated characters or locations."
    )


def make_pack(job_id, topic):
    title = topic.strip()[:120]
    fmt = os.getenv("FORMAT", "short").lower()

    if fmt not in SCENE_LIMITS:
        raise ValueError("FORMAT must be short or long.")

    # Short version uses five story beats from beginning to ending.
    if fmt == "short":
        selected_indexes = [0, 10, 19, 35, 47]
        selected_beats = [STORY_BEATS[i] for i in selected_indexes]
    else:
        selected_beats = STORY_BEATS

    narration_lines = [beat[0] for beat in selected_beats]
    narration_text = " ".join(narration_lines)

    scene_prompts = []
    for index, (narration, visual) in enumerate(selected_beats, start=1):
        scene_prompts.append(
            build_scene_prompt(index, narration, visual)
        )

    subtitles_text = "\n".join(narration_lines)

    pack = {
        "job_id": job_id,
        "title": title,
        "format": fmt,
        "language": "English",
        "target_audience": (
            "English-speaking viewers in the United States and Europe"
        ),
        "scene_count": len(selected_beats),
        "scene_duration_seconds": 10,
        "total_visual_duration_seconds": len(selected_beats) * 10,
        "story_outline": (
            "An original supernatural hotel mystery. A man discovers "
            "a hotel connected to his forgotten childhood and must escape "
            "before the building claims him again."
        ),
        "visual_style": VISUAL_STYLE,
        "english_narration": narration_text,
        "english_subtitles": subtitles_text,
        "scene_prompts": scene_prompts,
        "generation_note": (
            "Generate every scene separately in Google Flow. "
            "Each clip must be exactly 10 seconds. Upload individual clips "
            "to the Telegram bot in scene order. Do not combine clips "
            "or upload a ZIP file."
        )
    }

    drive = services()

    folder_id = create_folder(
        drive,
        job_id,
        os.environ["DRIVE_INBOX_FOLDER_ID"]
    )

    manifest = {
        "title": title,
        "format": fmt,
        "language": "English",
        "target_audience": "United States and Europe",
        "target_minutes": 1 if fmt == "short" else 8,
        "scene_count": len(selected_beats),
        "scene_duration_seconds": 10,
        "english_narration": narration_text,
        "english_subtitles": subtitles_text,
        "youtube_description": (
            "An original English-language cinematic supernatural "
            "horror story for viewers in the United States and Europe. "
            "Fictional entertainment."
        ),
        "youtube_tags": [
            "horror story",
            "scary stories",
            "haunted hotel",
            "supernatural horror",
            "paranormal",
            "cinematic horror",
            "short horror film"
        ],
        "publish": True,
        "telegram_delivery": True
    }

    # Save complete narration and subtitles automatically.
    upload_json(drive, manifest, "manifest.json", folder_id)

    os.makedirs("work", exist_ok=True)

    pack_path = f"work/{job_id}_prompt_pack.json"
    with open(pack_path, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)

    # Send story and scene prompts to Telegram.
    telegram(
        "HORROR STUDIO CLOUD — STORY PACK READY\n\n"
        f"Title: {title}\n"
        f"Job ID: {job_id}\n"
        f"Format: {fmt.upper()}\n"
        f"Scenes: {len(selected_beats)}\n"
        "Clip duration: 10 seconds each\n"
        f"Total visual duration: {len(selected_beats) * 10} seconds\n\n"
        "ENGLISH NARRATION:\n\n"
        + narration_text
    )

    for index, prompt in enumerate(scene_prompts, start=1):
        telegram(
            f"GOOGLE FLOW PROMPT — SCENE {index:02d}/{len(scene_prompts)}\n\n"
            + prompt
        )

    telegram(
        "STORY PACK SAVED SUCCESSFULLY\n\n"
        f"Job ID: {job_id}\n"
        f"Drive folder: INBOX/{job_id}\n\n"
        "Upload your generated clips individually to the Telegram bot "
        "in scene order. Use one 10-second clip per scene."
    )

    print(json.dumps({
        "ok": True,
        "job_id": job_id,
        "format": fmt,
        "scene_count": len(selected_beats),
        "narration_characters": len(narration_text),
        "manifest_saved": True,
        "prompt_pack": pack_path
    }, ensure_ascii=False))


if __name__ == "__main__":
    make_pack(
        os.environ["JOB_ID"],
        os.environ.get("TOPIC_TITLE") or os.environ["JOB_ID"]
    )
