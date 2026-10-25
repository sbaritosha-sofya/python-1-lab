from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol

from .models import Submission


class SubmissionRepository(Protocol):
    """Контракт репозитория сдач."""

    def get(self, submission_id: str) -> Submission | None: ...

    def save(
        self, submission: Submission
    ) -> tuple[str, Submission]:
        """Сохранить сдачу.

        Возвращает пару (status, submission), где status -- accepted,
        duplicate или conflict.
        """
        ...

    def list(self) -> Iterable[Submission]: ...


@dataclass
class InMemorySubmissionRepository:
    """In-memory реализация репозитория.

    Хранит кортеж (Submission, content_hash) для быстрой проверки дубликатов
    и конфликтов.
    """

    _store: dict[str, tuple[Submission, str]] = field(default_factory=dict)

    def get(self, submission_id: str) -> Submission | None:
        entry = self._store.get(submission_id)
        return entry[0] if entry else None

    def save(self, submission: Submission) -> tuple[str, Submission]:
        new_hash = submission.content_hash()
        existing = self._store.get(submission.submission_id)
        if existing:
            existing_submission, existing_hash = existing
            if new_hash == existing_hash:
                return "duplicate", existing_submission
            return "conflict", existing_submission
        self._store[submission.submission_id] = (submission, new_hash)
        return "accepted", submission

    def list(self) -> Iterable[Submission]:
        return (entry[0] for entry in self._store.values())

    def __contains__(self, submission_id: str) -> bool:
        return submission_id in self._store
