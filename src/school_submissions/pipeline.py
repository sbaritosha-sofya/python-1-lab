from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from .features import FeatureSet, build_features
from .models import Assignment, Submission


@dataclass
class FeatureStream:
    source: Iterable[Submission]
    assignment: Assignment
    method: str
    seen: int = field(default=0, init=False)
    skipped_other_assignment: int = field(default=0, init=False)

    def __iter__(self) -> Iterator[FeatureSet]:
        for submission in self.source:
            self.seen += 1
            if submission.assignment_id != self.assignment.assignment_id:
                self.skipped_other_assignment += 1
                continue
            yield build_features(submission, self.assignment, self.method)


def iter_features(
    source: Iterable[Submission],
    assignment: Assignment,
    method: str,
) -> FeatureStream:
    return FeatureStream(source=source, assignment=assignment, method=method)


def collect_features(stream: Iterable[FeatureSet]) -> list[FeatureSet]:
    return list(stream)


def index_size_bytes(features: Iterable[FeatureSet]) -> int:
    return sum(feature.approximate_size_bytes() for feature in features)
