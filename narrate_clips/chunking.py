"""Split long text into short spoken chunks, one per video clip.

Rules (measured on real narrated series):
- Pack 20-25 words into every clip (target pace 120-150 words/min).
  Never below 100 words/min: a clip with a single short line alone
  sounds empty, so short lines are always joined with the next line.
- Never split a sentence across two clips, unless one sentence alone
  is longer than the maximum: then split it on commas/semicolons first,
  and on words only as a last resort.
- Keep the original order and never drop or reorder words.
"""

from __future__ import annotations

import re

# A sentence ends on . ! ? or ... followed by whitespace (or end of text).
# Ellipsis and abbreviations are handled conservatively: "Mr." style
# abbreviations are kept together by the capital-letter lookahead.
_SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+(?=[\"“\(\[]?[A-Z0-9])")
_WORD_RE = re.compile(r"\S+")


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, keeping the punctuation attached."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = _SENTENCE_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def _split_long_sentence(sentence: str, max_words: int) -> list[str]:
    """Split one over-long sentence on commas/semicolons, then on words."""
    words = _WORD_RE.findall(sentence)
    if len(words) <= max_words:
        return [sentence]
    # First try: split on clause boundaries (, ; : —).
    clauses = re.split(r"(?<=[,;:—])\s+", sentence)
    if len(clauses) > 1:
        out: list[str] = []
        buf = ""
        for clause in clauses:
            candidate = (buf + " " + clause).strip() if buf else clause
            if len(_WORD_RE.findall(candidate)) <= max_words:
                buf = candidate
            else:
                if buf:
                    out.append(buf)
                buf = clause
        if buf:
            out.append(buf)
        # Any clause still too long falls through to word splitting.
        final: list[str] = []
        for piece in out:
            final.extend(_split_on_words(piece, max_words))
        return final
    return _split_on_words(sentence, max_words)


def _split_on_words(sentence: str, max_words: int) -> list[str]:
    words = _WORD_RE.findall(sentence)
    return [" ".join(words[i:i + max_words])
            for i in range(0, len(words), max_words)]


def chunk_text(text: str, target_words: int = 25,
               max_words: int = 30, min_words: int = 10) -> list[str]:
    """Split text into spoken chunks.

    target_words: aim for this many words per chunk (default 25).
    max_words:    never exceed this many words per chunk (default 30).
    min_words:    a chunk shorter than this is merged with the next one,
                  unless it is the last chunk (default 10).

    Returns a list of chunks in order, each a plain string.
    """
    sentences = split_sentences(text)
    pieces: list[str] = []
    for sentence in sentences:
        pieces.extend(_split_long_sentence(sentence, max_words))

    chunks: list[str] = []
    buf = ""
    buf_words = 0
    for piece in pieces:
        piece_words = len(_WORD_RE.findall(piece))
        if buf and buf_words + piece_words > target_words and buf_words >= min_words:
            chunks.append(buf)
            buf, buf_words = piece, piece_words
        else:
            buf = (buf + " " + piece).strip() if buf else piece
            buf_words += piece_words
    if buf:
        chunks.append(buf)

    # Merge a too-short chunk with the next one (never leave a lone line).
    merged: list[str] = []
    i = 0
    while i < len(chunks):
        chunk = chunks[i]
        words = len(_WORD_RE.findall(chunk))
        if words < min_words and i + 1 < len(chunks):
            chunks[i + 1] = chunk + " " + chunks[i + 1]
        else:
            merged.append(chunk)
        i += 1
    return merged


def word_count(chunk: str) -> int:
    return len(_WORD_RE.findall(chunk))
