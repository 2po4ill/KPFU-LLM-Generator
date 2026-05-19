"""Unit tests for facet grounding scorer (hybrid jaccard + embedding)."""

from generation.generator_v3 import OptimizedContentGenerator


def test_sentence_is_grounded_hybrid_or_semantic():
    assert OptimizedContentGenerator._sentence_is_grounded(
        0.05, 0.60, jaccard_min=0.07, embedding_min=0.52, mode="hybrid"
    )
    assert not OptimizedContentGenerator._sentence_is_grounded(
        0.05, 0.40, jaccard_min=0.07, embedding_min=0.52, mode="hybrid"
    )


def test_sentence_is_grounded_jaccard_only():
    assert OptimizedContentGenerator._sentence_is_grounded(
        0.10, 0.90, jaccard_min=0.07, embedding_min=0.52, mode="jaccard"
    )
    assert not OptimizedContentGenerator._sentence_is_grounded(
        0.05, 0.90, jaccard_min=0.07, embedding_min=0.52, mode="jaccard"
    )


def test_skip_boilerplate_sentences():
    gen = OptimizedContentGenerator.__new__(OptimizedContentGenerator)
    assert gen._should_skip_grounding_sentence("Понимание каждой фазы позволяет организациям.")
    assert not gen._should_skip_grounding_sentence(
        "Уязвимость — дефект системы, который может быть использован для реализации угрозы."
    )
