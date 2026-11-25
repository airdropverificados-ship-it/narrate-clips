"""Text-to-speech engines for narrate-clips.

Three engines, all free, no API key:
- "gtts"  (default): Google Translate TTS via the `gtts` package.
  Works anywhere the machine can reach translate.google.com.
- "piper": fully offline local synthesis with Piper. Needs a voice model
  (.onnx + .onnx.json), e.g. en_US-amy-medium from
  https://huggingface.co/rhasspy/piper-voices — download once, reuse.
- "edge":  Microsoft Edge TTS via the `edge-tts` package. Needs direct
  internet access to speech.platform.bing.com; fails behind proxies that
  intercept TLS (it does on some sandboxed VMs — use gtts there).

Every engine writes one audio file per chunk and returns its path.
"""

from __future__ import annotations

import os
import subprocess


class TTSError(RuntimeError):
    pass


def _require_module(name: str, install_hint: str):
    try:
        return __import__(name)
    except ImportError as exc:
        raise TTSError(
            f"The '{name}' package is not installed. Install it with: "
            f"{install_hint}") from exc


def synthesize_gtts(text: str, out_path: str, lang: str = "en") -> str:
    gtts = _require_module("gtts", "pip install gtts")
    try:
        gtts.gTTS(text, lang=lang).save(out_path)
    except Exception as exc:
        raise TTSError(f"gTTS failed for {out_path!r}: {exc}") from exc
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise TTSError(f"gTTS produced no audio at {out_path!r}")
    return out_path


def synthesize_piper(text: str, out_path: str, model: str,
                     piper_bin: str = "piper") -> str:
    if not model or not os.path.exists(model):
        raise TTSError(
            "Piper needs a voice model file (.onnx). Download one, e.g. "
            "en_US-amy-medium.onnx from "
            "https://huggingface.co/rhasspy/piper-voices, then pass "
            "--piper-model <path>.")
    try:
        proc = subprocess.run(
            [piper_bin, "-m", model, "-f", out_path],
            input=text, capture_output=True, text=True, timeout=120)
    except FileNotFoundError as exc:
        raise TTSError(
            "The 'piper' binary was not found. Install it with: "
            "pip install piper-tts") from exc
    if proc.returncode != 0:
        raise TTSError(f"piper failed: {proc.stderr.strip()[-500:]}")
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise TTSError(f"piper produced no audio at {out_path!r}")
    return out_path


def synthesize_edge(text: str, out_path: str, voice: str) -> str:
    edge_tts = _require_module("edge_tts", "pip install edge-tts")
    import asyncio

    async def _save() -> None:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(out_path)

    try:
        asyncio.run(_save())
    except Exception as exc:
        raise TTSError(
            f"edge-tts failed (it needs direct internet access to "
            f"speech.platform.bing.com): {exc}") from exc
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise TTSError(f"edge-tts produced no audio at {out_path!r}")
    return out_path


ENGINES = ("gtts", "piper", "edge")


def synthesize(text: str, out_path: str, engine: str = "gtts",
               lang: str = "en", voice: str = "en-US-AriaNeural",
               piper_model: str | None = None) -> str:
    """Synthesize one chunk of text to an audio file. Returns out_path."""
    if engine == "gtts":
        return synthesize_gtts(text, out_path, lang=lang)
    if engine == "piper":
        return synthesize_piper(text, out_path, model=piper_model or "")
    if engine == "edge":
        return synthesize_edge(text, out_path, voice=voice)
    raise TTSError(f"Unknown engine {engine!r}. Choose one of: "
                   + ", ".join(ENGINES))
