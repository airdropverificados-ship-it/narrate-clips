# narrate-clips — turn long text into consecutive narrated video clips

> Give it a text file. It splits the text into short spoken chunks
> (20–25 words each), synthesises narration for every chunk and assembles
> one vertical video clip per chunk, with the text burned in as a subtitle.
> Built for narrated series: same voice, same style, every clip in order.

## Why

Long-form narration published as short vertical clips performs better than
one long video — but recording and cutting dozens of clips by hand is slow.
This tool does the mechanical part: chunking, narration and assembly. You
write the text; it produces the clips.

## What it does

- **Sentence-aware chunking** — packs 20–25 words per clip, never splits
  a sentence across clips (unless one sentence alone is over the maximum),
  and never leaves a single short line alone in a clip.
- **Free TTS, no API key** — three engines:
  - `gtts` (default): Google Translate TTS. Works anywhere the machine
    can reach translate.google.com.
  - `piper`: fully offline local synthesis. Needs a voice model (`.onnx`)
    downloaded once.
  - `edge`: Microsoft Edge TTS. Needs direct internet access to
    `speech.platform.bing.com`; fails behind proxies that intercept TLS.
- **Vertical video** — 720×1280, solid background, burned-in subtitle,
  narration as the audio track. Optional `--join` concatenates all clips
  into one video.

## Install

Requires Python 3.10+ and `ffmpeg`/`ffprobe` on the PATH.

```bash
git clone https://github.com/airdropverificados-ship-it/narrate-clips.git
cd narrate-clips
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

For the Piper engine, also install `piper-tts` and download a voice
model once (e.g. `en_US-amy-medium.onnx` from
https://huggingface.co/rhasspy/piper-voices).

## Quickstart

```bash
python narrate.py examples/sample-story.txt --out clips/ --join
```

Output (real run, 25 Nov 2026 — the 110-word sample story):

```
[1/5] clip-01.mp4 (22 words, 8.6 s)
[2/5] clip-02.mp4 (22 words, 7.5 s)
[3/5] clip-03.mp4 (27 words, 10.2 s)
[4/5] clip-04.mp4 (20 words, 6.6 s)
[5/5] clip-05.mp4 (19 words, 6.6 s)
joined: clips/full.mp4
done: 5 clips, 39.5 s of narration in clips/
```

Every clip is 720×1280 (h264 + aac); `full.mp4` is the five clips joined
(39.5 s, 703 KB).

## More examples

```bash
# Spanish narration
python narrate.py historia.txt --out clips/ --lang es

# Audio only (MP3 per chunk, no video)
python narrate.py story.txt --out audio/ --audio-only

# Offline synthesis with a local Piper voice
python narrate.py story.txt --out clips/ --engine piper \
    --piper-model en_US-amy-medium.onnx

# Edge TTS with a specific voice
python narrate.py story.txt --out clips/ --engine edge \
    --voice en-US-AriaNeural

# Shorter clips (~15 words each)
python narrate.py story.txt --out clips/ --words-per-clip 15
```

## Options

| Option | Default | What it does |
|---|---|---|
| `--out` | — (required) | Output directory for the clips |
| `--engine` | `gtts` | `gtts`, `piper` or `edge` |
| `--lang` | `en` | Language code for gTTS (e.g. `en`, `es`) |
| `--voice` | `en-US-AriaNeural` | Voice for the edge engine |
| `--piper-model` | — | Path to a Piper `.onnx` voice model |
| `--bg` | `0x1a1a2e` | Background colour (hex) |
| `--words-per-clip` | `25` | Target words per clip |
| `--audio-only` | off | Produce MP3 narration only, no video |
| `--join` | off | Also join all clips into `full.mp4` |

## How the chunking works

1. Split the text into sentences.
2. Pack sentences into chunks of ~25 words (never over 30). A sentence
   longer than the maximum is split on commas/semicolons first, and on
   words only as a last resort.
3. A chunk shorter than 10 words is merged with the next one, so no clip
   ever holds a single short line alone.
4. Word order is never changed and no word is dropped.

This keeps the pace at roughly 120–150 words per minute — dense,
continuous narration with no dead air.

## Layout

```
narrate.py                  # CLI entry point
narrate_clips/
  chunking.py               # sentence-aware chunking
  tts.py                    # gtts / piper / edge engines
  video.py                  # ffmpeg assembly + join
examples/sample-story.txt   # 110-word sample story
tests/
  test_chunking.py          # unit tests (offline)
  test_pipeline.py          # end-to-end test (needs network + ffmpeg)
```

## Tests

```bash
python -m unittest discover -s tests -v
```

11 tests: chunking rules (word counts, order, no sentence splits,
short-line merging) plus an end-to-end run on the sample story that
checks every clip has a video and an audio stream, that `--join`
produces a valid video, and that `--audio-only` produces MP3s. The
end-to-end test is skipped automatically if gTTS is unreachable.

## License

MIT — see `LICENSE`.
