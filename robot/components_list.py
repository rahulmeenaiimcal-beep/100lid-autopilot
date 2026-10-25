"""The names the script writer is allowed to use. Icons and objects are read straight
from the animation code, so the two can never drift apart."""
from __future__ import annotations

import re

from . import settings


def _keys(file: str, block: str) -> list[str]:
    src = (settings.VIDEO / "src" / "components" / file).read_text(encoding="utf-8")
    i = src.find(block)
    if i < 0:
        return []
    eq = src.find("= {", i)
    depth, j = 0, (eq + 2 if eq >= 0 else src.find("{", i))
    start = j
    while j < len(src):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    body = src[start + 1 : j]
    # top-level keys only: lines like `  name: ...` / `  "name": ...`
    return re.findall(r"^\s{2}\"?([a-z_]+)\"?:\s", body, flags=re.M)


ALLOWED_ICONS = _keys("Icon.tsx", "export const ICONS") or ["bank", "document", "coins", "check"]
ANATOMY_OBJECTS = [k for k in _keys("Devices.tsx", "const OBJECTS") if k] or ["generic"]
CUTAWAY_OBJECTS = _keys("Devices.tsx", "const SHELLS") or ["box"]
DEVICE_KINDS = ["knolling", "exploded", "cutaway", "anatomy", "stat", "timeline", "compare", "steps", "keyfacts"]
EMOTIONS = ["neutral", "happy", "excited", "curious", "worried", "shocked", "thinking", "proud"]
GESTURES = ["none", "point", "raise", "think", "wave", "explain", "thumbs"]
SETTINGS = ["classroom", "bank", "village", "shop", "home", "office", "studio"]
