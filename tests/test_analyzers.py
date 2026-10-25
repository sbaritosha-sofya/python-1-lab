from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from school_submissions.analyzers import (
    AnalysisContext,
    AnalysisReport,
    LengthAnalyzer,
    TemplateAnalyzer,
)
from school_submissions.models import Assignment, Submission
from school_submissions.sources import InMemorySource, JSONLSource


@pytest.fixture
def template_submission() -> Submission:
    return Submission(
        submission_id="sub-template",
        assignment_id="lab-1",
        student_id="student-c",
        text="Task solution\nSecond line\n",
        code="def solve():\n    return 42\n",
        used_ai=True,
        ai_declaration="AI used",
        timestamp=datetime(2026, 10, 11, 14, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def source_pair(tmp_path: Path, template_submission: Submission) -> tuple[InMemorySource, JSONLSource]:
    """Возвращает два источника с одинаковым содержимым."""
    data_file = tmp_path / "source.jsonl"
    data_file.write_text(
        json.dumps(template_submission.to_dict(), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return InMemorySource([template_submission]), JSONLSource(data_file)


def _contract_analyzer_on_submission(
    analyzer: LengthAnalyzer | TemplateAnalyzer,
    submission: Submission,
    assignment: Assignment,
) -> AnalysisReport:
    context = AnalysisContext(assignment=assignment)
    return analyzer.analyze(submission, context)


def _contract_analyzer_on_source(
    analyzer: LengthAnalyzer | TemplateAnalyzer,
    source: InMemorySource,
    assignment: Assignment,
) -> list[AnalysisReport]:
    context = AnalysisContext(assignment=assignment)
    reports = []
    with source:
        for submission in source:
            reports.append(analyzer.analyze(submission, context))
    return reports


class TestLengthAnalyzer:
    def test_returns_null_score(self, sample_submission: Submission, sample_assignment: Assignment) -> None:
        report = _contract_analyzer_on_submission(LengthAnalyzer(), sample_submission, sample_assignment)
        assert report.analyzer_id == "length"
        assert report.score is None
        assert "non-empty line(s)" in report.feedback["rubric_feedback"]

    def test_counts_non_empty_lines(self, sample_submission: Submission, sample_assignment: Assignment) -> None:
        report = _contract_analyzer_on_submission(LengthAnalyzer(), sample_submission, sample_assignment)
        assert report.feedback["text_non_empty_lines"] == 2
        assert report.feedback["code_non_empty_lines"] == 1

    def test_on_in_memory_source(self, sample_submission: Submission, sample_assignment: Assignment) -> None:
        source = InMemorySource([sample_submission])
        reports = _contract_analyzer_on_source(LengthAnalyzer(), source, sample_assignment)
        assert len(reports) == 1
        assert reports[0].analyzer_id == "length"


class TestTemplateAnalyzer:
    def test_finds_allowed_template(
        self, template_submission: Submission, sample_assignment: Assignment
    ) -> None:
        report = _contract_analyzer_on_submission(TemplateAnalyzer(), template_submission, sample_assignment)
        assert report.analyzer_id == "template"
        assert report.score == 1.0
        assert len(report.evidence) > 0
        text_evidence = [e for e in report.evidence if e["source"] == "text"]
        code_evidence = [e for e in report.evidence if e["source"] == "code"]
        assert any(e["line"] == 1 for e in code_evidence if e["matched"] == "def solve():")
        assert any(e["line"] == 2 for e in code_evidence if e["matched"] == "return 42")

    def test_evidence_line_numbers_are_one_based(
        self, template_submission: Submission, sample_assignment: Assignment
    ) -> None:
        report = _contract_analyzer_on_submission(TemplateAnalyzer(), template_submission, sample_assignment)
        for entry in report.evidence:
            assert entry["line"] >= 1

    def test_no_match_returns_zero_score(
        self, sample_submission: Submission, sample_assignment: Assignment
    ) -> None:
        report = _contract_analyzer_on_submission(TemplateAnalyzer(), sample_submission, sample_assignment)
        assert report.score == 0.0
        assert report.evidence == []

    def test_on_in_memory_source(
        self, template_submission: Submission, sample_assignment: Assignment
    ) -> None:
        source = InMemorySource([template_submission])
        reports = _contract_analyzer_on_source(TemplateAnalyzer(), source, sample_assignment)
        assert len(reports) == 1
        assert reports[0].analyzer_id == "template"


@pytest.mark.parametrize(
    "analyzer_factory,expected_id",
    [
        (LengthAnalyzer, "length"),
        (TemplateAnalyzer, "template"),
    ],
)
def test_contract_across_sources(
    source_pair: tuple[InMemorySource, JSONLSource],
    sample_assignment: Assignment,
    analyzer_factory: type[LengthAnalyzer] | type[TemplateAnalyzer],
    expected_id: str,
) -> None:
    """Один контрактный тест для обоих источников и обоих анализаторов."""
    in_memory, jsonl = source_pair
    for source in (in_memory, jsonl):
        with source:
            reports = [
                analyzer_factory().analyze(submission, AnalysisContext(assignment=sample_assignment))
                for submission in source
            ]
        assert len(reports) == 1
        assert reports[0].analyzer_id == expected_id
        assert reports[0].submission_id == "sub-template"


class TestAnalyzerDoesNotMutateInput:
    def test_length_analyzer_keeps_submission_unchanged(
        self, sample_submission: Submission, sample_assignment: Assignment
    ) -> None:
        original = sample_submission.to_dict()
        analyzer = LengthAnalyzer()
        analyzer.analyze(sample_submission, AnalysisContext(assignment=sample_assignment))
        assert sample_submission.to_dict() == original

    def test_template_analyzer_keeps_submission_unchanged(
        self, template_submission: Submission, sample_assignment: Assignment
    ) -> None:
        original = template_submission.to_dict()
        analyzer = TemplateAnalyzer()
        analyzer.analyze(template_submission, AnalysisContext(assignment=sample_assignment))
        assert template_submission.to_dict() == original
