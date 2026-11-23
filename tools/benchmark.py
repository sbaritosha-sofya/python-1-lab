from __future__ import annotations

import argparse
import cProfile
import gc
import io
import json
import os
import platform as platform_module
import pstats
import random
import statistics
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from school_submissions.comparison import find_top_k
from school_submissions.features import (
    AST_METHOD,
    TOKEN_METHOD,
    FeatureSet,
    build_features,
)
from school_submissions.models import Assignment, Submission
from school_submissions.parser import parse_assignment, parse_submission

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "corpus"
ASSIGNMENT_ID = "lab-sort"
CREATED_AT = "2026-11-01T10:00:00+03:00"


def load_inputs() -> tuple[Assignment, list[str]]:
    assignment = parse_assignment(
        json.loads((CORPUS / f"{ASSIGNMENT_ID}.assignment.json").read_text(encoding="utf-8"))
    )
    codes: list[str] = []
    for line in (CORPUS / "submissions.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        submission = parse_submission(json.loads(line))
        if submission.assignment_id == ASSIGNMENT_ID:
            codes.append(submission.code)
    if not codes:
        raise RuntimeError("No source code found for load generation")
    return assignment, codes


def make_load_submissions(count: int, codes: list[str], seed: int) -> list[Submission]:
    rng = random.Random(seed)
    submissions: list[Submission] = []
    for index in range(count):
        submissions.append(
            Submission(
                submission_id=f"load-{index:05d}",
                assignment_id=ASSIGNMENT_ID,
                student_id=f"load-student-{index:05d}",
                text="synthetic load record",
                code=rng.choice(codes),
                used_ai=False,
                timestamp=datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc),
            )
        )
    return submissions


def run_workload(
    submissions: list[Submission],
    assignment: Assignment,
    method: str,
    query_limit: int,
) -> int:
    index = [build_features(submission, assignment, method) for submission in submissions]
    queries = index[: min(query_limit, len(index))]
    for query in queries:
        find_top_k(query, index, k=5)
    return len(queries) * max(0, len(index) - 1)


def measure(
    submissions: list[Submission],
    assignment: Assignment,
    method: str,
    repeats: int,
    query_limit: int,
) -> dict[str, object]:
    wall_runs: list[float] = []
    peak_runs: list[int] = []
    comparisons = 0
    for _ in range(repeats):
        gc.collect()
        started = time.perf_counter()
        comparisons = run_workload(submissions, assignment, method, query_limit)
        wall_runs.append(time.perf_counter() - started)

    for _ in range(repeats):
        gc.collect()
        tracemalloc.start()
        try:
            run_workload(submissions, assignment, method, query_limit)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        peak_runs.append(peak)

    return {
        "wall_seconds_runs": wall_runs,
        "wall_seconds_median": statistics.median(wall_runs),
        "peak_mib_runs": [value / (1024 * 1024) for value in peak_runs],
        "peak_mib_median": statistics.median(peak_runs) / (1024 * 1024),
        "comparisons": comparisons,
    }


def _legacy_span_is_template(feature: FeatureSet, span) -> bool:
    if not feature.template_lines:
        return False
    return all(
        line in feature.template_lines for line in range(span.start, span.end + 1)
    )


def _legacy_unit_is_template(feature: FeatureSet, unit: tuple[str, ...]) -> bool:
    spans = feature.spans.get(unit, ())
    return bool(spans) and all(
        _legacy_span_is_template(feature, span) for span in spans
    )


def legacy_score_only(left: FeatureSet, right: FeatureSet) -> tuple[float, bool]:
    shared = left.units & right.units
    union = left.units | right.units
    if not union:
        return 0.0, False
    template_shared = {
        unit
        for unit in shared
        if _legacy_unit_is_template(left, unit)
        and _legacy_unit_is_template(right, unit)
    }
    return len(shared) / len(union), bool(shared) and template_shared == shared


def optimized_score_only(left: FeatureSet, right: FeatureSet) -> tuple[float, bool]:
    shared = left.units & right.units
    union_size = len(left.units) + len(right.units) - len(shared)
    if union_size == 0:
        return 0.0, False
    template_shared = shared & left.template_units & right.template_units
    return len(shared) / union_size, bool(shared) and template_shared == shared


