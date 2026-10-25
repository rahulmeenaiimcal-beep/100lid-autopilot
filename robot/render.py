"""Runs the Remotion animation project to draw the video frames and thumbnails,
then adds the sound with ffmpeg and makes small preview images for review."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from PIL import Image

from . import settings


def _remotion(args: list[str], log_name: str) -> None:
    cmd = ["npx", "--no-install", "remotion"] + args
    env = dict(os.environ, NODE_OPTIONS="--max-old-space-size=6144")
    log = settings.WORK / f"{log_name}.log"
    with open(log, "w") as fh:
        p = subprocess.run(cmd, cwd=settings.VIDEO, stdout=fh, stderr=subprocess.STDOUT, env=env)
    if p.returncode != 0:
        tail = log.read_text(errors="ignore")[-3000:]
        raise RuntimeError(f"Remotion failed ({log_name}):\n{tail}")


def video(props: dict, audio_wav: Path, out_mp4: Path, name: str) -> Path:
    props_file = settings.WORK / f"{name}.props.json"
    props_file.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    silent = settings.WORK / f"{name}.silent.mp4"
    _remotion(["render", "src/index.ts", "Episode", str(silent), f"--props={props_file}", "--muted", "--log=error"], f"render-{name}")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(audio_wav), "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out_mp4)],
        check=True,
    )
    silent.unlink(missing_ok=True)
    return out_mp4


def still(props: dict, out_png: Path, name: str) -> Path:
    props_file = settings.WORK / f"{name}.props.json"
    props_file.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    _remotion(["still", "src/index.ts", "Thumbnail", str(out_png), f"--props={props_file}", "--log=error"], f"still-{name}")
    # YouTube limit is 2 MB: save as high-quality JPEG
    jpg = out_png.with_suffix(".jpg")
    Image.open(out_png).convert("RGB").save(jpg, quality=90, optimize=True)
    return jpg


def contact_sheet(mp4: Path, times: list[float], out_jpg: Path, cols: int = 4) -> Path:
    """Grabs frames at the given seconds and tiles them into one image."""
    frames = []
    tmp = settings.WORK / "frames"
    tmp.mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(times):
        fp = tmp / f"{out_jpg.stem}_{i:02}.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{max(0, t):.2f}", "-i", str(mp4), "-frames:v", "1", "-q:v", "3", str(fp)], check=False)
        if fp.exists():
            frames.append(Image.open(fp).convert("RGB"))
    if not frames:
        return out_jpg
    w = 480
    h = int(frames[0].height * w / frames[0].width)
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * h), "white")
    for i, im in enumerate(frames):
        sheet.paste(im.resize((w, h)), ((i % cols) * w, (i // cols) * h))
    sheet.save(out_jpg, quality=85)
    return out_jpg
