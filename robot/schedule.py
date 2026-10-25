"""Publishing slots (India time) and which one needs a video next."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import settings

DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def tz() -> ZoneInfo:
    return ZoneInfo(settings.config()["schedule"].get("timezone", "Asia/Kolkata"))


def now() -> datetime:
    return datetime.now(tz())


def slots(kind: str, start: datetime, end: datetime) -> list[datetime]:
    rules = settings.config()["schedule"]["long" if kind == "long" else "shorts"]
    out = []
    d = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while d <= end:
        for r in rules:
            hh, mm = [int(x) for x in str(r["time"]).split(":")]
            if r["day"] == "daily" or DAYS.get(str(r["day"])[:3].lower()) == d.weekday():
                s = d.replace(hour=hh, minute=mm)
                if start <= s <= end:
                    out.append(s)
        d += timedelta(days=1)
    return sorted(out)


def key(kind: str, when: datetime) -> str:
    return f"{kind}@{when.isoformat(timespec='minutes')}"


def taken(ledger: dict) -> set[str]:
    return {v["slot"] for v in ledger.get("videos", []) if v.get("slot") and v.get("status") not in ("rejected", "failed")}


def next_due(ledger: dict, kind: str, ahead_hours: float | None = None) -> datetime | None:
    cfg = settings.config()["schedule"]
    ahead = ahead_hours if ahead_hours is not None else float(cfg.get("make_ahead_hours", 48))
    n = now()
    used = taken(ledger)
    for s in slots(kind, n + timedelta(minutes=45), n + timedelta(hours=ahead)):
        if key(kind, s) not in used:
            return s
    return None


def next_free_after(ledger: dict, kind: str, after: datetime) -> datetime:
    used = taken(ledger)
    for s in slots(kind, after, after + timedelta(days=14)):
        if key(kind, s) not in used:
            return s
    return after


def uploads_today(ledger: dict) -> int:
    today = now().date().isoformat()
    return sum(1 for v in ledger.get("videos", []) if str(v.get("uploaded_at", "")).startswith(today))


def to_utc_iso(when: datetime) -> str:
    return when.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def pretty(when: datetime) -> str:
    return when.strftime("%a %d %b, %I:%M %p IST").replace(" 0", " ")
