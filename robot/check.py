"""`python -m robot check` — tests every connection and explains problems in plain words."""
from __future__ import annotations

import time

from . import settings


def run() -> int:
    from .pipeline import summary

    rows = []

    def row(name, ok, msg=""):
        rows.append(f"| {name} | {'✅' if ok else '❌'} | {msg} |")

    cfg = settings.config()
    row("Settings file (config.yaml)", True, f"channel {cfg['channel']['name']}, review mode: {cfg.get('review_mode')}")
    # AI writers
    from . import llm
    keys = [p["name"] for p in cfg["llm"]["providers"] if settings.env(p["key_env"])]
    if keys:
        try:
            t = time.time()
            txt, who = llm.chat("Reply with one word.", "Say OK", max_tokens=20)
            row("AI writer", True, f"{who} answered in {time.time() - t:.1f}s (keys found: {', '.join(keys)})")
        except Exception as e:
            row("AI writer", False, f"keys found ({', '.join(keys)}) but no answer: {str(e)[:160]}")
    else:
        row("AI writer", False, "no AI key yet — add GEMINI_API_KEY (see the setup guide)")
    # voice
    try:
        from .tts import Voices
        c = Voices(settings.WORK / "voice-check", engine="edge")("guruji", "नमस्ते, मैं गुरुजी हूँ।")
        row("Hindi voice (Microsoft)", c.duration > 0.5, f"{c.duration:.1f}s test clip")
    except Exception as e:
        row("Hindi voice (Microsoft)", False, str(e)[:160])
    # YouTube
    from . import youtube
    if youtube.ready():
        try:
            ch = youtube.my_channel()
            want = cfg["channel"].get("channel_id")
            ok = ch.get("id") == want
            row("YouTube login", ok, f"logged in as **{ch.get('snippet', {}).get('title')}** ({ch.get('id')})" + ("" if ok else f" — expected {want}! Uploads are blocked until this matches."))
        except Exception as e:
            row("YouTube login", False, str(e)[:200])
    else:
        row("YouTube login", False, "not connected yet — add YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN")
    from . import review
    row("Review emails (GitHub issues)", review.enabled(), "" if review.enabled() else "only works inside GitHub Actions")
    summary("## Connection check\n\n| What | OK? | Details |\n|---|---|---|\n" + "\n".join(rows))
    return 0 if all("✅" in r for r in rows[:3]) else 1
