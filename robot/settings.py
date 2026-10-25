"""Loads config.yaml and knows where every folder is."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WORK = ROOT / "work"          # temporary files for one run (not saved to GitHub)
OUT = ROOT / "out"            # finished videos for one run (not saved to GitHub)
VIDEO = ROOT / "video"        # the Remotion animation project
PUBLIC = VIDEO / "public"     # files the renderer can read
TOPICS = ROOT / "topics"
SAMPLES = ROOT / "samples"


@lru_cache(maxsize=1)
def config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def cast() -> dict:
    return config()["cast"]


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def ensure_dirs() -> None:
    for d in (DATA, WORK, OUT, PUBLIC, DATA / "reports"):
        d.mkdir(parents=True, exist_ok=True)
