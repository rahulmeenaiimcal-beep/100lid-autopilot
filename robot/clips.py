"""Your own recorded clips ("Rahul Sir's Exam Tip").

Once a month (around the 20th) `plan-month` picks next month's topics in order,
writes a short tip script for each, and emails you the list (a GitHub issue).
You record them on your phone and drop the files on a GitHub "release" page
(release pages accept big video files, up to 2 GB each).

When the robot makes a video whose topic has a clip, it downloads that clip and
plays it right after the Exam Corner, with your name and subtitles. Each clip is
used once. Optional brand clips (intro.mp4 / outro.mp4 on the `clips-brand`
release) are used on every video.

File names: tip-01.mp4, tip-02.mp4 ... (any common video format works:
.mp4 .mov .mkv .webm .3gp). The number matches the list in the email."""
from __future__ import annotations

import json
import random
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import requests

from . import llm, research, settings, topics
from . import ledger as L

API = "https://api.github.com"
PLANS = settings.DATA / "month_plan"
VIDEO_EXT = (".mp4", ".mov", ".mkv", ".webm", ".3gp", ".m4v", ".avi")
BRAND_TAG = "clips-brand"


def _repo() -> str:
    return settings.env("GITHUB_REPOSITORY")


def _h(raw: bool = False) -> dict:
    h = {"Authorization": f"Bearer {settings.env('GITHUB_TOKEN')}"}
    h["Accept"] = "application/octet-stream" if raw else "application/vnd.github+json"
    return h


def month_key(d: datetime | None = None) -> str:
    return (d or datetime.now()).strftime("%Y-%m")


def next_month_key() -> str:
    n = datetime.now()
    first_next = (n.replace(day=1) + timedelta(days=32)).replace(day=1)
    return first_next.strftime("%Y-%m")


def tag_for(month: str) -> str:
    return f"clips-{month}"


def load_plan(month: str) -> dict | None:
    p = PLANS / f"{month}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save_plan(month: str, plan: dict) -> None:
    PLANS.mkdir(parents=True, exist_ok=True)
    (PLANS / f"{month}.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")


# ------------------------------------------------------------------ planning
def plan_topics(d: dict, n: int) -> list[dict]:
    """Next month's topics in order, keeping the series mix and skipping recent ones."""
    mix = {k: v for k, v in settings.config().get("topic_mix", {}).items() if k != "current_affairs"}
    used = topics._used(d) | {t for p in PLANS.glob("*.json") for t in (json.loads(p.read_text()).get("order") or [])}
    counts = {k: 0 for k in mix}
    out: list[dict] = []
    bank = topics.bank()
    while len(out) < n:
        # the series furthest below its monthly target goes next
        series = sorted(mix, key=lambda s: (counts[s] / max(1, mix[s]), random.random()))
        picked = None
        for s in series:
            pool = [t for t in bank if t["series"] == s and t["id"] not in used]
            if pool:
                top = max(t.get("priority", 1) for t in pool)
                picked = random.choice([t for t in pool if t.get("priority", 1) == top])
                break
        if not picked:
            break
        out.append(picked)
        used.add(picked["id"])
        counts[picked["series"]] += 1
    # interleave so the same series doesn't run back-to-back
    groups: dict[str, list[dict]] = {}
    for t in out:
        groups.setdefault(t["series"], []).append(t)
    mixed: list[dict] = []
    while any(groups.values()):
        for s in sorted(groups, key=lambda k: -len(groups[k])):
            if groups[s] and (not mixed or mixed[-1]["series"] != s or len([g for g in groups.values() if g]) == 1):
                mixed.append(groups[s].pop(0))
    return mixed


TIP_SYSTEM = """You write short to-camera scripts for Rahul Sir, a real Indian management teacher who
presents an exam-prep YouTube channel (100LID) in Hindi with English exam terms kept in English.
Facts must come only from the research notes. No financial or legal advice."""


def tip_script(topic: dict, notes: str) -> dict:
    user = f"""Write "Rahul Sir's Exam Tip" for a video about {topic['title_en']} ({topic.get('title_hi', '')}).
It plays inside the video right after the Exam Corner, so: no greeting, no "subscribe", no sign-off.
Rahul Sir speaks to camera, warmly and personally, as an experienced teacher (60-80 seconds, 130-170 Hindi words):
1. One memory trick that makes the key facts easy to remember.
2. The single fact examiners ask most about this topic, said clearly.
3. One common mistake students make, and how to avoid it.
Short, speakable sentences. Natural spoken Hindi in Devanagari; numbers as digits; exam terms in English.
Return JSON: {{"script_hi": "...", "script_en": "natural English translation", "one_line": "the tip in 8 English words"}}

RESEARCH NOTES:
<<<
{notes[:12000]}
>>>"""
    res, _ = llm.chat(TIP_SYSTEM, user, want_json=True, temperature=0.6, max_tokens=3000)
    return {k: str(res.get(k, "")).strip() for k in ("script_hi", "script_en", "one_line")}


