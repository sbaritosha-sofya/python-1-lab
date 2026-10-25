from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .service import SubmissionService


def cmd_import(args: argparse.Namespace) -> int:
    service = SubmissionService()
    report: dict[str, Any] = {
        "accepted": [],
        "duplicates": [],
        "conflicts": [],
        "errors": [],
    }

    # Импорт читает файл построчно: повреждённая строка не останавливает
    # обработку, а попадает в отчёт с номером строки.
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="school-submissions",
        description="Приём лабораторных работ.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="Импорт сдач из JSONL")
    import_parser.add_argument("input", help="Путь к .jsonl файлу")
    import_parser.set_defaults(func=cmd_import)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
