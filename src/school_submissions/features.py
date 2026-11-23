from __future__ import annotations

import ast
import hashlib
import io
import tokenize as py_tokenize
from dataclasses import dataclass
from typing import Any, Iterable, Iterator

from .models import Assignment, Submission

TOKEN_METHOD = "token-3gram"
AST_METHOD = "ast-normalized"
FEATURE_VERSION = "1.0.0"

NGRAM_SIZE = 3
_SPAN_OCCURRENCE_LIMIT = 3

_SERVICE_TOKEN_TYPES = frozenset(
    {
        py_tokenize.ENCODING,
        py_tokenize.NL,
        py_tokenize.NEWLINE,
        py_tokenize.INDENT,
        py_tokenize.DEDENT,
        py_tokenize.ENDMARKER,
        py_tokenize.COMMENT,
    }
)


@dataclass(frozen=True, slots=True)
class LineRange:
    start: int
    end: int

    def to_dict(self) -> dict[str, int]:
        return {"line_start": self.start, "line_end": self.end}

    def is_within(self, line_count: int) -> bool:
        return 1 <= self.start <= self.end <= line_count


Unit = tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FeatureSet:
    method: str
    method_version: str
    submission_id: str
    assignment_id: str
    student_id: str
    status: str
    message: str | None
    line_count: int
    unit_count: int
    units: frozenset[Unit]
    spans: dict[Unit, tuple[LineRange, ...]]
    template_lines: frozenset[int]
    structure_hash: str | None = None

    def approximate_size_bytes(self) -> int:
        text = sum(len("".join(unit)) for unit in self.units)
        spans = sum(16 * len(ranges) for ranges in self.spans.values())
        return text + spans + 256

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "method_version": self.method_version,
            "submission_id": self.submission_id,
            "assignment_id": self.assignment_id,
            "student_id": self.student_id,
            "status": self.status,
            "message": self.message,
            "line_count": self.line_count,
            "unit_count": self.unit_count,
            "unit_set_size": len(self.units),
            "template_lines": sorted(self.template_lines),
            "structure_hash": self.structure_hash,
            "approximate_size_bytes": self.approximate_size_bytes(),
        }


def _format_token_error(exc: BaseException) -> str:
    if isinstance(exc, py_tokenize.TokenError):
        message, position = exc.args
        line = position[0] if isinstance(position, tuple) and position else "?"
        return f"{message} (line {line})"
    if isinstance(exc, SyntaxError):
        line = exc.lineno if exc.lineno is not None else "?"
        return f"{exc.msg} (line {line})"
    return str(exc)


def _template_lines(code: str, assignment: Assignment) -> frozenset[int]:
    patterns = [pattern for pattern in assignment.allowed_templates if pattern]
    if not patterns:
        return frozenset()
    matched: set[int] = set()
    for line_no, line in enumerate(code.splitlines(), start=1):
        stripped = line.strip()
        if any(pattern.strip() == stripped or pattern in line for pattern in patterns):
            matched.add(line_no)
    return frozenset(matched)


def _build_units(
    events: Iterable[tuple[str, int, int]],
    size: int = NGRAM_SIZE,
) -> tuple[frozenset[Unit], dict[Unit, tuple[LineRange, ...]]]:
    materialized = list(events)
    collected: dict[Unit, list[LineRange]] = {}
    for index in range(len(materialized) - size + 1):
        window = materialized[index : index + size]
        unit = tuple(event[0] for event in window)
        span = LineRange(
            start=min(event[1] for event in window),
            end=max(event[2] for event in window),
        )
        ranges = collected.setdefault(unit, [])
        if len(ranges) < _SPAN_OCCURRENCE_LIMIT:
            ranges.append(span)
    spans = {unit: tuple(ranges) for unit, ranges in collected.items()}
    return frozenset(spans), spans


def _token_events(code: str) -> tuple[list[tuple[str, int, int]] | None, str | None]:
    events: list[tuple[str, int, int]] = []
    try:
        for token in py_tokenize.generate_tokens(io.StringIO(code).readline):
            if token.type in _SERVICE_TOKEN_TYPES:
                continue
            if token.type == py_tokenize.ERRORTOKEN and not token.string.strip():
                continue
            events.append((token.string, token.start[0], token.end[0]))
    except (py_tokenize.TokenError, IndentationError, SyntaxError) as exc:
        return None, _format_token_error(exc)
    return events, None


