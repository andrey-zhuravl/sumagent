from sumagent_a.chunking import chunk_text


def test_chunking_limits_and_overlap() -> None:
    text = "abcdefghijklmnopqrstuvwxyz" * 10
    chunks = chunk_text(text, max_chunk_chars=50, overlap_chars=5, max_chunks=10)
    assert chunks
    assert all(len(chunk.text) <= 50 for chunk in chunks)
    for first, second in zip(chunks, chunks[1:]):
        assert first.text[-5:] == second.text[:5]
