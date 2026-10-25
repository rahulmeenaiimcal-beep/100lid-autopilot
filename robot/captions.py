"""Subtitle files (.srt) in Hindi and English, timed exactly to the voice."""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import llm
from .timeline import FPS, Plan


def _ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def _split(text: str, max_chars: int = 84) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts = re.split(r"(?<=[।,.!?—:])\s+", text)
    out, cur = [], ""
    for p in parts:
        if len(cur) + len(p) + 1 <= max_chars:
            cur = (cur + " " + p).strip()
        else:
            if cur:
                out.append(cur)
            while len(p) > max_chars:
                cut = p.rfind(" ", 0, max_chars)
                cut = cut if cut > 20 else max_chars
                out.append(p[:cut].strip())
                p = p[cut:].strip()
            cur = p
    if cur:
        out.append(cur)
    return out


def cues(plan: Plan, texts: list[str] | None = None) -> list[tuple[float, float, str]]:
    out = []
    for i, (start, clip) in enumerate(plan.voice):
        text = texts[i] if texts else clip.text
        pieces = _split(text)
        total = sum(len(p) for p in pieces) or 1
        t = start / FPS
        for p in pieces:
            d = clip.duration * len(p) / total
            out.append((t, t + d, p))
            t += d
    return out


def write_srt(c: list[tuple[float, float, str]], path: Path) -> Path:
    lines = []
    for i, (a, b, t) in enumerate(c, 1):
        lines += [str(i), f"{_ts(a)} --> {_ts(max(b, a + 0.4))}", t, ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def translate(lines: list[str]) -> list[str] | None:
    """Hindi → natural English, keeping exam terms. Returns None if it can't be done
    (so a Hindi file is never uploaded as "English")."""
    out: list[str] = []
    for i in range(0, len(lines), 60):
        batch = lines[i : i + 60]
        user = (
            "Translate each Hindi line into natural, simple English subtitles. Keep names, scheme names, "
            "numbers and English terms exactly. Return JSON {\"lines\": [...]} with the same number of items, same order.\n\n"
            + json.dumps(batch, ensure_ascii=False)
        )
        try:
            res, _ = llm.chat("You translate subtitles accurately.", user, want_json=True, temperature=0.2, max_tokens=8000)
            got = [str(x) for x in (res or {}).get("lines", [])]
            if len(got) != len(batch):
                return None
            out += got
        except llm.LLMError:
            return None
    # sanity check: real English has almost no Devanagari letters
    deva = sum(1 for t in out for ch in t if "\u0900" <= ch <= "\u097F")
    total = sum(len(t) for t in out) or 1
    return out if deva / total < 0.1 else None


def make(plan: Plan, folder: Path, english: bool = True) -> dict[str, Path]:
    files = {"hi": write_srt(cues(plan), folder / "captions.hi.srt")}
    if english:
        en = translate([c.text for _, c in plan.voice])
        if en:
            files["en"] = write_srt(cues(plan, en), folder / "captions.en.srt")
        else:
            print("English subtitles skipped: translation not available")
    return files
