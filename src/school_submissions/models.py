from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class Submission:
    """Версия сдачи лабораторной работы."""

    submission_id: str
    assignment_id: str
    student_id: str
    text: str
    code: str
    used_ai: bool
    timestamp: datetime
    ai_declaration: str = ""

    def content_hash(self) -> str:
        """SHA-256 по содержательным полям сдачи."""
        payload = {
            "assignment_id": self.assignment_id,
            "student_id": self.student_id,
            "text": self.text,
            "code": self.code,
            "used_ai": self.used_ai,
            "ai_declaration": self.ai_declaration,
            "timestamp": self.timestamp.isoformat(),
        }
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Сериализация для CLI."""
        return {
            "submission_id": self.submission_id,
            "assignment_id": self.assignment_id,
            "student_id": self.student_id,
            "text": self.text,
            "code": self.code,
            "used_ai": self.used_ai,
            "ai_declaration": self.ai_declaration,
            "timestamp": self.timestamp.isoformat(),
            "content_hash": self.content_hash(),
        }

