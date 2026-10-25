from __future__ import annotations

import pytest

from school_submissions.analysis_service import AnalysisService
from school_submissions.analyzers import AnalyzerRegistry, LengthAnalyzer, TemplateAnalyzer
from school_submissions.models import Assignment, Submission


def test_default_registry_contains_both_analyzers() -> None:
    service = AnalysisService()
    assert service.registry.list() == ["length", "template"]


def test_analysis_service_selects_analyzer(
    sample_submission: Submission, sample_assignment: Assignment
) -> None:
    service = AnalysisService()
    report = service.analyze("length", sample_submission, sample_assignment)
    assert report.analyzer_id == "length"
    assert report.score is None


def test_analysis_service_runs_all_analyzers(
    sample_submission: Submission, sample_assignment: Assignment
) -> None:
    service = AnalysisService()
    reports = service.analyze_all(sample_submission, sample_assignment)
    assert set(reports.keys()) == {"length", "template"}
    assert reports["length"].score is None
    assert reports["template"].score == 0.0


def test_custom_analyzer_can_be_registered(
    sample_submission: Submission, sample_assignment: Assignment
) -> None:
    class ConstantAnalyzer:
        analyzer_id = "constant"
        analyzer_version = "0.1.0"

        def analyze(self, submission: Submission, context: object):
            from school_submissions.analyzers import AnalysisReport

            return AnalysisReport(
                analyzer_id=self.analyzer_id,
                analyzer_version=self.analyzer_version,
                submission_id=submission.submission_id,
                assignment_id=submission.assignment_id,
                score=0.5,
                feedback={"rubric_feedback": "constant"},
                evidence=[],
            )

    registry = AnalyzerRegistry()
    registry.register("constant", ConstantAnalyzer)
    service = AnalysisService(registry)
    report = service.analyze("constant", sample_submission, sample_assignment)
    assert report.analyzer_id == "constant"


def test_unknown_analyzer_raises(sample_submission: Submission, sample_assignment: Assignment) -> None:
    service = AnalysisService(AnalyzerRegistry())
    with pytest.raises(Exception):
        service.analyze("unknown", sample_submission, sample_assignment)


def test_analyzer_exception_propagates(
    sample_submission: Submission, sample_assignment: Assignment
) -> None:
    class FailingAnalyzer:
        analyzer_id = "failing"
        analyzer_version = "0.1.0"

        def analyze(self, submission: Submission, context: object) -> None:
            raise RuntimeError("analyzer failure")

    registry = AnalyzerRegistry()
    registry.register("failing", FailingAnalyzer)
    service = AnalysisService(registry)
    with pytest.raises(RuntimeError, match="analyzer failure"):
        service.analyze("failing", sample_submission, sample_assignment)
