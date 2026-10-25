from __future__ import annotations

from datetime import datetime
from typing import Any

from .exceptions import SubmissionValidationError
from .models import Submission

_REQUIRED_FIELDS = (
    "submission_id",
    "assignment_id",
    "student_id",
    "text",
    "code",
    "used_ai",
    "timestamp",
)
_STRING_FIELDS = ("submission_id", "assignment_id", "student_id", "text", "code")
_OPTIONAL_FIELDS = ("ai_declaration",)


def parse_submission(raw: Any) -> Submission:
    """Преобразовать сырой словарь в :class:`Submission`.

    Входной объект не изменяется. При любой ошибке выбрасывается
    :class:`SubmissionValidationError` с кодом ``format`` или ``schema``.
    """
    if not isinstance(raw, dict):
        raise SubmissionValidationError(
            code="schema",
            field="<root>",
            message="Submission must be a JSON object",
        )

    keys = set(raw.keys())
    allowed = set(_REQUIRED_FIELDS) | set(_OPTIONAL_FIELDS)
    unknown = keys - allowed
    if unknown:
        name = sorted(unknown)[0]
        raise SubmissionValidationError(
            code="schema",
            field=name,
            message=f"Unknown field: {name}",
        )

    missing = [field for field in _REQUIRED_FIELDS if field not in raw]
    if missing:
        field = missing[0]
        raise SubmissionValidationError(
            code="schema",
            field=field,
            message=f"Missing required field: {field}",
        )

    for field in _STRING_FIELDS:
        value = raw[field]
        if not isinstance(value, str):
            raise SubmissionValidationError(
                code="schema",
                field=field,
                message=f"{field} must be a string",
            )

    used_ai = raw["used_ai"]
    if not isinstance(used_ai, bool):
        raise SubmissionValidationError(
            code="schema",
            field="used_ai",
            message="used_ai must be a boolean",
        )

    ai_declaration = raw.get("ai_declaration", "")
    if not isinstance(ai_declaration, str):
        raise SubmissionValidationError(
            code="schema",
            field="ai_declaration",
            message="ai_declaration must be a string",
        )
    if used_ai and not ai_declaration.strip():
        raise SubmissionValidationError(
            code="schema",
            field="ai_declaration",
            message="AI declaration is required when used_ai=true",
        )

    student_id = raw["student_id"].strip()
    if not student_id:
        raise SubmissionValidationError(
            code="schema",
            field="student_id",
            message="student_id must be non-empty",
        )

    ts_value = raw["timestamp"]
    if not isinstance(ts_value, str):
        raise SubmissionValidationError(
            code="schema",
            field="timestamp",
            message="timestamp must be a string",
        )
    try:
        timestamp = datetime.fromisoformat(ts_value)
    except Exception as exc:
        raise SubmissionValidationError(
            code="schema",
            field="timestamp",
            message=f"Invalid ISO 8601 timestamp: {exc}",
        ) from exc
    if timestamp.tzinfo is None:
        raise SubmissionValidationError(
            code="schema",
            field="timestamp",
            message="timestamp must include timezone information",
        )

    return Submission(
        submission_id=raw["submission_id"],
        assignment_id=raw["assignment_id"],
        student_id=student_id,
        text=raw["text"],
        code=raw["code"],
        used_ai=used_ai,
        timestamp=timestamp,
        ai_declaration=ai_declaration,
    )
