from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .comparison import DEFAULT_MAX_EVIDENCE, PairSimilarity, compare_features
from .features import FEATURE_VERSION, FeatureSet, build_features
from .models import Assignment, Submission
from .parser import parse_assignment, parse_submission

DERIVED_RELATIONS = frozenset(
    {
        "exact_copy",
        "reformatted_copy",
        "renamed_copy",
        "comment_change",
    }
)
TEMPLATE_RELATION = "same_template"
NEGATIVE_RELATIONS = frozenset({"independent", TEMPLATE_RELATION})


@dataclass(frozen=True, slots=True)
class Corpus:
    directory: Path
    submissions: dict[str, Submission]
    origins: dict[str, dict[str, Any]]
    pairs: tuple[dict[str, Any], ...]
    split: dict[str, Any]
    assignments: dict[str, Assignment]


@dataclass(frozen=True, slots=True)
class ScoredPair:
    pair: dict[str, Any]
    comparison: PairSimilarity
    split: str
    positive: bool

    @property
    def pair_id(self) -> str:
        return self.pair["pair_id"]

    @property
    def relation(self) -> str:
        return self.pair["derivation_relation"]

    @property
    def template_only(self) -> bool:
        return bool(self.pair.get("template_only", False))

    @property
    def score(self) -> float | None:
        return self.comparison.score


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_corpus(directory: str | Path) -> Corpus:
    directory = Path(directory)
    assignments: dict[str, Assignment] = {}
    for path in sorted(directory.glob("*.assignment.json")):
        assignment = parse_assignment(json.loads(path.read_text(encoding="utf-8")))
        assignments[assignment.assignment_id] = assignment

    submissions: dict[str, Submission] = {}
    for raw in _read_jsonl(directory / "submissions.jsonl"):
        submission = parse_submission(raw)
        if submission.submission_id in submissions:
            raise ValueError(f"Duplicate submission_id: {submission.submission_id}")
        submissions[submission.submission_id] = submission

    origins = {row["submission_id"]: row for row in _read_jsonl(directory / "origins.jsonl")}
    pairs = tuple(_read_jsonl(directory / "pairs.jsonl"))
    split = json.loads((directory / "split.json").read_text(encoding="utf-8"))

    corpus = Corpus(
        directory=directory,
        submissions=submissions,
        origins=origins,
        pairs=pairs,
        split=split,
        assignments=assignments,
    )
    validate_corpus(corpus)
    return corpus


def validate_corpus(corpus: Corpus) -> None:
    family_splits: dict[str, set[str]] = {}
    for submission_id, origin in corpus.origins.items():
        if submission_id not in corpus.submissions:
            raise ValueError(f"Origin for unknown submission: {submission_id}")
        family_splits.setdefault(origin["family_id"], set()).add(origin["split"])

    for family_id, splits in family_splits.items():
        if len(splits) > 1:
            raise ValueError(f"Family {family_id} leaks across splits: {sorted(splits)}")

    for pair in corpus.pairs:
        left_id = pair["left_submission_id"]
        right_id = pair["right_submission_id"]
        if left_id not in corpus.submissions or right_id not in corpus.submissions:
            raise ValueError(f"Pair {pair['pair_id']} references unknown submission")
        left = corpus.submissions[left_id]
        right = corpus.submissions[right_id]
        if left.assignment_id != pair["assignment_id"]:
            raise ValueError(f"Pair {pair['pair_id']} assignment mismatch")
        if right.assignment_id != pair["assignment_id"]:
            raise ValueError(f"Pair {pair['pair_id']} assignment mismatch")
        left_split = corpus.origins[left_id]["split"]
        right_split = corpus.origins[right_id]["split"]
        if left_split != right_split:
            raise ValueError(
                f"Pair {pair['pair_id']} crosses setup/eval: {left_split} vs {right_split}"
            )
        if pair.get("template_only") != (pair["derivation_relation"] == TEMPLATE_RELATION):
            raise ValueError(f"Pair {pair['pair_id']} has inconsistent template_only")


