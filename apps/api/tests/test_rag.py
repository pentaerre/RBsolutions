from app.services.rag import EXCERPT_CHARS, build_messages


def test_build_messages_truncates_excerpts() -> None:
    long = "x" * 4000
    messages = build_messages("q", [{"filename": "well.txt", "chunk_index": 0, "text": long}])
    user = messages[1]["content"]
    assert long not in user
    assert ("x" * EXCERPT_CHARS) in user
    assert "well.txt" in user
