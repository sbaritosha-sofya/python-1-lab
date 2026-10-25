from __future__ import annotations

import json
from pathlib import Path

from school_submissions.models import Submission
from school_submissions.sources import InMemorySource, JSONLSource


def test_in_memory_source_iteration(sample_submission: Submission) -> None:
    source = InMemorySource([sample_submission])
    with source:
        items = list(source)
    assert items == [sample_submission]


def test_jsonl_source_reads_valid_rows(tmp_path: Path, sample_submission: Submission) -> None:
    data_file = tmp_path / "submissions.jsonl"
    data_file.write_text(
        json.dumps(sample_submission.to_dict(), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    with JSONLSource(data_file) as source:
        items = list(source)
    assert len(items) == 1
    assert items[0].submission_id == sample_submission.submission_id
    assert source.closed


def test_jsonl_source_skips_broken_lines(tmp_path: Path, sample_submission: Submission) -> None:
    data_file = tmp_path / "mixed.jsonl"
    data_file.write_text(
        json.dumps(sample_submission.to_dict(), ensure_ascii=False)
        + "\n"
        + "not a json line\n"
        + json.dumps({"invalid": "object"})
        + "\n",
        encoding="utf-8",
    )
    with JSONLSource(data_file) as source:
        items = list(source)
    assert len(items) == 1


def test_jsonl_source_closes_on_exception(tmp_path: Path, sample_submission: Submission) -> None:
    data_file = tmp_path / "submissions.jsonl"
    data_file.write_text(
        json.dumps(sample_submission.to_dict(), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    source = JSONLSource(data_file)
    try:
        with source:
            raise RuntimeError("abort")
    except RuntimeError:
        pass
    assert source.closed


def test_jsonl_source_early_break_closes_file(tmp_path: Path, sample_submission: Submission) -> None:
    data_file = tmp_path / "submissions.jsonl"
    data_file.write_text(
        json.dumps(sample_submission.to_dict(), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    with JSONLSource(data_file) as source:
        for _ in source:
            break
    assert source.closed