def pair_split(corpus: Corpus, pair: dict[str, Any]) -> str:
    return corpus.origins[pair["left_submission_id"]]["split"]


def build_index(corpus: Corpus, method: str) -> dict[str, FeatureSet]:
    index: dict[str, FeatureSet] = {}
    for submission_id, submission in corpus.submissions.items():
        assignment = corpus.assignments.get(submission.assignment_id)
        if assignment is None:
            raise ValueError(f"No assignment for submission {submission_id}")
        index[submission_id] = build_features(submission, assignment, method)
    return index


def score_pairs(
    corpus: Corpus,
    index: dict[str, FeatureSet],
    max_evidence: int = DEFAULT_MAX_EVIDENCE,
) -> list[ScoredPair]:
    scored: list[ScoredPair] = []
    for pair in corpus.pairs:
        left = index[pair["left_submission_id"]]
        right = index[pair["right_submission_id"]]
        comparison = compare_features(left, right, max_evidence=max_evidence)
        scored.append(
            ScoredPair(
                pair=pair,
                comparison=comparison,
                split=pair_split(corpus, pair),
                positive=pair["derivation_relation"] in DERIVED_RELATIONS,
            )
        )
    return scored


def _safe_div(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _confusion(scored: Iterable[ScoredPair], threshold: float) -> dict[str, Any]:
    materialized = list(scored)
    tp = fp = tn = fn = 0
    uncertain = 0
    flagged = 0
    for item in materialized:
        score = item.score
        if score is None:
            uncertain += 1
            predicted = False
        else:
            predicted = score >= threshold
        if predicted:
            flagged += 1
        if item.positive and predicted:
            tp += 1
        elif item.positive:
            fn += 1
        elif predicted:
            fp += 1
        else:
            tn += 1

    total = len(materialized)
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    specificity = _safe_div(tn, tn + fp)
    f1 = None
    if precision is not None and recall is not None and precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)
    return {
        "threshold": threshold,
        "total": total,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "flagged": flagged,
        "uncertain": uncertain,
        "review_rate": _safe_div(flagged, total),
        "uncertain_share": _safe_div(uncertain, total),
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "false_positive_rate": _safe_div(fp, fp + tn),
        "f1": f1,
    }


def _fbeta(precision: float | None, recall: float | None, beta: float) -> float:
    if precision is None or recall is None:
        return 0.0
    beta_squared = beta * beta
    denominator = beta_squared * precision + recall
    if denominator == 0:
        return 0.0
    return (1 + beta_squared) * precision * recall / denominator


def _thresholds(step: float) -> list[float]:
    if step <= 0 or step > 1:
        raise ValueError("threshold step must be in (0, 1]")
    count = int(round(1 / step))
    return [round(index * step, 10) for index in range(count + 1)]


def select_threshold(scored: Iterable[ScoredPair], step: float = 0.01) -> dict[str, Any]:
    materialized = list(scored)
    scores = [item.score for item in materialized if item.score is not None]
    grid = _thresholds(step)
    best_metrics: dict[str, Any] | None = None
    best_key: tuple[float, ...] | None = None

    for threshold in grid:
        metrics = _confusion(materialized, threshold)
        f05 = _fbeta(metrics["precision"], metrics["recall"], beta=0.5)
        metrics["f0_5"] = f05
        recall = metrics["recall"] or 0.0
        specificity = metrics["specificity"]
        balanced = min(recall, specificity if specificity is not None else 1.0)
        margin = min((abs(threshold - score) for score in scores), default=0.0)
        key = (f05, balanced, margin, -threshold)
        if best_key is None or key > best_key:
            best_key = key
            best_metrics = metrics

    assert best_metrics is not None
    return {
        "threshold": best_metrics["threshold"],
        "criterion": "max_f0_5_then_balanced_accuracy_then_margin",
        "step": step,
        "grid_min": grid[0],
        "grid_max": grid[-1],
        "metrics": best_metrics,
    }


