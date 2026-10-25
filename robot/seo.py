"""Builds the YouTube title, description, tags and chapters for each video."""
from __future__ import annotations

from . import settings


def clean_title(t: str, limit: int = 100) -> str:
    t = (t or "").replace("<", "").replace(">", "").strip()
    if len(t) <= limit:
        return t
    cut = t[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" |-·,")


def _mmss(sec: float) -> str:
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m:02}:{s:02}"


def chapter_lines(chapters: list[tuple[float, str]]) -> list[str]:
    """YouTube needs: first chapter at 00:00, at least 3 chapters, each at least 10 seconds."""
    items = [(0.0, "शुरुआत · Intro")]
    for s, t in chapters:
        if s - items[-1][0] >= 10:
            items.append((s, t.replace("🧠", "").strip()))
    if len(items) < 3:
        return []
    return [f"{_mmss(s)} {t}" for s, t in items]


def tags(meta_tags: list[str], extra: list[str] | None = None) -> list[str]:
    out, total = [], 0
    for t in list(meta_tags or []) + list(extra or []):
        t = t.replace("<", "").replace(">", "").replace(",", " ").strip()
        if not t or t.lower() in {x.lower() for x in out}:
            continue
        cost = len(t) + (2 if " " in t else 0) + 1
        if total + cost > 480:
            break
        out.append(t)
        total += cost
    return out


def long_description(ep: dict, chapters: list[tuple[float, str]], playlist_url: str = "", next_title: str = "") -> str:
    cfg = settings.config()
    m = ep.get("meta") or {}
    parts = [m.get("summary", "").strip(), ""]
    ch = chapter_lines(chapters)
    if ch:
        parts += ["⏱️ Chapters"] + ch + [""]
    facts = []
    for s in ep.get("sections") or []:
        v = s.get("visual") or {}
        if v.get("kind") == "keyfacts":
            facts = [f"• {i['label']}" + (f" — {i['detail']}" if i.get("detail") else "") for i in v.get("items", [])]
    if facts:
        parts += ["📌 Exam Corner"] + facts + [""]
    if ep.get("quiz"):
        parts += [f"🧠 Video में {len(ep['quiz'])} सवालों का Quiz है — comment में अपना score बताएं!", ""]
    if playlist_url:
        parts += [f"📚 पूरी series: {playlist_url}"]
    if next_title:
        parts += [f"▶️ अगला video: {next_title}"]
    parts += [""]
    src = [u for u in (m.get("sources") or []) if isinstance(u, str) and u.startswith("http")]
    if src:
        parts += ["🔎 Sources (official / reference):"] + [f"- {u}" for u in src[:6]] + [""]
    as_of = ep.get("as_of", "")
    parts += [f"Facts checked as of {as_of}. Rates and limits can change — please confirm on the official website.", ""]
    note = "ℹ️ यह video सिर्फ education के लिए है, financial या legal advice नहीं।"
    if cfg["publish"].get("add_ai_note_in_description", True):
        note += " Animation और आवाज़ AI tools की मदद से बनाए गए हैं; हर script का fact-check होता है।"
    parts += [note, ""]
    if m.get("summary_en"):
        parts += ["English: " + m["summary_en"], ""]
    parts += [" ".join((m.get("hashtags") or [])[:3])]
    text = "\n".join(parts).strip()
    return text[:4900]


def long_description_en(ep: dict, chapters: list[tuple[float, str]]) -> str:
    m = ep.get("meta") or {}
    parts = [m.get("summary_en", "").strip(), ""]
    ch = chapter_lines(chapters)
    if ch:
        parts += ["Chapters"] + ch + [""]
    parts += ["Educational content only — not financial or legal advice. Animation and voices are made with AI tools; every script is fact-checked.", ""]
    parts += [" ".join((m.get("hashtags") or [])[:3])]
    return "\n".join(parts).strip()[:4900]


def short_description(ep: dict, short: dict, long_url: str = "") -> str:
    m = ep.get("meta") or {}
    first = (short.get("lines") or [{}])[0].get("text", "")
    parts = [first, ""]
    if long_url:
        parts += [f"▶️ Full video: {long_url}", ""]
    parts += ["Educational content · not financial advice · made with AI animation tools.", ""]
    parts += [" ".join(["#Shorts"] + (m.get("hashtags") or [])[:2])]
    return "\n".join(parts).strip()[:4900]
