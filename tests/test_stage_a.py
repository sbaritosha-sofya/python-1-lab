from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from school_submissions.exceptions import SubmissionValidationError
from school_submissions.models import Submission
from school_submissions.parser import parse_submission
from school_submissions.repository import InMemorySubmissionRepository
from school_submissions.service import AcceptResult, SubmissionService


def test_parse_valid_submission() -> None:
    raw = {
        "submission_id": "sub-001",
        "assignment_id": "lab-1",
        "student_id": "student-a",
        "text": "Hello\nworld\n",
        "code": "print('hello')\n",
        "used_ai": False,
        "ai_declaration": "",
        "timestamp": "2026-10-11T12:00:00+03:00",
    }
    original = raw.copy()
    submission = parse_submission(raw)
    assert isinstance(submission, Submission)
    assert submission.submission_id == "sub-001"
    assert submission.timestamp.tzinfo is not None
    assert raw == original


def test_empty_student_id() -> None:
    raw = {
        "submission_id": "sub-001",
        "assignment_id": "lab-1",
        "student_id": "  ",
        "text": "Text\n",
        "code": "code\n",
        "used_ai": False,
        "ai_declaration": "",
        "timestamp": "2026-10-11T12:00:00+03:00",
    }
    with pytest.raises(SubmissionValidationError) as exc_info:
        parse_submission(raw)
    assert exc_info.value.code == "schema"
    assert exc_info.value.field == "student_id"


def test_timestamp_without_timezone() -> None:
    raw = {
        "submission_id": "sub-001",
        "assignment_id": "lab-1",
        "student_id": "x",
        "text": "Text\n",
        "code": "code\n",
        "used_ai": False,
        "ai_declaration": "",
        "timestamp": "2026-10-11T12:00:00",
    }
    with pytest.raises(SubmissionValidationError) as exc_info:
        parse_submission(raw)
    assert exc_info.value.code == "schema"
    assert exc_info.value.field == "timestamp"


def test_unknown_field() -> None:
    raw = {
        "submission_id": "sub-001",
        "assignment_id": "lab-1",
        "student_id": "x",
        "text": "Text\n",
        "code": "code\n",
        "used_ai": False,
        "ai_declaration": "",
        "timestamp": "2026-10-11T12:00:00+03:00",
        "extra_field": "surprise",
    }
    with pytest.raises(SubmissionValidationError) as exc_info:
        parse_submission(raw)
    assert exc_info.value.code == "schema"
    assert exc_info.value.field == "extra_field"


def test_used_ai_requires_declaration() -> None:
    raw = {
        "submission_id": "sub-001",
        "assignment_id": "lab-1",
        "student_id": "x",
        "text": "Text\n",
        "code": "code\n",
        "used_ai": True,
        "ai_declaration": "",
        "timestamp": "2026-10-11T12:00:00+03:00",
    }
    with pytest.raises(SubmissionValidationError) as exc_info:
        parse_submission(raw)
    assert exc_info.value.field == "ai_declaration"


def test_duplicate_does_not_increase_count(sample_submission: Submission) -> None:
    repo = InMemorySubmissionRepository()
    status1, _ = repo.save(sample_submission)
    status2, stored = repo.save(sample_submission)
    assert status1 == "accepted"
    assert status2 == "duplicate"
    assert len(list(repo.list())) == 1
    assert stored is sample_submission


def test_conflict_does_not_overwrite(sample_submission: Submission) -> None:
    repo = InMemorySubmissionRepository()
    repo.save(sample_submission)
    modified = Submission(
        submission_id=sample_submission.submission_id,
        assignment_id=sample_submission.assignment_id,
        student_id=sample_submission.student_id,
        text="Different\n",
        code=sample_submission.code,
        used_ai=sample_submission.used_ai,
        timestamp=sample_submission.timestamp,
        ai_declaration=sample_submission.ai_declaration,
    )
    status, stored = repo.save(modified)
    assert status == "conflict"
    assert stored is sample_submission
    assert stored.text != modified.text


def test_service_accept_and_conflict(sample_submission: Submission) -> None:
    service = SubmissionService()
    raw = sample_submission.to_dict()
    # content_hash вычисляется динамически, убираем его из сырого словаря.
    raw.pop("content_hash", None)
    result1 = service.accept(raw)
    assert result1.status == "accepted"
    result2 = service.accept(raw)
    assert result2.status == "duplicate"

    raw["text"] = "Changed\n"
    result3 = service.accept(raw)
    assert result3.status == "conflict"


def test_broken_json_line_does_not_stop_import(tmp_path: Path) -> None:
    data_file = tmp_path / "mixed.jsonl"
    data_file.write_text(
        json.dumps(
            {
                "submission_id": "sub-001",
                "assignment_id": "lab-1",
                "student_id": "a",
                "text": "Text\n",
                "code": "code\n",
                "used_ai": False,
                "ai_declaration": "",
                "timestamp": "2026-10-11T12:00:00+03:00",
            }
        )
        + "\n"
        + "this is not json\n"
        + json.dumps(
            {
                "submission_id": "sub-002",
                "assignment_id": "lab-1",
                "student_id": "b",
                "text": "Text\n",
                "code": "code\n",
                "used_ai": False,
                "ai_declaration": "",
                "timestamp": "2026-10-11T12:00:00+03:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    service = SubmissionService()
    accepted = 0
    errors = 0
    with open(data_file, "r", encoding="utf-8") as fp:
        for line_no, line in enumerate(fp, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                errors += 1
                continue
            result = service.accept(raw)
            if result.status == "accepted":
                accepted += 1
    assert accepted == 2
    assert errors == 1
