from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from school_submissions.features import TOKEN_METHOD
from school_submissions.models import Assignment, Submission
from school_submissions.pipeline import collect_features, index_size_bytes, iter_features
from school_submissions.sources import InMemorySource, JSONLSource


def make_submission(
    submission_id: str,
    *,
    assignment_id: str = "lab-1",
    student_id: str | None = None,
    code: str = "def solve(items):\n    return sorted(items)\n",
) -> Submission:
    return Submission(
        submission_id=submission_id,
        assignment_id=assignment_id,
        student_id=student_id or f"student-{submission_id}",
        text="text",
        code=code,
        used_ai=False,
        timestamp=datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_pipeline_is_lazy_and_skips_other_assignments() -> None:
    produced: list[str] = []
    submissions = [
        make_submission("s1"),
        make_submission("s2", assignment_id="lab-2"),
        make_submission("s3"),
    ]

    def source():
        for submission in submissions:
            produced.append(submission.submission_id)
            yield submission

    stream = iter_features(source(), Assignment(assignment_id="lab-1", name="Test"), TOKEN_METHOD)
    iterator = iter(stream)

    assert produced == []
    first = next(iterator)
    assert produced == ["s1"]
    assert first.submission_id == "s1"

    second = next(iterator)
    assert produced == ["s1", "s2", "s3"]
    assert second.submission_id == "s3"
    assert stream.seen == 3
    assert stream.skipped_other_assignment == 1


def test_pipeline_collects_features_and_estimates_index_size() -> None:
    source = InMemorySource([make_submission("s1"), make_submission("s2")])
    stream = iter_features(source, Assignment(assignment_id="lab-1", name="Test"), TOKEN_METHOD)

    with source:
        features = collect_features(stream)

    assert [feature.submission_id for feature in features] == ["s1", "s2"]
    assert all(feature.status == "ok" for feature in features)
    assert index_size_bytes(features) > 0


def test_jsonl_source_stays_streaming(tmp_path: Path) -> None:
    path = tmp_path / "submissions.jsonl"
    lines = []
    for index in range(5):
        submission = make_submission(f"s{index}")
        payload = submission.to_dict()
        payload.pop("content_hash")
        import json

        lines.append(json.dumps(payload))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    source = JSONLSource(path)
    stream = iter_features(source, Assignment(assignment_id="lab-1", name="Test"), TOKEN_METHOD)

    with source:
        iterator = iter(stream)
        first = next(iterator)

    assert first.submission_id == "s0"
    assert stream.seen == 1
    assert source.closed is True
