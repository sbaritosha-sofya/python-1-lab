from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .analysis_service import AnalysisService
from .comparison import find_same_student_revisions, find_top_k
from .evaluation import evaluate_corpus, render_markdown
from .features import FEATURE_VERSION, supported_methods
from .models import Assignment, Submission
from .parser import parse_assignment, parse_submission
from .pipeline import index_size_bytes, iter_features
from .service import SubmissionService
from .sources import JSONLSource


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


def cmd_find_similar(args: argparse.Namespace) -> int:
    assignment = _load_assignment(args.assignment)
    source = JSONLSource(args.input)
    features = []
    invalid: list[dict[str, Any]] = []
    stream = iter_features(source, assignment, args.method)

    with source:
        for feature in stream:
            features.append(feature)
            if feature.status != "ok":
                invalid.append(feature.to_dict())

    results: list[dict[str, Any]] = []
    for target in features:
        top = find_top_k(
            target,
            features,
            k=args.top_k,
            include_same_student=args.include_same_student,
            max_evidence=args.max_evidence,
        )
        revisions = find_same_student_revisions(
            target,
            features,
            max_evidence=args.max_evidence,
        )
        results.append(
            {
                "submission_id": target.submission_id,
                "student_id": target.student_id,
                "status": target.status,
                "top": [item.to_dict() for item in top],
                "same_student_revisions": [item.to_dict() for item in revisions],
            }
        )

    report = {
        "assignment_id": assignment.assignment_id,
        "method": args.method,
        "method_version": FEATURE_VERSION,
        "submissions_seen": stream.seen,
        "submissions_indexed": len(features),
        "skipped_other_assignment": stream.skipped_other_assignment,
        "index_size_bytes_estimate": index_size_bytes(features),
        "invalid_features": invalid,
        "results": results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_evaluate_similarity(args: argparse.Namespace) -> int:
    report = evaluate_corpus(
        args.corpus,
        args.methods,
        threshold_step=args.threshold_step,
        max_evidence=args.max_evidence,
    )
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    wrote = False
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
        wrote = True
    if args.markdown:
        markdown = Path(args.markdown)
        markdown.parent.mkdir(parents=True, exist_ok=True)
        markdown.write_text(render_markdown(report) + "\n", encoding="utf-8")
        wrote = True
    if not wrote:
        print(payload)
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

    similar_parser = subparsers.add_parser(
        "find-similar",
        help="Поиск похожих сдач в одном задании",
    )
    similar_parser.add_argument("input", help="Путь к .jsonl файлу с сдачами")
    similar_parser.add_argument(
        "--assignment",
        required=True,
        help="Путь к JSON-файлу задания",
    )
    similar_parser.add_argument(
        "--method",
        choices=supported_methods(),
        default=supported_methods()[0],
        help="Метод сравнения",
    )
    similar_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Сколько кандидатов показывать для каждой сдачи",
    )
    similar_parser.add_argument(
        "--max-evidence",
        type=int,
        default=10,
        help="Сколько совпавших фрагментов прикладывать к паре",
    )
    similar_parser.add_argument(
        "--include-same-student",
        action="store_true",
        help="Разрешить повторные версии одного студента в top-k",
    )
    similar_parser.set_defaults(func=cmd_find_similar)

    evaluate_parser = subparsers.add_parser(
        "evaluate-similarity",
        help="Оценка качества методов на учебном корпусе",
    )
    evaluate_parser.add_argument("corpus", help="Каталог корпуса")
    evaluate_parser.add_argument(
        "--methods",
        nargs="+",
        choices=supported_methods(),
        default=list(supported_methods()),
        help="Сравниваемые методы",
    )
    evaluate_parser.add_argument(
        "--threshold-step",
        type=float,
        default=0.01,
        help="Шаг сетки порога review_required",
    )
    evaluate_parser.add_argument(
        "--max-evidence",
        type=int,
        default=5,
        help="Сколько фрагментов evidence сохранять в разборе ошибок",
    )
    evaluate_parser.add_argument("--output", default="", help="Путь к JSON-отчёту")
    evaluate_parser.add_argument(
        "--markdown",
        default="",
        help="Путь к Markdown-отчёту",
    )
    evaluate_parser.set_defaults(func=cmd_evaluate_similarity)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
