"""Integration test: full pipeline on the sample story.

Needs network (gTTS) and ffmpeg/ffprobe. If gTTS is unreachable the
test is skipped instead of failing — the unit tests in test_chunking.py
cover the chunking logic offline.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SAMPLE = os.path.join(ROOT, "examples", "sample-story.txt")


def has_stream(path, kind):
    """kind: 'v' for video, 'a' for audio (ffprobe stream specifiers)."""
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", kind,
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
        capture_output=True, text=True)
    expected = "video" if kind == "v" else "audio"
    return proc.returncode == 0 and expected in proc.stdout


class TestPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = os.path.join(cls.tmp.name, "clips")
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "narrate.py"),
             SAMPLE, "--out", cls.out, "--join"],
            capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            cls.tmp.cleanup()
            raise unittest.SkipTest(
                "pipeline needs gTTS + ffmpeg; last error: "
                + (proc.stderr.strip()[-300:] or proc.stdout.strip()[-300:]))
        cls.proc = proc

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_clip_count_matches_chunks(self):
        from narrate_clips.chunking import chunk_text
        with open(SAMPLE, encoding="utf-8") as fh:
            expected = len(chunk_text(fh.read()))
        clips = sorted(f for f in os.listdir(self.out)
                       if f.startswith("clip-") and f.endswith(".mp4"))
        self.assertEqual(len(clips), expected)

    def test_clips_have_video_and_audio(self):
        clips = sorted(f for f in os.listdir(self.out)
                       if f.startswith("clip-") and f.endswith(".mp4"))
        self.assertTrue(clips)
        for clip in clips:
            path = os.path.join(self.out, clip)
            self.assertTrue(has_stream(path, "v"), clip)
            self.assertTrue(has_stream(path, "a"), clip)
            self.assertGreater(os.path.getsize(path), 5000, clip)

    def test_joined_video_exists(self):
        joined = os.path.join(self.out, "full.mp4")
        self.assertTrue(os.path.exists(joined))
        self.assertTrue(has_stream(joined, "v"))
        self.assertTrue(has_stream(joined, "a"))

    def test_audio_only_mode(self):
        out2 = os.path.join(self.tmp.name, "audio")
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "narrate.py"),
             SAMPLE, "--out", out2, "--audio-only"],
            capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        mp3s = [f for f in os.listdir(out2) if f.endswith(".mp3")]
        self.assertTrue(mp3s)
        self.assertFalse([f for f in os.listdir(out2)
                          if f.endswith(".mp4")])


if __name__ == "__main__":
    unittest.main()
