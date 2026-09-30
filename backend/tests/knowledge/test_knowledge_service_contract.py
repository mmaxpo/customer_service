from app.services.knowledge_ingest import chunk_text, _vector_to_pgvector_str
from app.services.workflow_runner import run_workflow


def test_chunk_text_is_stable_and_overlapping():
    text = "a" * 1000

    chunks = chunk_text(
        text,
        chunk_size=300,
        chunk_overlap=50,
    )

    assert len(chunks) > 1
    assert all(chunk for chunk in chunks)
    assert chunks[0][-50:] == chunks[1][:50]


def test_vector_to_pgvector_str():
    assert _vector_to_pgvector_str([0.1, 0.2]) == "[0.10000000,0.20000000]"


def test_deprecated_workflow_runner_fails_loudly():
    try:
        run_workflow()
    except RuntimeError as exc:
        assert "deprecated" in str(exc)
    else:
        raise AssertionError("Deprecated workflow runner should fail loudly")
