
import os
import json
import asyncio
import subprocess

import edge_tts

from src.drive import (
    services,
    list_children,
    download_file,
    find_job_folder,
    upload_file,
)

VOICE = os.getenv("TTS_VOICE", "en-US-GuyNeural")

SCENE_LIMITS = {
    "short": 5,
    "long": 48,
}


def run(cmd):
    process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    if process.returncode:
        raise RuntimeError(process.stdout[-5000:])


def timestamp(seconds):
    milliseconds = int(seconds * 1000)
    hours = milliseconds // 3600000
    milliseconds %= 3600000
    minutes = milliseconds // 60000
    milliseconds %= 60000
    secs = milliseconds // 1000
    milliseconds %= 1000

    return (
        f"{hours:02}:{minutes:02}:"
        f"{secs:02},{milliseconds:03}"
    )


def make_srt(text, duration, path):
    chunks = [
        item.strip()
        for item in text.replace("!", ".").replace("?", ".").split(".")
        if item.strip()
    ]

    if not chunks:
        return

    step = duration / len(chunks)

    with open(path, "w", encoding="utf-8") as file:
        for index, chunk in enumerate(chunks):
            start = timestamp(index * step)
            end = timestamp((index + 1) * step)

            file.write(
                f"{index + 1}\n"
                f"{start} --> {end}\n"
                f"{chunk}\n\n"
            )


async def narration(text, output):
    await edge_tts.Communicate(
        text,
        VOICE,
        rate="-8%",
        pitch="-8Hz",
    ).save(output)


def validate_clips(files, video_format):
    required = SCENE_LIMITS[video_format]

    clip_map = {
        item["name"]: item
        for item in files
    }

    expected = [
        f"scene_{number:02d}.mp4"
        for number in range(1, required + 1)
    ]

    missing = [
        name for name in expected
        if name not in clip_map
    ]

    if missing:
        raise RuntimeError(
            f"{video_format.upper()} video requires "
            f"{required} clips. Missing: "
            + ", ".join(missing)
        )

    return [clip_map[name] for name in expected]


def main(job_id):
    os.makedirs("work", exist_ok=True)

    drive = services()
    folder_id = find_job_folder(drive, job_id)
    files = list_children(drive, folder_id)

    manifest_file = next(
        (
            item for item in files
            if item["name"] == "manifest.json"
        ),
        None,
    )

    if not manifest_file:
        raise RuntimeError("manifest.json is missing.")

    download_file(
        drive,
        manifest_file["id"],
        "work/manifest.json",
    )

    with open("work/manifest.json", encoding="utf-8") as file:
        manifest = json.load(file)

    video_format = manifest.get("format", "short").lower()

    if video_format not in SCENE_LIMITS:
        raise RuntimeError("Format must be short or long.")

    # Check all required clips and keep the correct scene order.
    clips = validate_clips(files, video_format)

    print(
        f"Starting {video_format.upper()} render: "
        f"{len(clips)} scenes"
    )

    local_clips = []

    for index, clip in enumerate(clips):
        path = f"work/clip_{index:03}.mp4"

        download_file(
            drive,
            clip["id"],
            path,
        )

        local_clips.append(path)

    narration_text = manifest.get(
        "english_narration", ""
    ).strip()

    if not narration_text:
        raise RuntimeError(
            "english_narration is missing from manifest.json."
        )

    # Generate English narration.
    asyncio.run(
        narration(
            narration_text,
            "work/narration.mp3",
        )
    )

    # Video dimensions.
    if video_format == "short":
        width, height = 1080, 1920
    else:
        width, height = 1920, 1080

    normalized = []

    # Normalize every clip.
    for index, path in enumerate(local_clips):
        output = f"work/norm_{index:03}.mp4"
        normalized.append(output)

        video_filter = (
            f"scale={width}:{height}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1,fps=30,format=yuv420p"
        )

        run([
            "ffmpeg",
            "-y",
            "-i", path,
            "-vf", video_filter,
            "-an",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            output,
        ])

    # Create ordered clip list.
    with open("work/list.txt", "w", encoding="utf-8") as file:
        for path in normalized:
            file.write(
                f"file '{os.path.abspath(path)}'\n"
            )

    # Join scenes.
    run([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", "work/list.txt",
        "-c", "copy",
        "work/sequence.mp4",
    ])

    # Read narration duration.
    duration = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1",
                "work/narration.mp3",
            ],
            text=True,
        ).strip()
    )

    if duration <= 0:
        raise RuntimeError("Narration duration is invalid.")

    # Use supplied subtitles, or narration as fallback.
    subtitles = manifest.get(
        "english_subtitles", ""
    ).strip()

    if not subtitles:
        subtitles = narration_text

    make_srt(
        subtitles,
        duration,
        "work/subs.srt",
    )

    subtitle_filter = (
        "subtitles=work/subs.srt:"
        "force_style='FontName=Arial,"
        "FontSize=22,Outline=2,Shadow=1,"
        "Alignment=2,MarginV=70'"
    )

    # Loop visuals until narration ends.
    run([
        "ffmpeg",
        "-y",
        "-stream_loop", "-1",
        "-i", "work/sequence.mp4",
        "-i", "work/narration.mp3",
        "-t", str(duration),
        "-vf", subtitle_filter,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "work/final.mp4",
    ])

    # Upload final video to Drive output folder.
    uploaded = upload_file(
        drive,
        "work/final.mp4",
        f"{job_id}_final.mp4",
        os.environ["DRIVE_OUTPUT_FOLDER_ID"],
    )

    result = {
        "title": manifest.get("title", job_id),
        "description": manifest.get("youtube_description", ""),
        "tags": manifest.get("youtube_tags", []),
        "publish": bool(manifest.get("publish", False)),
        "format": video_format,
        "telegram_delivery": bool(
            manifest.get("telegram_delivery", True)
        ),
        "duration_seconds": round(duration, 2),
        "scene_count": len(clips),
        "drive_file": uploaded,
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    import sys
    main(sys.argv[1])
