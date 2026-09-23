from app.services.text import chunk_text


def test_chunk_text_splits_long_input() -> None:
    text = " ".join(["word"] * 400)
    chunks = chunk_text(text, size=80, overlap=10)
    assert len(chunks) > 1
    assert all(chunk for chunk in chunks)


def test_chunk_text_empty() -> None:
    assert chunk_text("   ") == []
