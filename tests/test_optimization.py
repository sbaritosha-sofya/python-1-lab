from __future__ import annotations

import pytest

from school_submissions.comparison import compare_features
from school_submissions.evaluation import build_index, load_corpus, score_pairs
from school_submissions.features import AST_METHOD, TOKEN_METHOD, FeatureSet, LineRange


def _span_is_template(span: LineRange, template_lines: frozenset[int]) -> bool:
    if not template_lines:
        return False
    return all(line in template_lines for line in range(span.start, span.end + 1))


def _unit_is_template(feature: FeatureSet, unit: tuple[str, ...]) -> bool:
    spans = feature.spans.get(unit, ())
    return bool(spans) and all(
        _span_is_template(span, feature.template_lines) for span in spans
    )


def brute_force(left: FeatureSet, right: FeatureSet) -> tuple[float, int, int, bool]:
    shared = left.units & right.units
    union = left.units | right.units
    template_shared = {
        unit
        for unit in shared
        if _unit_is_template(left, unit) and _unit_is_template(right, unit)
    }
    score = len(shared) / len(union)
    return score, len(shared), len(union), bool(shared) and template_shared == shared


@pytest.mark.parametrize("method", [TOKEN_METHOD, AST_METHOD])
def test_optimized_score_matches_brute_force(method: str) -> None:
    corpus = load_corpus("data/corpus")
    index = build_index(corpus, method)

    for pair in corpus.pairs:
        left = index[pair["left_submission_id"]]
        right = index[pair["right_submission_id"]]
        expected_score, expected_shared, expected_union, expected_template_only = brute_force(
            left, right
        )

        result = compare_features(left, right, max_evidence=3)

        assert result.score == pytest.approx(expected_score)
        assert result.shared_units == expected_shared
        assert result.union_units == expected_union
        assert result.template_only is expected_template_only


@pytest.mark.parametrize("method", [TOKEN_METHOD, AST_METHOD])
def test_similarity_is_symmetric_and_in_range(method: str) -> None:
    corpus = load_corpus("data/corpus")
    index = build_index(corpus, method)

    for pair in corpus.pairs:
        left = index[pair["left_submission_id"]]
        right = index[pair["right_submission_id"]]

        forward = compare_features(left, right)
        backward = compare_features(right, left)

        assert forward.score is not None
        assert 0.0 <= forward.score <= 1.0
        assert forward.score == pytest.approx(backward.score)
        assert forward.shared_units == backward.shared_units
        assert forward.union_units == backward.union_units


def test_template_units_are_precomputed_for_template_pairs() -> None:
    corpus = load_corpus("data/corpus")
    index = build_index(corpus, TOKEN_METHOD)

    for pair in corpus.pairs:
        if not pair.get("template_only"):
            continue
        left = index[pair["left_submission_id"]]
        right = index[pair["right_submission_id"]]
        assert left.template_units == left.units
        assert right.template_units == right.units


def test_evaluation_scores_use_optimized_comparison() -> None:
    corpus = load_corpus("data/corpus")
    index = build_index(corpus, TOKEN_METHOD)
    scored = score_pairs(corpus, index)
    by_pair = {item.pair_id: item for item in scored}

    for pair in corpus.pairs:
        result = by_pair[pair["pair_id"]].comparison
        left = index[pair["left_submission_id"]]
        right = index[pair["right_submission_id"]]
        expected = compare_features(left, right)
        assert result.score == expected.score
