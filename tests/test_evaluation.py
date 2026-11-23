from __future__ import annotations

from dataclasses import replace

import pytest

from school_submissions.evaluation import (
    analyze_errors,
    build_index,
    evaluate_corpus,
    load_corpus,
    render_markdown,
    score_pairs,
    select_threshold,
    validate_corpus,
)
from school_submissions.features import AST_METHOD, TOKEN_METHOD


def test_corpus_loads_and_has_no_leakage() -> None:
    corpus = load_corpus("data/corpus")

    assert len(corpus.submissions) >= 30
    assert len(corpus.pairs) >= 40
    assert {origin["split"] for origin in corpus.origins.values()} == {"setup", "eval"}


def test_cross_split_pair_is_rejected() -> None:
    corpus = load_corpus("data/corpus")
    bad_pair = {
        "pair_id": "bad-pair",
        "left_submission_id": "s01",
        "right_submission_id": "s06",
        "assignment_id": "lab-sort",
        "family_id": "bad",
        "derivation_relation": "exact_copy",
        "template_only": False,
    }
    broken = replace(corpus, pairs=corpus.pairs + (bad_pair,))

    with pytest.raises(ValueError, match="crosses setup/eval"):
        validate_corpus(broken)


def test_threshold_selection_and_evaluation_on_both_methods() -> None:
    report = evaluate_corpus(
        "data/corpus",
        methods=[TOKEN_METHOD, AST_METHOD],
        threshold_step=0.01,
    )

    assert report["corpus"]["validation"] == "ok"
    assert set(report["methods"]) == {TOKEN_METHOD, AST_METHOD}
    assert report["method_agreement"]["pairs"] == report["methods"][TOKEN_METHOD]["eval"]["total"]

    for method, result in report["methods"].items():
        assert 0.0 <= result["threshold"] <= 1.0
        eval_metrics = result["eval"]
        assert eval_metrics["tp"] + eval_metrics["fp"] + eval_metrics["tn"] + eval_metrics["fn"] == eval_metrics["total"]
        assert eval_metrics["uncertain_share"] == 0.0
        assert result["template_slice"]["pairs"] == 10
        assert result["template_slice"]["flagged"] == 10
        assert result["template_slice"]["explained_as_template"] == 10
        assert result["statuses"].get("template_only") == 10
        assert result["eval_without_template"]["total"] == eval_metrics["total"] - 10


def test_ast_catches_renamed_copies_that_token_method_misses() -> None:
    report = evaluate_corpus(
        "data/corpus",
        methods=[TOKEN_METHOD, AST_METHOD],
        threshold_step=0.01,
    )

    token = report["methods"][TOKEN_METHOD]["eval"]
    ast = report["methods"][AST_METHOD]["eval"]

    assert ast["recall"] >= token["recall"]
    assert ast["f1"] >= token["f1"]
    assert report["method_agreement"]["second_only"] > 0


def test_errors_include_template_and_at_least_three_cases() -> None:
    report = evaluate_corpus(
        "data/corpus",
        methods=[TOKEN_METHOD, AST_METHOD],
        threshold_step=0.01,
    )

    errors = report["errors"]
    assert len(errors) >= 3
    assert any(error["template_only"] for error in errors)
    assert all(error["explanation"] for error in errors)
    assert all(error["evidence"] for error in errors)


def test_select_threshold_is_deterministic() -> None:
    corpus = load_corpus("data/corpus")
    index = build_index(corpus, TOKEN_METHOD)
    scored = score_pairs(corpus, index)
    setup = [item for item in scored if item.split == "setup"]

    first = select_threshold(setup, step=0.05)
    second = select_threshold(setup, step=0.05)

    assert first == second
    assert first["threshold"] in {0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0}


def test_error_analysis_can_be_called_directly() -> None:
    corpus = load_corpus("data/corpus")
    index = build_index(corpus, AST_METHOD)
    scored = score_pairs(corpus, index)
    eval_items = [item for item in scored if item.split == "eval"]
    threshold = 0.65

    errors = analyze_errors({AST_METHOD: eval_items}, {AST_METHOD: threshold})

    assert errors
    assert all(error["method"] == AST_METHOD for error in errors)


def test_markdown_contains_methods_and_error_section() -> None:
    report = evaluate_corpus(
        "data/corpus",
        methods=[TOKEN_METHOD, AST_METHOD],
        threshold_step=0.05,
    )

    markdown = render_markdown(report)

    assert "# Результаты оценки сходства" in markdown
    assert TOKEN_METHOD in markdown
    assert AST_METHOD in markdown
    assert "## Разбор ошибок" in markdown
    assert "template_only" in markdown
