from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator, Protocol, Self

from .models import Submission
from .parser import parse_submission


class Source(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: object) -> None: ...

    def __iter__(self) -> Iterator[Submission]: ...


class InMemorySource:
    def __init__(self, submissions: Iterable[Submission] | None = None) -> None:
        self._submissions: list[Submission] = list(submissions) if submissions is not None else []

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: object) -> None:
        return None

    def __iter__(self) -> Iterator[Submission]:
        return iter(self._submissions)

    def add(self, submission: Submission) -> None:
        self._submissions.append(submission)


class JSONLSource:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._fp: object | None = None

    def __enter__(self) -> Self:
        self._fp = open(self.path, "r", encoding="utf-8")
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: object) -> None:
        self.close()

    def close(self) -> None:
        if self._fp is not None:
            fp = self._fp
            self._fp = None
            if hasattr(fp, "close"):
                fp.close()

    @property
    def closed(self) -> bool:
        return self._fp is None or getattr(self._fp, "closed", False)

    def __iter__(self) -> Iterator[Submission]:
        if self._fp is None:
            raise RuntimeError("JSONLSource must be opened with 'with' statement")
        for line_no, line in enumerate(self._fp, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                yield parse_submission(raw)
            except Exception:
                continue
