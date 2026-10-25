"""Chooses the next long-video topic: keeps the monthly series mix, prefers
high-priority topics (old hits, often asked in exams), never repeats a topic
within 6 months, and leans towards series that perform well."""
from __future__ import annotations

import random
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests
import yaml

from . import settings

RSS = [
    "https://www.rbi.org.in/pressreleases_rss.xml",
    "https://www.rbi.org.in/notifications_rss.xml",
]


def bank() -> list[dict]:
    with open(settings.TOPICS / "bank.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["topics"]


def _used(ledger: dict, days: int = 180) -> set[str]:
    cut = datetime.now(timezone.utc) - timedelta(days=days)
    out = set()
    for e in ledger.get("episodes", {}).values():
        try:
            if datetime.fromisoformat(e["created"]) >= cut:
                out.add(e["topic_id"])
        except Exception:
            out.add(e.get("topic_id"))
    return out


def _month_counts(ledger: dict) -> dict[str, int]:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    c: dict[str, int] = {}
    for e in ledger.get("episodes", {}).values():
        if str(e.get("created", "")).startswith(month):
            c[e.get("series", "")] = c.get(e.get("series", ""), 0) + 1
    return c


def current_affairs_topic(ledger: dict) -> dict | None:
    """Once a month (from the 24th), a roundup built only from RBI's own announcements."""
    now = datetime.now(timezone.utc)
    tid = f"ca-{now:%Y-%m}"
    if now.day < 24 or any(e.get("topic_id") == tid for e in ledger.get("episodes", {}).values()):
        return None
    items = []
    for url in RSS:
        try:
            r = requests.get(url, timeout=40, headers={"User-Agent": "100LID-autopilot/1.0"})
            root = ET.fromstring(r.content)
            for it in root.iter("item"):
                title = (it.findtext("title") or "").strip()
                desc = (it.findtext("description") or "").strip()
                link = (it.findtext("link") or "").strip()
                date = (it.findtext("pubDate") or "").strip()
                if title:
                    items.append({"title": title, "desc": desc[:600], "link": link, "date": date})
        except Exception:
            continue
    if len(items) < 6:
        return None
    notes = "\n".join(f"- {i['date']}: {i['title']}. {i['desc']} ({i['link']})" for i in items[:40])
    return {
        "id": tid,
        "series": "current_affairs",
        "priority": 3,
        "guest": "chotu",
        "setting": "office",
        "title_en": f"Banking & RBI Current Affairs – {now:%B %Y}",
        "title_hi": f"बैंकिंग और RBI करंट अफेयर्स – {now:%B %Y}",
        "keywords": ["current affairs", "banking awareness", "RBI", f"{now:%B %Y}"],
        "_notes": "### RBI announcements this month (official RSS)\n" + notes,
        "sources": ["https://www.rbi.org.in/"],
    }


def choose(ledger: dict, skip: set[str] | None = None) -> dict:
    ca = current_affairs_topic(ledger)
    if ca and not (skip and ca["id"] in skip):
        return ca
    used = _used(ledger) | (skip or set())
    mix = settings.config().get("topic_mix", {})
    counts = _month_counts(ledger)
    weights = (ledger.get("learning", {}).get("weights", {}) or {}).get("series", {})
    best_series, best_score = None, -1e9
    for s, target in mix.items():
        if s == "current_affairs":
            continue
        deficit = (target - counts.get(s, 0)) / max(1, target)
        score = deficit + 0.25 * (weights.get(s, 1.0) - 1.0) + random.random() * 0.05
        if score > best_score and any(t["series"] == s and t["id"] not in used for t in bank()):
            best_series, best_score = s, score
    pool = [t for t in bank() if t["id"] not in used and (best_series is None or t["series"] == best_series)]
    if not pool:
        pool = [t for t in bank() if t["id"] not in (skip or set())] or bank()
    top = max(t.get("priority", 1) for t in pool)
    cands = [t for t in pool if t.get("priority", 1) == top]
    return random.choice(cands)


def peek_next_title(ledger: dict, current_id: str) -> str:
    try:
        t = choose(ledger, skip={current_id})
        return f"{t['title_en'].split(' (')[0]} | {t.get('title_hi', '')}".strip(" |")
    except Exception:
        return ""
