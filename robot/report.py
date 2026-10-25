"""The plain-language 3-day report. Saved in data/reports/ and sent to you as a
GitHub issue (which GitHub emails you)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from . import ledger as L
from . import review, settings, youtube


def _watch_hours_long_365() -> tuple[float, bool]:
    """Long-video watch hours in the last 365 days (what monetization counts).
    Returns (hours, exact). Falls back to all watch time if the split isn't available."""
    start = (date.today() - timedelta(days=365)).isoformat()
    try:
        r = youtube.ya().reports().query(ids="channel==MINE", startDate=start, endDate=date.today().isoformat(),
                                         metrics="estimatedMinutesWatched", dimensions="creatorContentType").execute()
        mins = sum(float(row[1]) for row in (r.get("rows") or []) if str(row[0]).upper() not in ("SHORTS", "SHORT"))
        return mins / 60, True
    except Exception:
        try:
            r = youtube.ya().reports().query(ids="channel==MINE", startDate=start, endDate=date.today().isoformat(),
                                             metrics="estimatedMinutesWatched").execute()
            return float((r.get("rows") or [[0]])[0][0]) / 60, False
        except Exception:
            return 0.0, False


def build(d: dict) -> str:
    today = date.today()
    lines = [f"# 📊 100LID report — {today:%d %b %Y}", ""]
    if not youtube.ready():
        return "\n".join(lines + ["YouTube is not connected yet, so there are no numbers to report."])
    ch = youtube.my_channel()
    stats = ch.get("statistics", {})
    subs = int(stats.get("subscriberCount", 0))
    daily = youtube.channel_daily(30)
    last3 = daily[-3:]
    prev3 = daily[-6:-3]
    v3, v3p = sum(int(x["views"]) for x in last3), sum(int(x["views"]) for x in prev3)
    s3 = sum(int(x["subscribersGained"]) - int(x["subscribersLost"]) for x in last3)
    m28 = sum(float(x["estimatedMinutesWatched"]) for x in daily[-28:])
    hours, exact = _watch_hours_long_365()
    pace = m28 / 60 / 28 if daily else 0
    need = max(0.0, 4000 - hours)
    months = (need / (pace * 30)) if pace > 0 else None
    lines += [
        "## In plain words",
        f"- **Last 3 days:** {v3:,} views ({'up' if v3 >= v3p else 'down'} from {v3p:,}), {s3:+} subscribers.",
        f"- **Subscribers:** {subs:,} (1,000 needed ✅)" if subs >= 1000 else f"- **Subscribers:** {subs:,} of 1,000 needed",
        f"- **Watch hours (last 12 months{'' if exact else ', incl. Shorts'}):** {hours:,.0f} of 4,000 needed.",
        f"- **Current pace:** {pace:.1f} watch hours a day" + (f" → about **{months:.1f} months** to 4,000 at this pace." if months else "."),
        "",
    ]
    # recent videos
    vids = [v for v in d["videos"] if v.get("video_id")][-15:]
    if vids:
        lines += ["## Latest videos", "", "| Video | Type | Status | Views | Avg watched | Subs |", "|---|---|---|---|---|---|"]
        for v in reversed(vids):
            s = v.get("stats") or {}
            avd = s.get("avd")
            watched = f"{int(avd // 60)}:{int(avd % 60):02} ({s.get('avp', 0):.0f}%)" if avd else "—"
            title = (v.get("title") or "")[:55].replace("|", "/")
            lines.append(f"| [{title}](https://youtu.be/{v['video_id']}) | {v.get('kind')} | {v.get('status')} | {s.get('views', 0):,} | {watched} | {s.get('subs', 0)} |")
        lines.append("")
    learning = d.get("learning", {})
    lines += ["## What the robot has learned", ""]
    if learning.get("judged_long", 0) < 3:
        lines.append(f"- Too early to judge: {learning.get('judged_long', 0)} long video(s) have 3+ days of data. Choices stay balanced until there are at least 3 of a kind.")
    for dim, label in (("series", "Series"), ("teacher", "Teacher"), ("short_kind", "Short type"), ("emotion", "Thumbnail face")):
        w = (learning.get("weights") or {}).get(dim) or {}
        if w:
            best = sorted(w, key=lambda k: -w[k])
            lines.append(f"- **{label}:** best → {best[0]}" + (f", weakest → {best[-1]}" if len(best) > 1 else ""))
    dev = learning.get("devices") or {}
    if dev:
        order = sorted(dev, key=lambda k: -dev[k])
        lines.append(f"- **Visual moments that hold viewers best:** {', '.join(order[:3])}; weakest: {order[-1]}")
    lines.append("")
    # decisions
    waiting = [v for v in d["videos"] if v.get("status") == "uploaded" and v.get("issue")]
    lines += ["## Needs your decision", ""]
    if waiting:
        for v in waiting:
            lines.append(f"- Waiting for your OK: **{v.get('title', '')[:70]}** → reply on issue #{v['issue']}")
    else:
        lines.append("- Nothing right now. 🎉")
    try:
        src = youtube.traffic_sources(28)
        if src:
            tot = sum(int(x["views"]) for x in src) or 1
            lines += ["", "## Where views come from (28 days)"] + [f"- {x['insightTrafficSourceType']}: {int(x['views']) * 100 // tot}%" for x in src[:6]]
    except Exception:
        pass
    return "\n".join(lines)


def run(d: dict) -> str:
    md = build(d)
    folder = settings.DATA / "reports"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "latest.md").write_text(md, encoding="utf-8")
    (folder / f"{datetime.now(timezone.utc):%Y-%m-%d}.md").write_text(md, encoding="utf-8")
    # keep the last 20 dated reports only
    dated = sorted(p for p in folder.glob("20*.md"))
    for p in dated[:-20]:
        p.unlink()
    if not youtube.ready():
        return md
    n = review.open_issue(f"📊 Channel report — {date.today():%d %b %Y}", md, ["report"])
    if n:
        review.close_open("report", keep=n)
    return md
