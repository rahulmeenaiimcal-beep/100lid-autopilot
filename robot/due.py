"""Quick check (no heavy installs needed): does a video need making right now?
Prints one word: long, short or none."""
from __future__ import annotations

import json
import sys

from . import schedule, settings
from . import ledger as L


def has_pending_short(d: dict) -> bool:
    for eid, e in d.get("episodes", {}).items():
        if e.get("rejected") or e.get("test"):
            continue
        ep = L.load_episode(eid)
        if ep and len(e.get("shorts_done", [])) < len(ep.get("shorts") or []):
            return True
    return False


def main() -> str:
    d = L.load(apply=False)
    cfg = settings.config()["schedule"]
    if schedule.uploads_today(d) >= int(cfg.get("max_uploads_per_day", 3)):
        return "none"
    if schedule.next_due(d, "long"):
        return "long"
    if schedule.next_due(d, "short", 30) and has_pending_short(d):
        return "short"
    return "none"


if __name__ == "__main__":
    print(main())
    sys.exit(0)
