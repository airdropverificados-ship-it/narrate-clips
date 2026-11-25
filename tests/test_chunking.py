"""Unit tests for narrate_clips.chunking (no network, no ffmpeg)."""

import unittest

from narrate_clips.chunking import chunk_text, split_sentences, word_count


class TestSplitSentences(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(
            split_sentences("Hello world. How are you? Fine!"),
            ["Hello world.", "How are you?", "Fine!"])

    def test_empty(self):
        self.assertEqual(split_sentences("   "), [])


class TestChunkText(unittest.TestCase):
    def test_keeps_order_and_words(self):
        text = ("The old house on the hill had been empty for twenty years. "
                "Nobody in the village would walk past it after dark. "
                "The windows were always shut, and yet every morning one of "
                "them stood open.")
        chunks = chunk_text(text)
        self.assertEqual(" ".join(chunks), rejoin(text))
        total = sum(word_count(c) for c in chunks)
        self.assertEqual(total, len(text.split()))

    def test_no_chunk_over_max(self):
        text = " ".join(f"word{i}." for i in range(200))
        # One "sentence" of 200 words must be split on words.
        chunks = chunk_text(text, target_words=25, max_words=30)
        self.assertTrue(all(word_count(c) <= 30 for c in chunks))
        self.assertEqual(sum(word_count(c) for c in chunks), 200)

    def test_short_line_is_merged(self):
        text = ("She opened the door slowly and stepped into the dark "
                "hallway of the old house. Yes. The floor creaked under "
                "her feet as she moved toward the stairs at the far end "
                "of the hall.")
        chunks = chunk_text(text)
        # "Yes." must not stand alone as its own clip.
        self.assertTrue(all(word_count(c) >= 10 for c in chunks[:-1]))
        self.assertNotIn("Yes.", chunks)

    def test_sentence_not_split(self):
        text = ("The lighthouse keeper lit the lamp every night without "
                "fail. The ships far out at sea depended on that single "
                "point of light to find their way home safely.")
        chunks = chunk_text(text, target_words=25)
        # 30 words total, two sentences: one chunk if it fits the target.
        self.assertEqual(len(chunks), 2)
        self.assertTrue(chunks[0].endswith("fail."))

    def test_target_words_respected(self):
        words = ("alpha beta gamma delta epsilon zeta eta theta iota kappa "
                 "lambda mu nu xi omicron pi rho sigma tau upsilon phi chi "
                 "psi omega one two three four five six seven eight nine "
                 "ten eleven twelve thirteen fourteen fifteen sixteen.")
        chunks = chunk_text(words, target_words=25, max_words=30)
        self.assertTrue(all(word_count(c) <= 30 for c in chunks))
        self.assertGreaterEqual(len(chunks), 2)


def rejoin(text):
    return " ".join(text.split())


if __name__ == "__main__":
    unittest.main()
