#!/usr/bin/env python3
"""narrate-clips: turn a long text into consecutive narrated video clips.

Reads a text file, splits it into short spoken chunks (20-25 words each),
synthesises narration for every chunk and assembles one vertical video
clip per chunk, with the text burned in as a subtitle.

Usage:
    python narrate.py story.txt --out clips/
    python narrate.py story.txt --out clips/ --lang es --join
    python narrate.py story.txt --out clips/ --audio-only
    python narrate.py story.txt --out clips/ --engine piper \\
        --piper-model en_US-amy-medium.onnx
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from narrate_clips.chunking import chunk_text, word_count  # noqa: E402
from narrate_clips.tts import ENGINES, TTSError, synthesize  # noqa: E402
from narrate_clips.video import VideoError, join_clips, make_clip, probe_duration  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Turn a long text into consecutive narrated video clips.")
    parser.add_argument("text_file", help="Plain-text file to narrate")
    parser.add_argument("--out", required=True,
                        help="Output directory for the clips")
    parser.add_argument("--engine", default="gtts", choices=ENGINES,
                        help="TTS engine (default: gtts)")
    parser.add_argument("--lang", default="en",
                        help="Language code for gTTS (e.g. en, es)")
    parser.add_argument("--voice", default="en-US-AriaNeural",
                        help="Voice for the edge engine")
    parser.add_argument("--piper-model", default=None,
                        help="Path to a Piper .onnx voice model")
    parser.add_argument("--bg", default="0x1a1a2e",
                        help="Background colour, hex (default 0x1a1a2e)")
    parser.add_argument("--words-per-clip", type=int, default=25,
                        help="Target words per clip (default 25)")
    parser.add_argument("--audio-only", action="store_true",
                        help="Produce MP3 narration only, no video")
    parser.add_argument("--join", action="store_true",
                        help="Also join all clips into one video")
    args = parser.parse_args(argv)

    if not os.path.exists(args.text_file):
        print(f"error: no such file: {args.text_file}", file=sys.stderr)
        return 2
    with open(args.text_file, encoding="utf-8") as fh:
        text = fh.read()
    chunks = chunk_text(text, target_words=args.words_per_clip)
    if not chunks:
        print("error: no text to narrate", file=sys.stderr)
        return 2

    os.makedirs(args.out, exist_ok=True)
    ext = "mp3" if args.engine == "gtts" or args.engine == "edge" else "wav"
    clip_paths: list[str] = []
    total_seconds = 0.0
    try:
        for i, chunk in enumerate(chunks, start=1):
            tag = f"clip-{i:02d}"
            audio_path = os.path.join(args.out, f"{tag}.{ext}")
            synthesize(chunk, audio_path, engine=args.engine,
                       lang=args.lang, voice=args.voice,
                       piper_model=args.piper_model)
            seconds = probe_duration(audio_path)
            total_seconds += seconds
            if args.audio_only:
                print(f"[{i}/{len(chunks)}] {tag}.{ext} "
                      f"({word_count(chunk)} words, {seconds:.1f} s)")
                continue
            clip_path = os.path.join(args.out, f"{tag}.mp4")
            make_clip(audio_path, chunk, clip_path, bg=args.bg)
            clip_paths.append(clip_path)
            print(f"[{i}/{len(chunks)}] {tag}.mp4 "
                  f"({word_count(chunk)} words, {seconds:.1f} s)")
    except (TTSError, VideoError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.join and clip_paths:
        joined = os.path.join(args.out, "full.mp4")
        join_clips(clip_paths, joined)
        print(f"joined: {joined}")

    print(f"done: {len(chunks)} clips, {total_seconds:.1f} s of narration "
          f"in {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
