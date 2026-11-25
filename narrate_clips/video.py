"""Assemble narrated clips with ffmpeg.

Each clip is a vertical 720x1280 video: a solid-colour background, the
chunk text burned in as a subtitle (libass `subtitles` filter), and the
chunk narration as the audio track. Clips are then optionally joined
into one video.
"""

from __future__ import annotations

import os
import subprocess

WIDTH, HEIGHT = 720, 1280


class VideoError(RuntimeError):
    pass


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise VideoError(
            "ffmpeg failed: " + " ".join(cmd) + "\n"
            + proc.stderr.strip()[-800:])


def probe_duration(path: str) -> float:
    """Duration in seconds via ffprobe."""
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True)
    if proc.returncode != 0:
        raise VideoError(f"ffprobe could not read {path!r}: "
                         + proc.stderr.strip()[-300:])
    return float(proc.stdout.strip())


def _write_srt(text: str, duration: float, path: str) -> None:
    """One caption spanning the whole clip, split into readable lines."""
    words = text.split()
    lines, line = [], ""
    for word in words:
        candidate = (line + " " + word).strip() if line else word
        if len(candidate) > 34 and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    caption = "\n".join(lines)
    end = max(duration - 0.05, 0.1)
    srt = ("1\n00:00:00,000 --> " + _srt_time(end) + "\n"
           + caption + "\n")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(srt)


def _srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def make_clip(audio_path: str, text: str, out_path: str,
              bg: str = "0x1a1a2e",
              font: str = "DejaVu Sans", font_size: int = 30) -> str:
    """Build one vertical clip from narration audio + caption text."""
    duration = probe_duration(audio_path)
    srt_path = out_path + ".srt"
    _write_srt(text, duration, srt_path)
    style = (f"FontName={font},FontSize={font_size},"
             "PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,"
             "BorderStyle=1,Outline=2,Alignment=2,MarginV=140")
    # Escape the path for the subtitles filter (colons, quotes).
    srt_escaped = srt_path.replace(":", "\\:").replace("'", "\\'")
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i",
        f"color=c={bg}:s={WIDTH}x{HEIGHT}:d={duration:.3f}",
        "-i", audio_path,
        "-vf", f"subtitles='{srt_escaped}':force_style='{style}'",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart",
        out_path,
    ]
    _run(cmd)
    os.remove(srt_path)
    return out_path


def join_clips(clip_paths: list[str], out_path: str) -> str:
    """Concatenate clips (same codec and size) into one video."""
    list_path = out_path + ".txt"
    with open(list_path, "w", encoding="utf-8") as fh:
        for clip in clip_paths:
            safe = os.path.abspath(clip).replace("'", "'\\''")
            fh.write(f"file '{safe}'\n")
    _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
          "-i", list_path, "-c", "copy", out_path])
    os.remove(list_path)
    return out_path
