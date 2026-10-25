"""Command line: python -m robot <command>

  check            test every connection and setting (safe, uploads nothing)
  sample           make the hand-written sample video + one Short (add --upload to upload)
  auto             make whatever is due next (used by the hourly timer)
  long / short     make one now (add --no-upload to only make the file)
  plan-month       pick next month's topics and email you the clips to record
  reply            handle your reply on a review issue (used automatically)
  stats            read YouTube numbers, learn, post pinned comments
  report           write the 3-day report
"""
from __future__ import annotations

import argparse
import sys
import traceback

from . import settings


def _housekeeping(d: dict) -> None:
    """Daily numbers + learning, and the 3-day report, if their own timer was skipped."""
    from datetime import datetime, timezone
    from . import learn, report, youtube
    if not youtube.ready():
        return

    def age_h(ts):
        try:
            return (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds() / 3600
        except Exception:
            return 1e9

    if age_h(d.get("learning", {}).get("updated", "")) > 26:
        learn.refresh(d)
        learn.learn(d)
        from .pipeline import post_pending_comments
        post_pending_comments(d)
    if age_h(d.get("last_report", "")) > 74:
        report.run(d)
        from . import ledger as L
        d["last_report"] = L.now_iso()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--issue", type=int, default=0)
    ap.add_argument("--text", default="")
    ap.add_argument("--month", default="", help="YYYY-MM for plan-month (default: next month)")
    a = ap.parse_args()
    settings.ensure_dirs()

    from . import ledger as L
    from . import pipeline, schedule

    d = L.load()
    try:
        if a.cmd == "check":
            from .check import run
            return run()
        if a.cmd in ("sample", "sample-clip"):
            pipeline.make_long(d, None, upload=a.upload, sample=True, test_clip=a.cmd == "sample-clip")
            if a.cmd == "sample-clip":
                L.save(d)
                return 0
            L.save(d)
            pipeline.make_short(d, None, upload=a.upload)
        elif a.cmd in ("auto", "long", "short"):
            kind = a.cmd
            if kind == "auto":
                from .due import main as due
                kind = due()
                if kind == "none":
                    print("nothing due — doing housekeeping if it is time")
                    _housekeeping(d)
                    L.save(d)
                    return 0
            slot = schedule.next_due(d, kind, 30 if kind == "short" else None) or schedule.next_free_after(d, kind, schedule.now())
            if kind == "long":
                pipeline.make_long(d, slot, upload=not a.no_upload)
            else:
                pipeline.make_short(d, slot, upload=not a.no_upload)
        elif a.cmd == "plan-month":
            from . import clips
            print(clips.plan_month(d, a.month or None))
        elif a.cmd == "reply":
            print(pipeline.handle_reply(d, a.issue, a.text))
            return 0  # the decision is saved as its own small file; the ledger is untouched
        elif a.cmd == "stats":
            from . import learn
            learn.refresh(d)
            learn.learn(d)
            pipeline.post_pending_comments(d)
        elif a.cmd == "report":
            from . import learn, report
            learn.refresh(d)
            learn.learn(d)
            report.run(d)
            d["last_report"] = L.now_iso()
        else:
            print(__doc__)
            return 2
    except Exception as e:
        traceback.print_exc()
        pipeline.summary(f"### ❌ Something went wrong\n```\n{str(e)[-1500:]}\n```")
        from . import review
        if a.cmd in ("auto", "long", "short") and not review.has_open("problem"):
            review.open_issue(f"Problem: the robot could not make a video ({a.cmd})", f"The run failed with:\n```\n{str(e)[-3000:]}\n```\nIt will try again in the next hour.", ["problem"])
        L.save(d)
        return 1
    L.save(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