def _score_stats(scored: Iterable[ScoredPair]) -> dict[str, Any]:
    materialized = list(scored)
    scores = [item.score for item in materialized if item.score is not None]
    if not scores:
        return {"count": len(materialized), "defined": 0, "mean": None, "min": None, "max": None}
    return {
        "count": len(materialized),
        "defined": len(scores),
        "mean": sum(scores) / len(scores),
        "min": min(scores),
        "max": max(scores),
    }


def _by_relation(scored: Iterable[ScoredPair], threshold: float) -> dict[str, Any]:
    groups: dict[str, list[ScoredPair]] = {}
    for item in scored:
        groups.setdefault(item.relation, []).append(item)
    result: dict[str, Any] = {}
    for relation, items in sorted(groups.items()):
        metrics = _confusion(items, threshold)
        result[relation] = {
            "pairs": len(items),
            "flagged": metrics["flagged"],
            "uncertain": metrics["uncertain"],
            "scores": _score_stats(items),
        }
    return result


def _status_counts(scored: Iterable[ScoredPair]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in scored:
        status = item.comparison.status
        counts[status] = counts.get(status, 0) + 1
    return counts


def _template_slice(scored: Iterable[ScoredPair], threshold: float) -> dict[str, Any]:
    items = [item for item in scored if item.template_only]
    flagged = [item for item in items if item.score is not None and item.score >= threshold]
    explained = [item for item in items if item.comparison.status == "template_only"]
    return {
        "pairs": len(items),
        "flagged": len(flagged),
        "flagged_share": _safe_div(len(flagged), len(items)),
        "explained_as_template": len(explained),
        "scores": _score_stats(items),
    }


def _flag(item: ScoredPair, threshold: float) -> bool:
    return item.score is not None and item.score >= threshold


def _error_record(
    item: ScoredPair,
    method: str,
    threshold: float,
    category: str,
    explanation: str,
) -> dict[str, Any]:
    return {
        "method": method,
        "pair_id": item.pair_id,
        "left_submission_id": item.pair["left_submission_id"],
        "right_submission_id": item.pair["right_submission_id"],
        "assignment_id": item.pair["assignment_id"],
        "relation": item.relation,
        "template_only": item.template_only,
        "split": item.split,
        "score": item.score,
        "threshold": threshold,
        "flagged": _flag(item, threshold),
        "ground_truth_positive": item.positive,
        "category": category,
        "explanation": explanation,
        "evidence": [entry.to_dict() for entry in item.comparison.evidence[:3]],
    }


def _explain(category: str, item: ScoredPair, method: str) -> str:
    if category == "template_false_positive":
        return (
            "Совпадение целиком объяснено разрешённым шаблоном: пара попала в "
            "review_required из-за высокого сходства, но это не доказательство нарушения."
        )
    if category == "false_negative":
        if item.relation == "renamed_copy":
            return (
                f"{method}: переименование переменных снизило сходство ниже порога; "
                "именно такой случай должен ловить структурный метод."
            )
        return (
            f"{method}: сходство оказалось ниже порога, хотя пара размечена как "
            f"{item.relation}."
        )
    if category == "independent_false_positive":
        return (
            "Независимые решения используют общий каркас языка, поэтому сходство "
            "превысило порог. Это ложное срабатывание, а не совпадение работы."
        )
    if category == "uncertain":
        return (
            "Результат неопределён: признаков недостаточно или исходник не разобран. "
            "Пара не может быть автоматически отнесена ни к одной стороне."
        )
    return "Ошибка классификации относительно размеченного отношения."


def _pick(
    items: list[ScoredPair],
    key,
    reverse: bool,
) -> ScoredPair | None:
    if not items:
        return None
    return sorted(items, key=key, reverse=reverse)[0]


def analyze_errors(
    eval_by_method: dict[str, list[ScoredPair]],
    thresholds: dict[str, float],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(item: ScoredPair, method: str, category: str) -> None:
        marker = (method, item.pair_id)
        if marker in seen:
            return
        seen.add(marker)
        records.append(
            _error_record(
                item,
                method,
                thresholds[method],
                category,
                _explain(category, item, method),
            )
        )

    for method, items in eval_by_method.items():
        threshold = thresholds[method]
        template_flagged = [
            item for item in items if item.template_only and _flag(item, threshold)
        ]
        best_template = _pick(
            template_flagged,
            key=lambda item: item.score if item.score is not None else -1.0,
            reverse=True,
        )
        if best_template is not None:
            add(best_template, method, "template_false_positive")

    for method, items in eval_by_method.items():
        threshold = thresholds[method]
        false_negatives = [
            item for item in items if item.positive and not _flag(item, threshold)
        ]
        ordered = sorted(
            false_negatives,
            key=lambda item: item.score if item.score is not None else -1.0,
        )
        for worst in ordered[:2]:
            add(worst, method, "false_negative")

    for method, items in eval_by_method.items():
        threshold = thresholds[method]
        independent_flagged = [
            item
            for item in items
            if not item.positive and not item.template_only and _flag(item, threshold)
        ]
        best = _pick(
            independent_flagged,
            key=lambda item: item.score if item.score is not None else -1.0,
            reverse=True,
        )
        if best is not None:
            add(best, method, "independent_false_positive")

    for method, items in eval_by_method.items():
        uncertain = [item for item in items if item.score is None]
        candidate = uncertain[0] if uncertain else None
        if candidate is not None:
            add(candidate, method, "uncertain")

    if len(records) < 3:
        for method, items in eval_by_method.items():
            threshold = thresholds[method]
            misclassified = [
                item for item in items if item.positive != _flag(item, threshold)
            ]
            for item in sorted(
                misclassified,
                key=lambda value: abs((value.score or 0.0) - threshold),
                reverse=True,
            ):
                category = "false_negative" if item.positive else "independent_false_positive"
                add(item, method, category)
                if len(records) >= 3:
                    break
            if len(records) >= 3:
                break

    return records[:6]


def _method_agreement(
    eval_by_method: dict[str, list[ScoredPair]],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    methods = list(eval_by_method)
    if len(methods) < 2:
        return {"methods": methods, "pairs": 0, "note": "need at least two methods"}

    first, second = methods[0], methods[1]
    second_index = {item.pair_id: item for item in eval_by_method[second]}
    counts = {
        "both_flagged": 0,
        "first_only": 0,
        "second_only": 0,
        "neither_flagged": 0,
    }
    by_relation: dict[str, dict[str, int]] = {}
    for item in eval_by_method[first]:
        other = second_index[item.pair_id]
        first_flag = _flag(item, thresholds[first])
        second_flag = _flag(other, thresholds[second])
        if first_flag and second_flag:
            key = "both_flagged"
        elif first_flag:
            key = "first_only"
        elif second_flag:
            key = "second_only"
        else:
            key = "neither_flagged"
        counts[key] += 1
        relation_counts = by_relation.setdefault(
            item.relation,
            {"both_flagged": 0, "first_only": 0, "second_only": 0, "neither_flagged": 0},
        )
        relation_counts[key] += 1

    return {
        "methods": [first, second],
        "pairs": len(eval_by_method[first]),
        **counts,
        "by_relation": by_relation,
    }


def _corpus_stats(corpus: Corpus) -> dict[str, Any]:
    splits: dict[str, int] = {}
    relations: dict[str, int] = {}
    for origin in corpus.origins.values():
        splits[origin["split"]] = splits.get(origin["split"], 0) + 1
    for pair in corpus.pairs:
        relations[pair["derivation_relation"]] = (
            relations.get(pair["derivation_relation"], 0) + 1
        )
    return {
        "directory": str(corpus.directory),
        "assignments": sorted(corpus.assignments),
        "submissions": len(corpus.submissions),
        "origins": len(corpus.origins),
        "pairs": len(corpus.pairs),
        "submissions_by_split": splits,
        "pairs_by_relation": relations,
        "template_pairs": sum(1 for pair in corpus.pairs if pair.get("template_only")),
        "validation": "ok",
    }


def evaluate_corpus(
    directory: str | Path,
    methods: Iterable[str],
    threshold_step: float = 0.01,
    max_evidence: int = DEFAULT_MAX_EVIDENCE,
) -> dict[str, Any]:
    corpus = load_corpus(directory)
    method_list = list(methods)
    scores_by_method: dict[str, list[ScoredPair]] = {}
    indexes: dict[str, dict[str, FeatureSet]] = {}

    for method in method_list:
        index = build_index(corpus, method)
        indexes[method] = index
        scores_by_method[method] = score_pairs(
            corpus, index, max_evidence=max_evidence
        )

    results: dict[str, Any] = {}
    thresholds: dict[str, float] = {}
    eval_by_method: dict[str, list[ScoredPair]] = {}

    for method in method_list:
        all_scores = scores_by_method[method]
        setup = [item for item in all_scores if item.split == "setup"]
        eval_items = [item for item in all_scores if item.split == "eval"]
        eval_by_method[method] = eval_items

        selection = select_threshold(setup, step=threshold_step)
        threshold = selection["threshold"]
        thresholds[method] = threshold
        setup_metrics = _confusion(setup, threshold)
        eval_metrics = _confusion(eval_items, threshold)
        eval_without_template = [
            item for item in eval_items if not item.template_only
        ]

        results[method] = {
            "method_version": FEATURE_VERSION,
            "threshold": threshold,
            "threshold_selection": selection,
            "setup": setup_metrics,
            "eval": eval_metrics,
            "eval_without_template": _confusion(eval_without_template, threshold),
            "by_relation": _by_relation(eval_items, threshold),
            "statuses": _status_counts(eval_items),
            "template_slice": _template_slice(eval_items, threshold),
            "index_size_bytes_estimate": sum(
                feature.approximate_size_bytes() for feature in indexes[method].values()
            ),
        }

    report = {
        "corpus": _corpus_stats(corpus),
        "config": {
            "methods": method_list,
            "feature_version": FEATURE_VERSION,
            "threshold_step": threshold_step,
            "max_evidence": max_evidence,
            "positive_relations": sorted(DERIVED_RELATIONS),
            "negative_relations": sorted(NEGATIVE_RELATIONS),
        },
        "methods": results,
        "method_agreement": _method_agreement(eval_by_method, thresholds),
        "errors": analyze_errors(eval_by_method, thresholds),
    }
    return report


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = ["# Результаты оценки сходства", ""]
    corpus = report["corpus"]
    lines.extend(
        [
            "## Корпус",
            "",
            f"- Сдач: {corpus['submissions']}",
            f"- Пар: {corpus['pairs']}",
            f"- Пар с шаблоном: {corpus['template_pairs']}",
            f"- Задания: {', '.join(corpus['assignments'])}",
            f"- Проверка утечки семейств: {corpus['validation']}",
            "",
        ]
    )

    lines.extend(["## Сравнение методов", ""])
    lines.append(
        "| метод | порог | TP | FP | TN | FN | precision | recall | F1 | неопр. |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for method, result in report["methods"].items():
        eval_metrics = result["eval"]
        lines.append(
            "| {method} | {threshold} | {tp} | {fp} | {tn} | {fn} | {precision} | "
            "{recall} | {f1} | {uncertain} |".format(
                method=method,
                threshold=_fmt(result["threshold"]),
                tp=eval_metrics["tp"],
                fp=eval_metrics["fp"],
                tn=eval_metrics["tn"],
                fn=eval_metrics["fn"],
                precision=_fmt(eval_metrics["precision"]),
                recall=_fmt(eval_metrics["recall"]),
                f1=_fmt(eval_metrics["f1"]),
                uncertain=f"{eval_metrics['uncertain']} ({_fmt(eval_metrics['uncertain_share'])})",
            )
        )
    lines.append("")

    lines.extend(["## Eval без шаблонных пар", ""])
    lines.append("| метод | TP | FP | TN | FN | precision | recall | F1 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for method, result in report["methods"].items():
        metrics = result["eval_without_template"]
        lines.append(
            "| {method} | {tp} | {fp} | {tn} | {fn} | {precision} | {recall} | {f1} |".format(
                method=method,
                tp=metrics["tp"],
                fp=metrics["fp"],
                tn=metrics["tn"],
                fn=metrics["fn"],
                precision=_fmt(metrics["precision"]),
                recall=_fmt(metrics["recall"]),
                f1=_fmt(metrics["f1"]),
            )
        )
    lines.append("")

    lines.extend(["## Выбор порога на setup", ""])
    for method, result in report["methods"].items():
        selection = result["threshold_selection"]
        setup = result["setup"]
        lines.append(
            f"- `{method}`: порог {_fmt(result['threshold'])}, F1 на setup "
            f"{_fmt(setup['f1'])}, precision {_fmt(setup['precision'])}, "
            f"recall {_fmt(setup['recall'])}; критерий: {selection['criterion']}."
        )
    lines.append("")

    lines.extend(["## Срез по отношениям на eval", ""])
    for method, result in report["methods"].items():
        lines.append(f"### {method}")
        lines.append("")
        lines.append("| отношение | пар | попало в review | неопределённых | средний score |")
        lines.append("|---|---:|---:|---:|---:|")
        for relation, data in result["by_relation"].items():
            stats = data["scores"]
            lines.append(
                f"| {relation} | {data['pairs']} | {data['flagged']} | "
                f"{data['uncertain']} | {_fmt(stats['mean'])} |"
            )
        template = result["template_slice"]
        lines.extend(
            [
                "",
                f"Шаблонные пары: {template['pairs']}, попали в review "
                f"{template['flagged']} ({_fmt(template['flagged_share'])}), "
                f"объяснены как `template_only`: {template['explained_as_template']}.",
                "",
            ]
        )

    agreement = report["method_agreement"]
    if agreement.get("pairs"):
        lines.extend(
            [
                "## Согласие методов на eval",
                "",
                f"- Оба отметили: {agreement['both_flagged']}",
                f"- Только {agreement['methods'][0]}: {agreement['first_only']}",
                f"- Только {agreement['methods'][1]}: {agreement['second_only']}",
                f"- Ни один: {agreement['neither_flagged']}",
                "",
            ]
        )

    lines.extend(["## Разбор ошибок", ""])
    if not report["errors"]:
        lines.append("Ошибок не найдено.")
    for index, error in enumerate(report["errors"], start=1):
        lines.extend(
            [
                f"### {index}. {error['category']} ({error['method']})",
                "",
                f"- Пара: `{error['left_submission_id']}` / `{error['right_submission_id']}`",
                f"- Отношение: `{error['relation']}`, шаблон: {error['template_only']}",
                f"- Score: {_fmt(error['score'])}, порог: {_fmt(error['threshold'])}, "
                f"review_required: {error['flagged']}",
                f"- Объяснение: {error['explanation']}",
                "",
            ]
        )
        if error["evidence"]:
            lines.append("Evidence:")
            for item in error["evidence"]:
                lines.append(
                    f"- `{item['left']['line_start']}-{item['left']['line_end']}` ↔ "
                    f"`{item['right']['line_start']}-{item['right']['line_end']}`: "
                    f"`{' '.join(item['unit'])}`"
                )
            lines.append("")

    lines.extend(
        [
            "## Ограничения",
            "",
            "- Корпус синтетический и малый; метрики не переносятся на реальных студентов.",
            "- Порог выбран на setup, метрики посчитаны на eval без повторной настройки.",
            "- `review_required` означает необходимость ручного разбора, а не нарушение.",
            "- Общий шаблон даёт высокий score и объясняется отдельно через `template_only`.",
            "",
        ]
    )
    return "\n".join(lines)