def build_token_features(submission: Submission, assignment: Assignment) -> FeatureSet:
    line_count = len(submission.code.splitlines())
    template_lines = _template_lines(submission.code, assignment)
    events, error = _token_events(submission.code)
    if events is None:
        return FeatureSet(
            method=TOKEN_METHOD,
            method_version=FEATURE_VERSION,
            submission_id=submission.submission_id,
            assignment_id=submission.assignment_id,
            student_id=submission.student_id,
            status="syntax_error",
            message=error,
            line_count=line_count,
            unit_count=0,
            units=frozenset(),
            spans={},
            template_lines=template_lines,
        )

    units, spans = _build_units(events)
    status = "ok" if units else "insufficient"
    return FeatureSet(
        method=TOKEN_METHOD,
        method_version=FEATURE_VERSION,
        submission_id=submission.submission_id,
        assignment_id=submission.assignment_id,
        student_id=submission.student_id,
        status=status,
        message=None,
        line_count=line_count,
        unit_count=len(events),
        units=units,
        spans=spans,
        template_lines=template_lines,
    )


class _IdentifierNormalizer(ast.NodeTransformer):
    def __init__(self, mapping: dict[str, str]) -> None:
        self._mapping = mapping

    def _normalized(self, name: str) -> str:
        return self._mapping.get(name, name)

    def visit_Name(self, node: ast.Name) -> ast.AST:
        node.id = self._normalized(node.id)
        return node

    def visit_arg(self, node: ast.arg) -> ast.AST:
        node.arg = self._normalized(node.arg)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.name = self._normalized(node.name)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        node.name = self._normalized(node.name)
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        node.name = self._normalized(node.name)
        self.generic_visit(node)
        return node


def _identifier_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.arg):
        return node.arg
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    return None


def _user_identifiers(tree: ast.AST) -> dict[str, str]:
    located: list[tuple[int, int, int, str]] = []
    order = 0
    for node in ast.walk(tree):
        name = _identifier_name(node)
        if name is None or not name:
            continue
        line = getattr(node, "lineno", 0)
        column = getattr(node, "col_offset", 0)
        located.append((line, column, order, name))
        order += 1
    located.sort(key=lambda item: (item[0], item[1], item[2]))

    mapping: dict[str, str] = {}
    for _, _, _, name in located:
        if name not in mapping:
            mapping[name] = f"id{len(mapping)}"
    return mapping


def _ast_label(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return f"Name:{node.id}"
    if isinstance(node, ast.arg):
        return f"arg:{node.arg}"
    if isinstance(node, ast.Constant):
        value = repr(node.value)
        if len(value) > 40:
            value = value[:37] + "..."
        return f"Constant:{value}"
    label = type(node).__name__
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        label = f"{label}:{node.name}"
    return label


def _ast_events(node: ast.AST, fallback_line: int = 1) -> Iterator[tuple[str, int, int]]:
    line = getattr(node, "lineno", fallback_line)
    end_line = getattr(node, "end_lineno", line)
    yield (_ast_label(node), line, end_line)
    for child in ast.iter_child_nodes(node):
        yield from _ast_events(child, line)


def build_ast_features(submission: Submission, assignment: Assignment) -> FeatureSet:
    line_count = len(submission.code.splitlines())
    template_lines = _template_lines(submission.code, assignment)
    try:
        tree = ast.parse(submission.code)
    except SyntaxError as exc:
        return FeatureSet(
            method=AST_METHOD,
            method_version=FEATURE_VERSION,
            submission_id=submission.submission_id,
            assignment_id=submission.assignment_id,
            student_id=submission.student_id,
            status="syntax_error",
            message=_format_token_error(exc),
            line_count=line_count,
            unit_count=0,
            units=frozenset(),
            spans={},
            template_lines=template_lines,
        )

    mapping = _user_identifiers(tree)
    normalized = _IdentifierNormalizer(mapping).visit(tree)
    ast.fix_missing_locations(normalized)
    dumped = ast.dump(normalized, annotate_fields=True, include_attributes=False)
    structure_hash = hashlib.sha256(dumped.encode("utf-8")).hexdigest()

    events = list(_ast_events(normalized))
    units, spans = _build_units(events)
    status = "ok" if units else "insufficient"
    return FeatureSet(
        method=AST_METHOD,
        method_version=FEATURE_VERSION,
        submission_id=submission.submission_id,
        assignment_id=submission.assignment_id,
        student_id=submission.student_id,
        status=status,
        message=None,
        line_count=line_count,
        unit_count=len(events),
        units=units,
        spans=spans,
        template_lines=template_lines,
        structure_hash=structure_hash,
    )


def build_features(
    submission: Submission,
    assignment: Assignment,
    method: str = TOKEN_METHOD,
) -> FeatureSet:
    if method == TOKEN_METHOD:
        return build_token_features(submission, assignment)
    if method == AST_METHOD:
        return build_ast_features(submission, assignment)
    raise ValueError(f"Unknown feature method: {method}")


def supported_methods() -> tuple[str, ...]:
    return (TOKEN_METHOD, AST_METHOD)