def release_link(month: str) -> str:
    title = f"My clips for {datetime.strptime(month, '%Y-%m'):%B %Y}"
    return f"https://github.com/{_repo()}/releases/new?tag={tag_for(month)}&title={requests.utils.quote(title)}"


def plan_month(d: dict, month: str | None = None) -> str:
    from . import review

    month = month or next_month_key()
    existing = load_plan(month)
    if existing and existing.get("tips"):
        return f"plan for {month} already exists"
    mix = {k: v for k, v in settings.config().get("topic_mix", {}).items() if k != "current_affairs"}
    order = plan_topics(d, sum(mix.values()))
    tips = []
    for i, t in enumerate(order, 1):
        notes = research.gather(t)["notes"]
        try:
            s = tip_script(t, notes) if len(notes) > 500 else {"script_hi": "", "script_en": "", "one_line": ""}
        except llm.LLMError:
            s = {"script_hi": "", "script_en": "", "one_line": ""}
        tips.append({"n": i, "file": f"tip-{i:02}", "topic_id": t["id"], "title_en": t["title_en"], "title_hi": t.get("title_hi", ""), **s})
    plan = {"month": month, "created": L.now_iso(), "order": [t["topic_id"] for t in tips], "tips": tips, "used": {}}
    save_plan(month, plan)
    pretty = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
    body = [
        f"## 🎥 Your recording list for {pretty}",
        "",
        f"These are next month's {len(tips)} long videos, in order. Each one has a short tip for **you** to record (about 1 minute each, ~15 minutes in total).",
        "",
        "### How to record (phone is perfect)",
        "- Hold the phone **sideways (landscape)**, at eye level, about an arm's length away. Look into the camera.",
        "- Sit facing a window or a lamp so your face is bright. Plain background, quiet room.",
        "- You don't need to read word-for-word — say it naturally in your own words. Mistakes? Just start that clip again.",
        "- Optional, once only: also record **intro** (3–5 s, e.g. \"नमस्ते, मैं राहुल…\") and **outro** (5–8 s). These are used on every video.",
        "",
        "### How to send them",
        f"1. Name the files **tip-01, tip-02, …** (the number from this list).",
        f"2. Open this link: {release_link(month)}",
        "3. Drag all the video files into the box that says **\"Attach binaries\"**, wait for them to finish uploading, then click the green **Publish release** button.",
        f"4. For intro/outro, do the same once at https://github.com/{_repo()}/releases/new?tag={BRAND_TAG}&title=Brand%20clips (files named **intro** and **outro**).",
        "",
        "Missing a clip? No problem — that video is simply made without it.",
        "",
        "---",
    ]
    for t in tips:
        body += [f"### {t['file']} — {t['title_en']} | {t['title_hi']}", ""]
        if t["script_hi"]:
            body += [t["script_hi"], "", f"<details><summary>English</summary>\n\n{t['script_en']}\n</details>", ""]
        else:
            body += ["_(The AI could not write this script — just share your best exam tip on this topic in about 1 minute.)_", ""]
    review.open_issue(f"🎥 Recording list for {pretty} ({len(tips)} short clips)", "\n".join(body), ["recording"])
    return f"planned {len(tips)} topics for {month}"


# ------------------------------------------------------------------ using the clips
def _release_assets(tag: str) -> list[dict]:
    if not (_repo() and settings.env("GITHUB_TOKEN")):
        return []
    r = requests.get(f"{API}/repos/{_repo()}/releases/tags/{tag}", headers=_h(), timeout=30)
    return r.json().get("assets", []) if r.ok else []


def _find_asset(assets: list[dict], stem: str) -> dict | None:
    stem = stem.lower()
    for a in assets:
        name = a.get("name", "").lower()
        base, ext = (name.rsplit(".", 1) + [""])[:2]
        base = re.sub(r"[\s_]+", "-", base)
        if ("." + ext) in VIDEO_EXT and (base == stem or base == stem.replace("-0", "-")):
            return a
    return None


def _download(asset: dict, dest: Path) -> Path:
    with requests.get(asset["url"], headers=_h(raw=True), stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return dest


def _probe_seconds(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def prepare(src: Path, name: str) -> dict:
    """Converts any phone video into a clean 1080p H.264 file for the animation, plus a
    loudness-matched WAV for the sound mix."""
    folder = settings.PUBLIC / "clips"
    folder.mkdir(parents=True, exist_ok=True)
    mp4 = folder / f"{name}.mp4"
    wav = settings.WORK / f"{name}.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf",
         "scale='min(1920,iw)':'min(1080,ih)':force_original_aspect_ratio=decrease,fps=30,format=yuv420p",
         "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(mp4)],
        check=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", "24000",
         "-af", "highpass=f=80,afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=11", str(wav)],
        check=True,
    )
    w, h = 1920, 1080
    try:
        dims = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(mp4)], capture_output=True, text=True).stdout.strip()
        w, h = [int(x) for x in dims.split(",")[:2]]
    except Exception:
        pass
    return {"file": f"clips/{name}.mp4", "wav": str(wav), "duration": _probe_seconds(wav), "w": w, "h": h}


