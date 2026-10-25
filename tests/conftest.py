from __future__ import annotations

from datetime import datetime, timezone

import pytest

from school_submissions.models import Assignment, Submission


@pytest.fixture
def sample_submission() -> Submission:
    return Submission(
        submission_id="sub-001",
        assignment_id="lab-1",
        student_id="student-a",
        text="Hello\nworld\n",
        code="print('hello')\n",
        used_ai=False,
        timestamp=datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def ai_submission() -> Submission:
    return Submission(
        submission_id="sub-002",
        assignment_id="lab-1",
        student_id="student-b",
        text="Task solution\nSecond line\n",
        code="def solve():\n    return 42\n",
        used_ai=True,
        ai_declaration="Generated with AI assistant, verified manually.",
        timestamp=datetime(2026, 10, 11, 13, 30, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_assignment() -> Assignment:
    return Assignment(
        assignment_id="lab-1",
        name="Введение в Python",
        description="Первая лабораторная работа.",
        allowed_templates=("def solve():", "return 42"),
    )


@pytest.fixture
def empty_assignment() -> Assignment:
    return Assignment(
        assignment_id="lab-1",
        name="Empty assignment",
    )
