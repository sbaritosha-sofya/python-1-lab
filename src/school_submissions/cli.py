from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .analysis_service import AnalysisService
from .models import Assignment, Submission
from .parser import parse_assignment, parse_submission
from .service import SubmissionService


def cmd_import(args: argparse.Namespace) -> int:
    service = SubmissionService()
    report: dict[str, Any] = {
        "accepted": [],
        "duplicates": [],
        "conflicts": [],
        "errors": [],
    }

    with open(args.input, "r", encoding="utf-8") as fp:
        for line_no, line in enumerate(fp, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                report["errors"].append(
                    {
                        "line": line_no,
                        "code": "format",
                        "field": "<line>",
                        "message": f"Invalid JSON: {exc}",
                    }
                )
                continue

            result = service.accept(raw)
            if result.status == "accepted":
                report["accepted"].append(result.submission.to_dict())
            elif result.status == "duplicate":
                report["duplicates"].append(result.submission.to_dict())
            elif result.status == "conflict":
                report["conflicts"].append(
                    {
                        "existing": result.submission.to_dict(),
                        "attempted": result.attempted.to_dict(),
                    }
                )
            else:
                report["errors"].append(
                    {
                        "line": line_no,
                        "code": result.error["code"],
                        "field": result.error["field"],
                        "message": result.error["message"],
                    }
                )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _load_assignment(path: str) -> Assignment:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_assignment(raw)


def _load_submission(raw: Any) -> Submission:
    return parse_submission(raw)


def cmd_analyze(args: argparse.Namespace) -> int:
    assignment = _load_assignment(args.assignment)
    analysis = AnalysisService()
    reports: list[dict[str, Any]] = []

    with open(args.input, "r", encoding="utf-8") as fp:
        for line_no, line in enumerate(fp, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                reports.append(
                    {
                        "line": line_no,
                        "error": f"Invalid JSON: {exc}",
                    }
                )
                continue

            try:
                submission = _load_submission(raw)
            except ValueError as exc:
                reports.append(
                    {
                        "line": line_no,
                        "error": str(exc),
                    }
                )
                continue

            analyzer_id = args.analyzer
            if analyzer_id:
                report = analysis.analyze(analyzer_id, submission, assignment)
                reports.append(report.to_dict())
            else:
                batch = analysis.analyze_all(submission, assignment)
                reports.append(
                    {
                        "submission_id": submission.submission_id,
                        "analyzer_reports": {
                            key: value.to_dict() for key, value in batch.items()
                        },
                    }
                )

    print(json.dumps(reports, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="school-submissions",
        description="Приём лабораторных работ.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="Импорт сдач из JSONL")
    import_parser.add_argument("input", help="Путь к .jsonl файлу")
    import_parser.set_defaults(func=cmd_import)

    analyze_parser = subparsers.add_parser("analyze", help="Запуск анализатора")
    analyze_parser.add_argument("input", help="Путь к .jsonl файлу с сдачами")
    analyze_parser.add_argument(
        "--assignment",
        required=True,
        help="Путь к JSON-файлу задания",
    )
    analyze_parser.add_argument(
        "--analyzer",
        default="",
        help="Идентификатор анализатора (если не указан -- запускает все)",
    )
    analyze_parser.set_defaults(func=cmd_analyze)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
