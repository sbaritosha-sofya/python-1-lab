from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .features import FeatureSet, LineRange, Unit

DEFAULT_MAX_EVIDENCE = 10


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    unit: Unit
    left: LineRange
    right: LineRange
    template_only: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit": list(self.unit),
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "template_only": self.template_only,
        }


@dataclass(frozen=True, slots=True)
class PairSimilarity:
    left_id: str
    right_id: str
    left_student: str
    right_student: str
    assignment_id: str
    method: str
    method_version: str
    status: str
    reason: str | None
    score: float | None
    shared_units: int
    union_units: int
    shared_template_units: int
    template_only: bool
    structure_equal: bool | None
    evidence: tuple[EvidenceItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "left": {
                "submission_id": self.left_id,
                "student_id": self.left_student,
            },
            "right": {
                "submission_id": self.right_id,
                "student_id": self.right_student,
            },
            "assignment_id": self.assignment_id,
            "method": self.method,
            "method_version": self.method_version,
            "status": self.status,
            "reason": self.reason,
            "score": self.score,
            "shared_units": self.shared_units,
            "union_units": self.union_units,
            "shared_template_units": self.shared_template_units,
            "template_only": self.template_only,
            "structure_equal": self.structure_equal,
            "evidence": [item.to_dict() for item in self.evidence],
        }


def _span_is_template(span: LineRange, template_lines: frozenset[int]) -> bool:
    if not template_lines:
        return False
    return all(line in template_lines for line in range(span.start, span.end + 1))


def _unit_is_template(feature: FeatureSet, unit: Unit) -> bool:
    ranges = feature.spans.get(unit, ())
    if not ranges:
        return False
    return all(_span_is_template(span, feature.template_lines) for span in ranges)


def _empty_result(
    left: FeatureSet,
    right: FeatureSet,
    status: str,
    reason: str | None,
) -> PairSimilarity:
    return PairSimilarity(
        left_id=left.submission_id,
        right_id=right.submission_id,
        left_student=left.student_id,
        right_student=right.student_id,
        assignment_id=left.assignment_id,
        method=left.method,
        method_version=left.method_version,
        status=status,
        reason=reason,
        score=None,
        shared_units=0,
        union_units=0,
        shared_template_units=0,
        template_only=False,
        structure_equal=None,
        evidence=(),
    )


def compare_features(
    left: FeatureSet,
    right: FeatureSet,
    max_evidence: int = DEFAULT_MAX_EVIDENCE,
    allow_same_student: bool = False,
) -> PairSimilarity:
    if left.method != right.method:
        raise ValueError(
            f"Cannot compare different methods: {left.method} and {right.method}"
        )
    if left.submission_id == right.submission_id:
        return _empty_result(left, right, "self_match", "same submission")
    if left.assignment_id != right.assignment_id:
        return _empty_result(left, right, "different_assignment", "assignment mismatch")
    if not allow_same_student and left.student_id == right.student_id:
        return _empty_result(left, right, "same_student_revision", "same student")
    if left.status == "syntax_error" or right.status == "syntax_error":
        return _empty_result(left, right, "syntax_error", "source could not be parsed")

    shared = left.units & right.units
    union = left.units | right.units
    if not union:
        return _empty_result(left, right, "insufficient_data", "empty unit union")

    template_shared = {unit for unit in shared if _unit_is_template(left, unit) and _unit_is_template(right, unit)}
    template_only = bool(shared) and template_shared == shared
    score = len(shared) / len(union)

    evidence: list[EvidenceItem] = []
    for unit in sorted(shared):
        if len(evidence) >= max_evidence:
            break
        left_spans = left.spans.get(unit, ())
        right_spans = right.spans.get(unit, ())
        if not left_spans or not right_spans:
            continue
        left_span = left_spans[0]
        right_span = right_spans[0]
        if not left_span.is_within(left.line_count) or not right_span.is_within(right.line_count):
            continue
        evidence.append(
            EvidenceItem(
                unit=unit,
                left=left_span,
                right=right_span,
                template_only=unit in template_shared,
            )
        )

    structure_equal: bool | None = None
    if left.structure_hash is not None and right.structure_hash is not None:
        structure_equal = left.structure_hash == right.structure_hash

    return PairSimilarity(
        left_id=left.submission_id,
        right_id=right.submission_id,
        left_student=left.student_id,
        right_student=right.student_id,
        assignment_id=left.assignment_id,
        method=left.method,
        method_version=left.method_version,
        status="template_only" if template_only else "ok",
        reason="all shared units belong to the allowed template" if template_only else None,
        score=score,
        shared_units=len(shared),
        union_units=len(union),
        shared_template_units=len(template_shared),
        template_only=template_only,
        structure_equal=structure_equal,
        evidence=tuple(evidence),
    )


def _candidate_allowed(
    target: FeatureSet,
    candidate: FeatureSet,
    include_same_student: bool,
) -> bool:
    if candidate.submission_id == target.submission_id:
        return False
    if candidate.assignment_id != target.assignment_id:
        return False
    if not include_same_student and candidate.student_id == target.student_id:
        return False
    return True


def find_top_k(
    target: FeatureSet,
    candidates: Iterable[FeatureSet],
    k: int = 5,
    include_same_student: bool = False,
    max_evidence: int = DEFAULT_MAX_EVIDENCE,
) -> list[PairSimilarity]:
    if target.status != "ok":
        return []
    results: list[PairSimilarity] = []
    for candidate in candidates:
        if not _candidate_allowed(target, candidate, include_same_student):
            continue
        if candidate.status != "ok":
            continue
        comparison = compare_features(
            target,
            candidate,
            max_evidence=max_evidence,
            allow_same_student=include_same_student,
        )
        if comparison.score is None:
            continue
        results.append(comparison)
    results.sort(key=lambda item: (-(item.score or 0.0), item.right_id))
    return results[:k]


def find_same_student_revisions(
    target: FeatureSet,
    candidates: Iterable[FeatureSet],
    max_evidence: int = DEFAULT_MAX_EVIDENCE,
) -> list[PairSimilarity]:
    results: list[PairSimilarity] = []
    for candidate in candidates:
        if candidate.submission_id == target.submission_id:
            continue
        if candidate.assignment_id != target.assignment_id:
            continue
        if candidate.student_id != target.student_id:
            continue
        comparison = compare_features(
            target,
            candidate,
            max_evidence=max_evidence,
            allow_same_student=True,
        )
        if comparison.score is None:
            continue
        results.append(comparison)
    results.sort(key=lambda item: (-(item.score or 0.0), item.right_id))
    return results
