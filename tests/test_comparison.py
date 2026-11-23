from __future__ import annotations

from datetime import datetime, timezone

from school_submissions.comparison import (
    compare_features,
    find_same_student_revisions,
    find_top_k,
)
from school_submissions.features import TOKEN_METHOD, build_token_features
from school_submissions.models import Assignment, Submission


def make_submission(
    code: str,
    *,
    submission_id: str,
    assignment_id: str = "lab-1",
    student_id: str,
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


def make_assignment(assignment_id: str = "lab-1") -> Assignment:
    return Assignment(assignment_id=assignment_id, name="Test")


COPY = "def solve(items):\n    return sorted(items)\n"
OTHER = "def solve(values):\n    result = []\n    for value in values:\n        result.append(value * 2)\n    return result\n"


def features_for(code: str, submission_id: str, student_id: str, assignment_id: str = "lab-1"):
    assignment = make_assignment(assignment_id)
    submission = make_submission(
        code,
        submission_id=submission_id,
        student_id=student_id,
        assignment_id=assignment_id,
    )
    assert assignment.assignment_id == submission.assignment_id
    return build_token_features(submission, assignment)


def test_exact_copy_has_maximum_similarity() -> None:
    left = features_for(COPY, "a", "student-a")
    right = features_for(COPY, "b", "student-b")

    result = compare_features(left, right)

    assert result.status == "ok"
    assert result.score == 1.0
    assert result.shared_units > 0
    assert result.method == TOKEN_METHOD


def test_self_match_is_not_compared() -> None:
    left = features_for(COPY, "a", "student-a")

    result = compare_features(left, left)

    assert result.status == "self_match"
    assert result.score is None


def test_different_assignment_is_rejected() -> None:
    left = features_for(COPY, "a", "student-a", "lab-1")
    right = features_for(COPY, "b", "student-b", "lab-2")

    result = compare_features(left, right)

    assert result.status == "different_assignment"
    assert result.score is None


def test_same_student_revision_is_separate() -> None:
    left = features_for(COPY, "a1", "student-a")
    right = features_for(COPY, "a2", "student-a")

    result = compare_features(left, right)

    assert result.status == "same_student_revision"
    assert result.score is None


def test_top_k_excludes_self_other_assignment_and_same_student() -> None:
    target = features_for(COPY, "a1", "student-a")
    candidates = [
        target,
        features_for(COPY, "b1", "student-b"),
        features_for(OTHER, "c1", "student-c"),
        features_for(COPY, "a2", "student-a"),
        features_for(COPY, "d1", "student-d", "lab-2"),
    ]

    top = find_top_k(target, candidates, k=5)
    revisions = find_same_student_revisions(target, candidates)

    ids = {item.right_id for item in top}
    assert ids == {"b1", "c1"}
    assert "a1" not in ids
    assert "a2" not in ids
    assert "d1" not in ids
    assert top[0].right_id == "b1"
    assert top[0].score == 1.0
    assert [item.right_id for item in revisions] == ["a2"]


def test_top_k_respects_k() -> None:
    target = features_for(COPY, "a1", "student-a")
    candidates = [
        features_for(COPY, f"b{index}", f"student-b{index}") for index in range(10)
    ]

    top = find_top_k(target, candidates, k=3)

    assert len(top) == 3


def test_empty_features_are_skipped_in_top_k() -> None:
    target = features_for(COPY, "a1", "student-a")
    empty = features_for("x\n", "b1", "student-b")

    assert find_top_k(target, [empty], k=5) == []
