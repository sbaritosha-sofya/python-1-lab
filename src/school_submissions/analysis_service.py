from __future__ import annotations

from dataclasses import dataclass

from .analyzers import (
    AnalysisContext,
    AnalysisReport,
    Analyzer,
    AnalyzerRegistry,
    LengthAnalyzer,
    TemplateAnalyzer,
)
from .models import Assignment, Submission


@dataclass
class AnalysisService:
    registry: AnalyzerRegistry

    def __init__(self, registry: AnalyzerRegistry | None = None) -> None:
        self.registry = registry if registry is not None else AnalyzerRegistry()
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.registry.register("length", LengthAnalyzer)
        self.registry.register("template", TemplateAnalyzer)

    def analyze(
        self,
        analyzer_id: str,
        submission: Submission,
        assignment: Assignment,
    ) -> AnalysisReport:
        analyzer = self.registry.get(analyzer_id)
        context = AnalysisContext(assignment=assignment)
        return self._run_analyzer(analyzer, submission, context)

    def _run_analyzer(
        self,
        analyzer: Analyzer,
        submission: Submission,
        context: AnalysisContext,
    ) -> AnalysisReport:
        return analyzer.analyze(submission, context)

    def analyze_all(
        self,
        submission: Submission,
        assignment: Assignment,
    ) -> dict[str, AnalysisReport]:
        context = AnalysisContext(assignment=assignment)
        return {
            analyzer_id: self._run_analyzer(self.registry.get(analyzer_id), submission, context)
            for analyzer_id in self.registry.list()
        }
