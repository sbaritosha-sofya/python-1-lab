from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .exceptions import SubmissionValidationError
from .models import Submission
from .parser import parse_submission
from .repository import InMemorySubmissionRepository, SubmissionRepository


@dataclass(frozen=True, slots=True)
class AcceptResult:
    status: str  # accepted | duplicate | conflict | error
    submission: Submission | None = None
    attempted: Submission | None = None
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "submission": self.submission.to_dict() if self.submission else None,
            "attempted": self.attempted.to_dict() if self.attempted else None,
            "error": self.error,
        }


@dataclass
class SubmissionService:
    """Доменный сервис приёма сдач.

    Не зависит от HTTP/CLI и работает только с доменными моделями.
    """

    repository: SubmissionRepository = field(default_factory=InMemorySubmissionRepository)

    def accept(self, raw: Any) -> AcceptResult:
        """Распарсить и сохранить сдачу.

        При повторном submission_id и совпадении хеша возвращает duplicate.
        При совпадении идентификатора с другим содержимым -- conflict.
        """
        try:
            submission = parse_submission(raw)
        except SubmissionValidationError as exc:
            return AcceptResult(
                status="error",
                error={
                    "code": exc.code,
                    "field": exc.field,
                    "message": exc.message,
                },
            )

        status, stored = self.repository.save(submission)
        if status == "conflict":
            return AcceptResult(status="conflict", submission=stored, attempted=submission)
        if status == "duplicate":
            return AcceptResult(status="duplicate", submission=stored)
        return AcceptResult(status="accepted", submission=submission)