def benchmark_optimization(repeats: int = 3) -> dict[str, object]:
    assignment, codes = load_inputs()
    submissions = make_load_submissions(1000, codes, seed=42)
    features = [build_features(submission, assignment, TOKEN_METHOD) for submission in submissions]
    rng = random.Random(7)
    pairs = []
    for _ in range(2000):
        left = rng.choice(features)
        right = rng.choice(features)
        if left.submission_id == right.submission_id:
            continue
        pairs.append((left, right))

    legacy_times: list[float] = []
    optimized_times: list[float] = []
    equal = True
    for _ in range(repeats):
        gc.collect()
        started = time.perf_counter()
        for left, right in pairs:
            legacy_score_only(left, right)
        legacy_times.append(time.perf_counter() - started)

        gc.collect()
        started = time.perf_counter()
        for left, right in pairs:
            optimized_score_only(left, right)
        optimized_times.append(time.perf_counter() - started)

    for left, right in pairs:
        legacy = legacy_score_only(left, right)
        optimized = optimized_score_only(left, right)
        if abs(legacy[0] - optimized[0]) > 1e-12 or legacy[1] != optimized[1]:
            equal = False
            break

    legacy_median = statistics.median(legacy_times)
    optimized_median = statistics.median(optimized_times)
    return {
        "description": (
            "score-only benchmark: union set allocation and per-pair template span "
            "scan (legacy) versus union size arithmetic and precomputed template_units"
        ),
        "pairs": len(pairs),
        "repeats": repeats,
        "legacy_seconds_runs": legacy_times,
        "optimized_seconds_runs": optimized_times,
        "legacy_seconds_median": legacy_median,
        "optimized_seconds_median": optimized_median,
        "speedup": legacy_median / optimized_median if optimized_median else None,
        "scores_equal": equal,
    }


def write_profile(path: Path, assignment: Assignment) -> None:
    submissions = make_load_submissions(1000, load_inputs()[1], seed=42)
    profiler = cProfile.Profile()
    profiler.enable()
    for method in (TOKEN_METHOD, AST_METHOD):
        run_workload(submissions, assignment, method, query_limit=50)
    profiler.disable()
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats(25)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stream.getvalue(), encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# Замеры производительности", ""]
    environment = report["environment"]
    parameters = report["parameters"]
    lines.extend(
        [
            "## Среда",
            "",
            f"- Python: {environment['python']}",
            f"- Платформа: {environment['platform']}",
            f"- CPU: {environment['cpu_count']}",
            f"- seed: {parameters['seed']}",
            f"- повторов на замер: {parameters['repeats']}",
            f"- запросов top-k: {parameters['query_limit']}",
            "",
            "Данные для нагрузки синтетические и не используются для оценки качества.",
            "",
            "## Время и память",
            "",
            "| записей | метод | медиана времени, с | медиана памяти, МиБ | сравнений |",
            "|---:|---|---:|---:|---:|",
        ]
    )
    measurements = report["measurements"]
    for size in parameters["sizes"]:
        for method, runs in measurements.items():
            result = runs[str(size)]
            lines.append(
                f"| {size} | {method} | {result['wall_seconds_median']:.3f} | "
                f"{result['peak_mib_median']:.2f} | {result['comparisons']} |"
            )
    optimization = report["optimization"]
    lines.extend(
        [
            "",
            "## Оптимизация сравнения",
            "",
            f"- Пар в замере: {optimization['pairs']}",
            f"- Было (медиана): {optimization['legacy_seconds_median']:.4f} с",
            f"- Стало (медиана): {optimization['optimized_seconds_median']:.4f} с",
            f"- Ускорение: {optimization['speedup']:.2f}x",
            f"- Score и template_only совпадают: {optimization['scores_equal']}",
            "",
            "Что изменено: размер объединения считается арифметически без создания "
            "множества объединения, а шаблонные признаки предвычисляются в "
            "`template_units` вместо повторного обхода диапазонов строк на каждую пару.",
            "",
            "## Ограничения",
            "",
            "- Пиковая память измерена через `tracemalloc` (память Python-кучи).",
            "- Нагрузка включает построение индекса и top-k для фиксированного числа "
            "запросов, а не полный перебор всех пар.",
            "- Конкурентность не измеряется.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Замеры производительности анализатора")
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[100, 1000, 5000],
        help="Размеры корпуса",
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--query-limit", type=int, default=100)
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=[TOKEN_METHOD, AST_METHOD],
        default=[TOKEN_METHOD, AST_METHOD],
    )
    parser.add_argument("--output", default="reports/performance.json")
    parser.add_argument("--markdown", default="reports/performance.md")
    parser.add_argument("--profile", default="reports/profile.txt")
    args = parser.parse_args(argv)

    assignment, codes = load_inputs()
    measurements: dict[str, dict[str, Any]] = {}
    for method in args.methods:
        method_results: dict[str, Any] = {}
        for size in args.sizes:
            submissions = make_load_submissions(size, codes, seed=args.seed)
            method_results[str(size)] = measure(
                submissions,
                assignment,
                method,
                repeats=args.repeats,
                query_limit=args.query_limit,
            )
        measurements[method] = method_results

    report: dict[str, Any] = {
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform_module.platform(),
            "cpu_count": os.cpu_count(),
            "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        },
        "parameters": {
            "sizes": args.sizes,
            "repeats": args.repeats,
            "seed": args.seed,
            "query_limit": args.query_limit,
            "methods": args.methods,
            "ngram_size": 3,
        },
        "measurements": measurements,
        "optimization": benchmark_optimization(repeats=args.repeats),
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    markdown = Path(args.markdown)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(report) + "\n", encoding="utf-8")

    write_profile(Path(args.profile), assignment)

    print(
        f"wrote {output}, {markdown}, {args.profile}; "
        f"speedup={report['optimization']['speedup']:.2f}x"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