def for_topic(d: dict, topic_id: str, eid: str) -> tuple[dict | None, dict | None, dict | None]:
    """Returns (tip clip, intro clip, outro clip) ready to use, or None for each that's missing."""
    tip = intro = outro = None
    month = month_key()
    plan = load_plan(month)
    if plan:
        t = next((x for x in plan["tips"] if x["topic_id"] == topic_id and x["file"] not in plan.get("used", {})), None)
        if t:
            a = _find_asset(_release_assets(tag_for(month)), t["file"])
            if a:
                try:
                    info = prepare(_download(a, settings.WORK / a["name"]), f"{eid}-tip")
                    if info["duration"] > 3:
                        tip = {**add_subtitles(info, t.get("script_hi", "")), "plan_file": t["file"], "month": month}
                except Exception as e:
                    print(f"clip {t['file']} could not be used: {e}")
    brand = _release_assets(BRAND_TAG)
    for stem in ("intro", "outro"):
        a = _find_asset(brand, stem)
        if not a:
            continue
        try:
            info = prepare(_download(a, settings.WORK / a["name"]), f"brand-{stem}")
            if 1 < info["duration"] < 20:
                info = add_subtitles(info)
                if stem == "intro":
                    intro = info
                else:
                    outro = info
        except Exception as e:
            print(f"{stem} clip could not be used: {e}")
    return tip, intro, outro


def mark_used(tip: dict | None, eid: str) -> None:
    if not tip:
        return
    plan = load_plan(tip["month"])
    if plan:
        plan.setdefault("used", {})[tip["plan_file"]] = eid
        save_plan(tip["month"], plan)


def planned_next(d: dict) -> str | None:
    """The next planned topic for this month that hasn't been made yet."""
    plan = load_plan(month_key())
    if not plan:
        return None
    made = {e.get("topic_id") for e in d.get("episodes", {}).values() if not e.get("test")}
    for tid in plan.get("order") or []:
        if tid not in made:
            return tid
    return None


# ------------------------------------------------------------------ exact subtitles from your own speech
def transcribe(wav: Path, fallback: str = "") -> list[dict]:
    """Hindi speech-to-text with the open-source Whisper model (faster-whisper), so the
    subtitles match what you actually said. Falls back to the planned script."""
    try:
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError:
            subprocess.run(["pip", "install", "-q", "faster-whisper>=1.0"], check=True, timeout=600)
            from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel(settings.config().get("clips", {}).get("whisper_model", "small"), device="cpu", compute_type="int8")
        segs, _ = model.transcribe(str(wav), language="hi", vad_filter=True, beam_size=5)
        out = [{"start": float(s.start), "end": float(s.end), "hi": s.text.strip()} for s in segs if s.text.strip()]
        if out:
            return out
    except Exception as e:
        print(f"speech-to-text not available ({e}); using the planned script for subtitles")
    if not fallback:
        return []
    dur = _probe_seconds(wav) or 60
    parts = [p for p in re.split(r"(?<=[।?!])\s+", fallback) if p.strip()]
    total = sum(len(p) for p in parts) or 1
    t, out = 0.0, []
    for p in parts:
        d = dur * len(p) / total
        out.append({"start": t, "end": t + d, "hi": p})
        t += d
    return out


def add_subtitles(info: dict, script_hi: str = "") -> dict:
    from .captions import translate

    segs = transcribe(Path(info["wav"]), script_hi)
    if segs:
        en = translate([s["hi"] for s in segs]) or []
        for s, e in zip(segs, en):
            s["en"] = e
    info["segments"] = segs
    info["text"] = " ".join(s["hi"] for s in segs) or script_hi
    info["en"] = " ".join(s.get("en", "") for s in segs).strip()
    return info


def synthetic_test_clip(eid: str, script_hi: str, script_en: str) -> dict:
    """A stand-in clip (moving test pattern + tone) to test the whole clip process
    before you have recorded anything. Used only by the `sample-clip` test job."""
    src = settings.WORK / "test-clip.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=20",
         "-f", "lavfi", "-i", "sine=frequency=220:duration=20", "-shortest", "-c:v", "libx264", "-preset", "veryfast",
         "-c:a", "aac", str(src)],
        check=True,
    )
    info = prepare(src, f"{eid}-tip")
    info = add_subtitles(info, script_hi)
    if not info.get("en"):
        info["segments"] = [{"start": 0, "end": info["duration"], "hi": script_hi, "en": script_en}]
        info["en"] = script_en
    return {**info, "plan_file": "test", "month": month_key()}
