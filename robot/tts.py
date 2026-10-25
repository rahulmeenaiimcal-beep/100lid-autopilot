"""Text-to-speech. Two free engines:

* edge   — Microsoft Edge neural voices (hi-IN Madhur & Swara), varied by pitch/speed per character.
* parler — AI4Bharat Indic Parler-TTS (Apache-2.0, runs on GitHub's own machine, no account needed).

Every clip is cached by its text+voice, so re-runs never pay twice."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import subprocess
import time
import wave
from pathlib import Path

import numpy as np

from . import settings
from .timeline import FPS, Clip

SR = 24000  # all voice clips are converted to 24 kHz mono WAV


def normalize(text: str) -> str:
    """Makes text easier for a voice to read aloud (symbols, slashes, emojis)."""
    t = text
    t = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]", "", t)   # emojis
    t = t.replace("→", " फिर ").replace("·", ", ").replace("—", ", ").replace("–", ", ")
    t = re.sub(r"(\d)\s*/\s*(\S)", r"\1 या \2", t)              # 18 साल/10वीं -> 18 साल या 10वीं
    t = re.sub(r"(\D)/(\D)", r"\1 या \2", t)
    t = t.replace("&", " और ").replace("%", " प्रतिशत")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _key(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]


def wav_info(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
        if w.getnchannels() > 1:
            data = data.reshape(-1, w.getnchannels()).mean(axis=1)
    return data, sr


def to_wav(src: Path, dst: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", str(SR), "-af",
         "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
         "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse",
         str(dst)],
        check=True,
    )


def amplitude(samples: np.ndarray, sr: int) -> list[float]:
    """Loudness per video frame (0..1), used to move the characters' mouths."""
    hop = sr / FPS
    n = int(np.ceil(len(samples) / hop))
    out = []
    for i in range(n):
        seg = samples[int(i * hop): int((i + 1) * hop)]
        out.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
    if not out:
        return out
    ref = np.percentile(out, 92) or 1e-6
    return [min(1.0, max(0.0, (v / ref) ** 0.8)) if v > ref * 0.12 else 0.0 for v in out]


# ---------------------------------------------------------------- engines
async def _edge(text: str, voice: str, rate: str, pitch: str, out_mp3: Path) -> None:
    import edge_tts  # type: ignore

    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await comm.save(str(out_mp3))


def edge_say(text: str, vcfg: dict, out_wav: Path) -> None:
    mp3 = out_wav.with_suffix(".mp3")
    last = None
    for attempt in range(4):
        try:
            asyncio.run(_edge(text, vcfg.get("voice", "hi-IN-MadhurNeural"), vcfg.get("rate", "+0%"), vcfg.get("pitch", "+0Hz"), mp3))
            if mp3.exists() and mp3.stat().st_size > 1000:
                to_wav(mp3, out_wav)
                mp3.unlink(missing_ok=True)
                return
        except Exception as e:  # network hiccups happen; retry with backoff
            last = e
        time.sleep(2 + attempt * 3)
    raise RuntimeError(f"Edge TTS failed: {last}")


class _Parler:
    model = None
    tok = None
    desc_tok = None

    @classmethod
    def load(cls):
        if cls.model is None:
            import torch  # type: ignore
            from parler_tts import ParlerTTSForConditionalGeneration  # type: ignore
            from transformers import AutoTokenizer  # type: ignore

            torch.set_num_threads(max(1, (__import__("os").cpu_count() or 2)))
            name = "ai4bharat/indic-parler-tts"
            cls.model = ParlerTTSForConditionalGeneration.from_pretrained(name)
            cls.tok = AutoTokenizer.from_pretrained(name)
            cls.desc_tok = AutoTokenizer.from_pretrained(cls.model.config.text_encoder._name_or_path)
        return cls


def parler_say(text: str, vcfg: dict, out_wav: Path) -> None:
    import torch  # type: ignore

    P = _Parler.load()
    desc = P.desc_tok(vcfg.get("description", "A clear Hindi voice."), return_tensors="pt")
    prompt = P.tok(text, return_tensors="pt")
    with torch.no_grad():
        gen = P.model.generate(
            input_ids=desc.input_ids,
            attention_mask=desc.attention_mask,
            prompt_input_ids=prompt.input_ids,
            prompt_attention_mask=prompt.attention_mask,
        )
    audio = gen.cpu().numpy().squeeze().astype(np.float32)
    sr = P.model.config.sampling_rate
    raw = out_wav.with_suffix(".raw.wav")
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    to_wav(raw, out_wav)
    raw.unlink(missing_ok=True)


# ---------------------------------------------------------------- public
class Voices:
    """Creates (and caches) the voice clip for each (character, line)."""

    def __init__(self, cache_dir: Path, engine: str | None = None):
        self.dir = cache_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        cfg = settings.config()
        self.engine = engine or cfg.get("tts", {}).get("engine", "edge")
        self.started = time.time()
        self.budget = float(cfg.get("tts", {}).get("parler_max_minutes", 40)) * 60
        self.used = {"edge": 0, "parler": 0}

    def _vcfg(self, speaker: str, engine: str) -> dict:
        c = settings.cast().get(speaker) or settings.cast().get("guruji")
        return dict((c.get("voice") or {}).get(engine) or {})

    def __call__(self, speaker: str, text: str) -> Clip:
        spoken = normalize(text)
        engine = self.engine
        if engine == "auto":
            engine = "parler" if time.time() - self.started < self.budget else "edge"
        vcfg = self._vcfg(speaker, engine if engine != "auto" else "edge")
        path = self.dir / f"{_key(engine, json.dumps(vcfg, sort_keys=True), spoken)}.wav"
        if not path.exists():
            try:
                if engine == "parler":
                    parler_say(spoken, vcfg, path)
                else:
                    edge_say(spoken, vcfg, path)
            except Exception:
                if engine == "parler":  # fall back to the Microsoft voice for the rest of this video
                    self.engine = "edge"
                    return self(speaker, text)
                raise
        self.used[engine] = self.used.get(engine, 0) + 1
        samples, sr = wav_info(path)
        dur = len(samples) / sr
        return Clip(speaker=speaker, text=text, duration=dur, amp=amplitude(samples, sr), path=str(path))
