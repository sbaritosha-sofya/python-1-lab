from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .models import Assignment, Submission


@dataclass(frozen=True, slots=True)
class AnalysisReport:
    analyzer_id: str
    analyzer_version: str
    submission_id: str
    assignment_id: str
    score: float | None
    feedback: dict[str, Any]
    evidence: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "analyzer_id": self.analyzer_id,
            "analyzer_version": self.analyzer_version,
            "submission_id": self.submission_id,
            "assignment_id": self.assignment_id,
            "score": self.score,
            "feedback": self.feedback,
            "evidence": self.evidence,
        }


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    assignment: Assignment

    def source_data(self) -> dict[str, Any]:
        return self.assignment.to_dict()


class Analyzer(Protocol):
    analyzer_id: str
    analyzer_version: str

    def analyze(self, submission: Submission, context: AnalysisContext) -> AnalysisReport: ...


AnalyzerFactory = Callable[[], Analyzer]


@dataclass
class AnalyzerRegistry:
    _factories: dict[str, AnalyzerFactory] = field(default_factory=dict)

    def register(self, analyzer_id: str, factory: AnalyzerFactory) -> None:
        self._factories[analyzer_id] = factory

    def get(self, analyzer_id: str) -> Analyzer:
        factory = self._factories.get(analyzer_id)
        if factory is None:
            raise SubmissionAnalysisError(
                analyzer_id=analyzer_id,
                message=f"Analyzer '{analyzer_id}' is not registered",
            )
        return factory()

    def list(self) -> list[str]:
        return sorted(self._factories.keys())


class SubmissionAnalysisError(Exception):
    def __init__(self, analyzer_id: str, message: str) -> None:
        self.analyzer_id = analyzer_id
        self.message = message
        super().__init__(f"[{analyzer_id}] {message}")


class LengthAnalyzer:
    analyzer_id = "length"
    analyzer_version = "1.0.0"

    def analyze(self, submission: Submission, context: AnalysisContext) -> AnalysisReport:
        text_lines = [line for line in submission.text.splitlines() if line.strip()]
        code_lines = [line for line in submission.code.splitlines() if line.strip()]
        text_count = len(text_lines)
        code_count = len(code_lines)
        return AnalysisReport(
            analyzer_id=self.analyzer_id,
            analyzer_version=self.analyzer_version,
            submission_id=submission.submission_id,
            assignment_id=submission.assignment_id,
            score=None,
            feedback={
                "rubric_feedback": (
                    f"Text contains {text_count} non-empty line(s), "
                    f"code contains {code_count} non-empty line(s)."
                ),
                "text_non_empty_lines": text_count,
                "code_non_empty_lines": code_count,
            },
            evidence=[],
        )


class TemplateAnalyzer:
    analyzer_id = "template"
    analyzer_version = "1.0.0"

    def analyze(self, submission: Submission, context: AnalysisContext) -> AnalysisReport:
        allowed = context.assignment.allowed_templates
        evidence: list[dict[str, Any]] = []
        text_lines = submission.text.splitlines()
        code_lines = submission.code.splitlines()

        for pattern in allowed:
            for line_no, line in enumerate(text_lines, start=1):
                if pattern in line:
                    evidence.append(
                        {
                            "source": "text",
                            "line": line_no,
                            "matched": pattern,
                            "note": "Allowed template match",
                        }
                    )
            for line_no, line in enumerate(code_lines, start=1):
                if pattern in line:
                    evidence.append(
                        {
                            "source": "code",
                            "line": line_no,
                            "matched": pattern,
                            "note": "Allowed template match",
                        }
                    )

        matched_patterns = {entry["matched"] for entry in evidence}
        score = 1.0 if allowed and matched_patterns else 0.0
        unmatched = [pattern for pattern in allowed if pattern not in matched_patterns]

        return AnalysisReport(
            analyzer_id=self.analyzer_id,
            analyzer_version=self.analyzer_version,
            submission_id=submission.submission_id,
            assignment_id=submission.assignment_id,
            score=score,
            feedback={
                "rubric_feedback": (
                    "Template match is allowed. "
                    f"Matched {len(matched_patterns)} of {len(allowed)} pattern(s)."
                ),
                "matched_patterns": sorted(matched_patterns),
                "unmatched_patterns": sorted(unmatched),
            },
            evidence=evidence,
        )
