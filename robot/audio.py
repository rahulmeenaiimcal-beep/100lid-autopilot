"""Sound: original background music (composed by code, so no copyright claims ever),
small sound effects for the visual moments, and the final mix with voice ducking."""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import numpy as np

from .timeline import FPS, Plan
from .tts import wav_info

SR = 48000
NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}

# Each series gets its own key, tempo and chord loop so episodes in a series sound related.
MOODS = {
    "schemes": ("D", 92, [0, 7, 9, 5]),            # I V vi IV — warm and hopeful
    "banking_law": ("F", 86, [0, 5, 9, 7]),         # I IV vi V — steady, serious
    "rbi_economy": ("A", 96, [9, 5, 0, 7]),         # vi IV I V — curious
    "current_affairs": ("G", 104, [0, 9, 5, 7]),    # newsy and brisk
    "shorts": ("E", 112, [0, 7, 9, 5]),
}


def hz(semitones_from_a4: float) -> float:
    return 440.0 * 2 ** (semitones_from_a4 / 12)


def _env(n: int, a: float, r: float) -> np.ndarray:
    e = np.ones(n, dtype=np.float32)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def music_loop(series: str, seed: int = 0) -> np.ndarray:
    key, bpm, prog = MOODS.get(series, MOODS["schemes"])
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    bar = beat * 4
    bars = len(prog) * 2
    n = int(bars * bar * SR)
    out = np.zeros(n, dtype=np.float32)
    root = NOTE[key] - 9  # semitones from A
    for b in range(bars):
        deg = prog[b % len(prog)]
        minor = deg in (9, 2, 4)
        chord = [deg, deg + (3 if minor else 4), deg + 7]
        start = int(b * bar * SR)
        ln = int(bar * SR)
        t = np.arange(ln) / SR
        # soft pad
        pad = np.zeros(ln, dtype=np.float32)
        for c in chord:
            f0 = hz(root + c - 12)
            pad += 0.33 * (np.sin(2 * np.pi * f0 * t) + 0.25 * np.sin(2 * np.pi * 2 * f0 * t))
        pad *= _env(ln, 0.4, 0.5) * 0.18
        out[start:start + ln] += pad
        # plucked arpeggio on eighth notes
        for k in range(8):
            ps = start + int(k * beat / 2 * SR)
            pl = int(beat / 2 * SR)
            if ps + pl > n:
                break
            c = chord[[0, 1, 2, 1, 0, 2, 1, 2][k]] + (12 if rng.random() > 0.7 else 0)
            f0 = hz(root + c)
            tt = np.arange(pl) / SR
            tone = np.sin(2 * np.pi * f0 * tt) * np.exp(-tt * 9) * 0.16
            out[ps:ps + pl] += tone.astype(np.float32)
        # light kick + shaker
        for k in range(4):
            ks = start + int(k * beat * SR)
            kl = int(0.18 * SR)
            if ks + kl > n:
                break
            tt = np.arange(kl) / SR
            kick = np.sin(2 * np.pi * (55 + 60 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 18) * (0.22 if k % 2 == 0 else 0.12)
            out[ks:ks + kl] += kick.astype(np.float32)
            hs = ks + int(beat / 2 * SR)
            hl = int(0.05 * SR)
            if hs + hl < n:
                out[hs:hs + hl] += (rng.standard_normal(hl) * np.exp(-np.arange(hl) / SR * 80) * 0.03).astype(np.float32)
    return out


def sfx(kind: str) -> np.ndarray:
    rng = np.random.default_rng(len(kind))
    if kind == "whoosh":
        n = int(0.45 * SR)
        t = np.arange(n) / SR
        noise = rng.standard_normal(n).astype(np.float32)
        # sweep a simple low-pass by mixing smoothed noise
        k = np.linspace(40, 4, n).astype(int)
        cs = np.cumsum(noise)
        sm = np.array([(cs[i] - cs[max(0, i - k[i])]) / k[i] for i in range(n)], dtype=np.float32)
        return sm * np.sin(np.pi * t / t[-1]) * 0.5
    if kind == "pop":
        n = int(0.09 * SR)
        t = np.arange(n) / SR
        return (np.sin(2 * np.pi * (700 + 500 * t / t[-1]) * t) * np.exp(-t * 45) * 0.35).astype(np.float32)
    if kind == "hit":
        n = int(0.6 * SR)
        t = np.arange(n) / SR
        boom = np.sin(2 * np.pi * (45 + 90 * np.exp(-t * 20)) * t) * np.exp(-t * 6)
        crack = rng.standard_normal(n) * np.exp(-t * 30) * 0.3
        return ((boom + crack) * 0.55).astype(np.float32)
    if kind == "tick":
        one = int(0.03 * SR)
        t = np.arange(one) / SR
        click = np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 200) * 0.3
        out = np.zeros(int(5.0 * SR), dtype=np.float32)
        for s in range(5):
            out[int(s * SR): int(s * SR) + one] += click.astype(np.float32)
        return out
    if kind == "ding":
        n = int(1.0 * SR)
        t = np.arange(n) / SR
        return ((np.sin(2 * np.pi * 880 * t) + 0.6 * np.sin(2 * np.pi * 1320 * t)) * np.exp(-t * 4) * 0.25).astype(np.float32)
    return np.zeros(1, dtype=np.float32)


def _resample(x: np.ndarray, sr: int) -> np.ndarray:
    if sr == SR:
        return x
    n = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def mix(plan: Plan, series: str, out_wav: Path, seed: int = 0) -> Path:
    total = int(plan.props["durationInFrames"] / FPS * SR) + SR
    voice = np.zeros(total, dtype=np.float32)
    for start_frame, clip in plan.voice:
        if not clip.path:
            continue
        x, sr = wav_info(Path(clip.path))
        x = _resample(x, sr)
        s = int(start_frame / FPS * SR)
        e = min(total, s + len(x))
        voice[s:e] += x[: e - s]
    # music, looped, ducked under the voice
    loop = music_loop(series, seed)
    reps = int(np.ceil(total / len(loop)))
    music = np.tile(loop, reps)[:total]
    act = np.abs(voice) > 0.01
    win = int(0.25 * SR)
    cs = np.cumsum(act.astype(np.float32))
    smooth = (cs - np.concatenate([np.zeros(win), cs[:-win]])) / win
    smooth = np.clip(smooth * 3, 0, 1)
    gain = 0.30 - 0.20 * smooth  # louder in pauses, quiet under speech
    fade = np.ones(total, dtype=np.float32)
    fl = int(1.5 * SR)
    fade[-fl:] = np.linspace(1, 0, fl)
    music = music * gain * fade * 0.6
    fx = np.zeros(total, dtype=np.float32)
    for frame, kind in plan.sfx:
        x = sfx(kind)
        s = int(frame / FPS * SR)
        e = min(total, s + len(x))
        if s < total:
            fx[s:e] += x[: e - s] * 0.5
    master = voice + music + fx
    peak = float(np.max(np.abs(master))) or 1.0
    master = master / peak * 0.89
    stereo = np.repeat((np.clip(master, -1, 1) * 32767).astype(np.int16)[:, None], 2, axis=1)
    raw = out_wav.with_suffix(".premix.wav")
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())
    # broadcast-style loudness (-14 LUFS, like YouTube's own target)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), str(out_wav)], check=True)
    raw.unlink(missing_ok=True)
    return out_wav
