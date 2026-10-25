"""Reads YouTube's numbers for every video and learns what works:
which series, teachers, thumbnail styles and Short types do best, and which
visual moments (knolling, cutaway, ...) hold viewers — using the real retention
curve around the exact seconds where each moment appears.

It changes its choices only after 3+ videos of a kind, and always keeps ~30%
of choices as experiments."""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from . import ledger as L
from . import youtube

MIN_SAMPLES = 3
EXPLORE = 0.3


def _age_days(v: dict) -> float:
    t = v.get("published_at") or v.get("uploaded_at")
    if not t:
        return 0
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(t.replace("Z", "+00:00"))).total_seconds() / 86400
    except Exception:
        return 0


def refresh(d: dict) -> None:
    vids = [v for v in d["videos"] if v.get("video_id")]
    if not vids or not youtube.ready():
        return
    st = youtube.video_status([v["video_id"] for v in vids])
    for v in vids:
        it = st.get(v["video_id"])
        if not it:
            if v.get("status") not in ("rejected",):
                v["status"] = "missing"
            continue
        priv = it["status"].get("privacyStatus")
        if priv == "public" and v.get("status") != "public":
            v["status"] = "public"
            v["published_at"] = it["snippet"].get("publishedAt") or L.now_iso()
        elif it["status"].get("publishAt") and priv == "private":
            v["status"] = "scheduled"
        s = it.get("statistics", {})
        v.setdefault("stats", {}).update({"views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)), "comments": int(s.get("commentCount", 0))})
    public = [v for v in vids if v.get("status") == "public"]
    an = youtube.analytics([v["video_id"] for v in public], start=(datetime.now(timezone.utc) - timedelta(days=400)).date())
    for v in public:
        a = an.get(v["video_id"])
        if a:
            v["stats"].update({
                "views": int(a.get("views", 0)),
                "minutes": float(a.get("estimatedMinutesWatched", 0)),
                "avd": float(a.get("averageViewDuration", 0)),
                "avp": float(a.get("averageViewPercentage", 0)),
                "subs": int(a.get("subscribersGained", 0)),
                "shares": int(a.get("shares", 0)),
            })
        v["stats"]["updated"] = L.now_iso()
        # retention curve for long videos (only once they have some views)
        if v.get("kind") == "long" and v["stats"].get("views", 0) >= 50 and _age_days(v) >= 3 and not v.get("retention_done_at_views") == v["stats"]["views"]:
            curve = youtube.retention(v["video_id"])
            if curve:
                v["retention"] = [[round(a, 3), round(b, 3)] for a, b in curve[::5]]
                v["beat_scores"] = beat_scores(curve, v.get("beats") or [], v.get("frames") or 0)
                v["retention_done_at_views"] = v["stats"]["views"]


def beat_scores(curve: list[tuple[float, float]], beats: list[dict], frames: int) -> list[dict]:
    """How well each visual moment kept viewers, compared with the video's average."""
    if not curve or not frames:
        return []

    def at(x: float) -> float:
        best = min(curve, key=lambda p: abs(p[0] - x))
        return best[1]

    total_drop = max(1e-6, curve[0][1] - curve[-1][1])
    avg_drop_per_ratio = total_drop / max(1e-6, curve[-1][0] - curve[0][0])
    out = []
    for b in beats:
        a, z = b["from"] / frames, b["to"] / frames
        if z - a < 0.01:
            continue
        drop = (at(a) - at(z)) / (z - a)
        out.append({"kind": b["kind"], "where": b.get("where"), "score": round(avg_drop_per_ratio - drop, 3)})
    return out


def _rank_scores(items: list[dict], key) -> dict[int, float]:
    vals = sorted((key(v), i) for i, v in enumerate(items))
    n = max(1, len(vals) - 1)
    return {i: r / n for r, (_, i) in enumerate(vals)}


def learn(d: dict) -> None:
    longs = [v for v in d["videos"] if v.get("kind") == "long" and v.get("status") == "public" and _age_days(v) >= 3 and v.get("stats")]
    shorts = [v for v in d["videos"] if v.get("kind") == "short" and v.get("status") == "public" and _age_days(v) >= 2 and v.get("stats")]
    w: dict[str, dict] = {"series": {}, "teacher": {}, "palette": {}, "layout": {}, "emotion": {}, "short_kind": {}}

    def score_set(items, weights_avp=0.5):
        if not items:
            return {}
        r_avp = _rank_scores(items, lambda v: v["stats"].get("avp", 0))
        r_views = _rank_scores(items, lambda v: v["stats"].get("views", 0))
        r_subs = _rank_scores(items, lambda v: v["stats"].get("subs", 0))
        return {i: weights_avp * r_avp[i] + 0.3 * r_views[i] + (0.7 - weights_avp) * r_subs[i] for i in range(len(items))}

    sc = score_set(longs)
    for i, v in enumerate(longs):
        v["score"] = round(sc[i], 3)
    groups: dict[tuple[str, str], list[float]] = {}
    for i, v in enumerate(longs):
        th = v.get("thumb") or {}
        for dim, val in (("series", v.get("series")), ("teacher", (v.get("cast") or {}).get("teacher")),
                         ("palette", th.get("palette")), ("layout", th.get("layout")), ("emotion", th.get("emotion"))):
            if val is not None:
                groups.setdefault((dim, str(val)), []).append(sc[i])
    ss = score_set(shorts, 0.4)
    for i, v in enumerate(shorts):
        v["score"] = round(ss[i], 3)
        groups.setdefault(("short_kind", str(v.get("short_kind"))), []).append(ss[i])
    for (dim, val), arr in groups.items():
        if len(arr) >= MIN_SAMPLES:
            m = sum(arr) / len(arr)
            w[dim][val] = round(1 + (m - 0.5), 3)  # 0.5 .. 1.5
    dev: dict[str, list[float]] = {}
    for v in longs:
        for b in v.get("beat_scores") or []:
            dev.setdefault(b["kind"], []).append(b["score"])
    devices = {k: round(sum(a) / len(a), 3) for k, a in dev.items() if len(a) >= MIN_SAMPLES}
    d["learning"] = {"weights": w, "devices": devices, "judged_long": len(longs), "judged_short": len(shorts), "updated": L.now_iso()}


def pick(d: dict, dim: str, options: list, default=None):
    """Weighted choice with exploration."""
    weights = (d.get("learning", {}).get("weights", {}) or {}).get(dim, {})
    if not weights or random.random() < EXPLORE:
        return random.choice(options) if options else default
    ws = [max(0.2, weights.get(str(o), 1.0)) for o in options]
    return random.choices(options, weights=ws, k=1)[0]


def device_hint(d: dict) -> str:
    dev = d.get("learning", {}).get("devices", {})
    if len(dev) < 2:
        return ""
    best = sorted(dev, key=lambda k: -dev[k])[:3]
    worst = sorted(dev, key=lambda k: dev[k])[:1]
    return (f"\nLEARNED FROM OUR OWN RETENTION DATA: viewers stay best during {', '.join(best)} moments; "
            f"use those at the 25/50/70% marks. {worst[0]} holds viewers least — use it only where it truly fits.\n")
