import pytest
from lake_of_vectors.sync.chunker import chunk_text


def test_short_text_returns_single_chunk():
    text = "This is a short sentence."
    chunks = chunk_text(text, max_tokens=500, overlap_tokens=50)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_long_text_is_split_into_multiple_chunks():
    # Create text that's clearly longer than 500 tokens (~2000 words)
    paragraphs = []
    for i in range(40):
        paragraphs.append(f"Paragraph {i}. " + "word " * 50)
    text = "\n\n".join(paragraphs)

    chunks = chunk_text(text, max_tokens=500, overlap_tokens=50)
    assert len(chunks) > 1


def test_chunks_have_overlap():
    paragraphs = []
    for i in range(20):
        paragraphs.append(f"Unique marker {i}. " + "filler " * 80)
    text = "\n\n".join(paragraphs)

    chunks = chunk_text(text, max_tokens=200, overlap_tokens=50)
    assert len(chunks) >= 2

    # Check that there's some shared content between consecutive chunks
    for i in range(len(chunks) - 1):
        words_current = set(chunks[i].split()[-30:])
        words_next = set(chunks[i + 1].split()[:30])
        overlap = words_current & words_next
        assert len(overlap) > 0, f"No overlap between chunk {i} and {i+1}"


def test_splits_on_double_newline_first():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = chunk_text(text, max_tokens=5, overlap_tokens=0)
    # Should split on paragraph boundaries
    assert any("First paragraph." in c for c in chunks)
    assert any("Second paragraph." in c for c in chunks)


def test_empty_text_returns_empty_list():
    chunks = chunk_text("", max_tokens=500, overlap_tokens=50)
    assert chunks == []


def test_whitespace_only_returns_empty_list():
    chunks = chunk_text("   \n\n  ", max_tokens=500, overlap_tokens=50)
    assert chunks == []


def test_no_separator_in_large_text_does_not_recurse():
    # A long string with no whitespace or punctuation — all separators fail,
    # must fall back to hard character split without RecursionError.
    text = "a" * 10000
    chunks = chunk_text(text, max_tokens=10, overlap_tokens=2)
    assert len(chunks) > 1
    assert all(len(c) <= 10 * 4 + 1 for c in chunks)


def test_large_real_world_note_does_not_recurse():
    # Simulates a large note with some structure — regression for the RecursionError
    # triggered when syncing larger Obsidian vaults.
    line = "This is a sentence with some words. " * 20
    text = "\n".join([line] * 100)  # ~72k chars, no double-newlines
    chunks = chunk_text(text, max_tokens=500, overlap_tokens=50)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 500 * 4 + 200  # allow a little slack for overlap
