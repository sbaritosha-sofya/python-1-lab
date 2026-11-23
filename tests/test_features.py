from __future__ import annotations

from datetime import datetime, timezone

from school_submissions.comparison import compare_features
from school_submissions.features import (
    AST_METHOD,
    TOKEN_METHOD,
    build_ast_features,
    build_token_features,
)
from school_submissions.models import Assignment, Submission


def make_submission(
    code: str,
    *,
    submission_id: str = "sub-1",
    assignment_id: str = "lab-1",
    student_id: str = "student-a",
) -> Submission:
    return Submission(
        submission_id=submission_id,
        assignment_id=assignment_id,
        student_id=student_id,
        text="text",
        code=code,
        used_ai=False,
        timestamp=datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc),
    )


def make_assignment(templates: tuple[str, ...] = ()) -> Assignment:
    return Assignment(
        assignment_id="lab-1",
        name="Test",
        allowed_templates=templates,
    )


def test_formatting_and_comments_do_not_change_token_similarity() -> None:
    a = make_submission("def solve(items):\n    return sorted(items)\n", submission_id="a", student_id="a")
    b = make_submission(
        "def solve( items ):\n\n    # different comment\n    return sorted( items )\n",
        submission_id="b",
        student_id="b",
    )
    assignment = make_assignment()
    left = build_token_features(a, assignment)
    right = build_token_features(b, assignment)

    result = compare_features(left, right)

    assert result.status == "ok"
    assert result.score == 1.0
    assert result.shared_units == result.union_units


def test_renaming_keeps_token_similarity_low_but_ast_equal() -> None:
    original = (
        "def solve(items):\n"
        "    total = 0\n"
        "    for item in items:\n"
        "        total += item\n"
        "    return total\n"
    )
    renamed = (
        "def solve(values):\n"
        "    acc = 0\n"
        "    for value in values:\n"
        "        acc += value\n"
        "    return acc\n"
    )
    assignment = make_assignment()
    left = make_submission(original, submission_id="a", student_id="a")
    right = make_submission(renamed, submission_id="b", student_id="b")

    token_result = compare_features(
        build_token_features(left, assignment),
        build_token_features(right, assignment),
    )
    ast_result = compare_features(
        build_ast_features(left, assignment),
        build_ast_features(right, assignment),
    )

    assert token_result.score is not None
    assert token_result.score < 1.0
    assert ast_result.structure_equal is True
    assert ast_result.score == 1.0


def test_template_lines_are_marked_and_matching_template_is_explained() -> None:
    template = "def solve(items):\n    return sorted(items)\n"
    assignment = make_assignment(("def solve(items):", "return sorted(items)"))
    left = build_token_features(make_submission(template, submission_id="a", student_id="a"), assignment)
    right = build_token_features(make_submission(template, submission_id="b", student_id="b"), assignment)

    result = compare_features(left, right)

    assert left.template_lines == frozenset({1, 2})
    assert result.score == 1.0
    assert result.template_only is True
    assert result.status == "template_only"
    assert result.reason is not None


def test_empty_code_returns_insufficient_data() -> None:
    assignment = make_assignment()
    left = build_token_features(make_submission("x\n", submission_id="a", student_id="a"), assignment)
    right = build_token_features(make_submission("", submission_id="b", student_id="b"), assignment)

    result = compare_features(left, right)

    assert left.status == "insufficient"
    assert result.status == "insufficient_data"
    assert result.score is None


def test_syntax_error_is_reported_without_crash() -> None:
    assignment = make_assignment()
    broken = make_submission("def solve(:\n    return 1\n", submission_id="a", student_id="a")

    token_features = build_token_features(broken, assignment)
    ast_features = build_ast_features(broken, assignment)

    assert token_features.status == "syntax_error"
    assert token_features.message
    assert ast_features.status == "syntax_error"
    assert ast_features.message


def test_evidence_points_to_existing_lines() -> None:
    code = (
        "def solve(items):\n"
        "    total = 0\n"
        "    for item in items:\n"
        "        total += item\n"
        "    return total\n"
    )
    assignment = make_assignment()
    left = build_token_features(make_submission(code, submission_id="a", student_id="a"), assignment)
    right = build_ast_features(make_submission(code, submission_id="b", student_id="b"), assignment)

    token_result = compare_features(
        left,
        build_token_features(make_submission(code, submission_id="b", student_id="b"), assignment),
    )
    ast_result = compare_features(
        build_ast_features(make_submission(code, submission_id="a", student_id="a"), assignment),
        right,
    )

    for result in (token_result, ast_result):
        assert result.evidence
        for item in result.evidence:
            assert item.left.is_within(5)
            assert item.right.is_within(5)


def test_methods_are_not_mixed() -> None:
    assignment = make_assignment()
    token = build_token_features(make_submission("print(1 + 2)\n", submission_id="a", student_id="a"), assignment)
    ast_features = build_ast_features(make_submission("print(1 + 2)\n", submission_id="b", student_id="b"), assignment)

    try:
        compare_features(token, ast_features)
    except ValueError as exc:
        assert "different methods" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

    assert token.method == TOKEN_METHOD
    assert ast_features.method == AST_METHOD
