from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "corpus"


def load_jsonl(name: str) -> list[dict]:
    path = DATA / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_corpus_size_and_label_coverage() -> None:
    submissions = load_jsonl("submissions.jsonl")
    pairs = load_jsonl("pairs.jsonl")
    origins = load_jsonl("origins.jsonl")

    assert len(submissions) >= 30
    assert len(pairs) >= 40
    assert len(origins) == len(submissions)
    assert {item["submission_id"] for item in origins} == {
        item["submission_id"] for item in submissions
    }


def test_corpus_has_required_relations_and_template_pairs() -> None:
    pairs = load_jsonl("pairs.jsonl")
    relations = {item["derivation_relation"] for item in pairs}

    assert {"exact_copy", "reformatted_copy", "renamed_copy", "comment_change", "same_template", "independent"} <= relations
    assert len([item for item in pairs if item["template_only"]]) >= 5


def test_pairs_reference_existing_submissions() -> None:
    submissions = {
        item["submission_id"]: item for item in load_jsonl("submissions.jsonl")
    }
    pairs = load_jsonl("pairs.jsonl")

    for item in pairs:
        left = submissions[item["left_submission_id"]]
        right = submissions[item["right_submission_id"]]
        assert left["assignment_id"] == item["assignment_id"]
        assert right["assignment_id"] == item["assignment_id"]
        assert left["student_id"] != right["student_id"]
        assert item["template_only"] == (item["derivation_relation"] == "same_template")


def test_families_do_not_leak_between_setup_and_eval() -> None:
    origins = load_jsonl("origins.jsonl")
    split = json.loads((DATA / "split.json").read_text(encoding="utf-8"))

    assert not set(split["setup_families"]) & set(split["eval_families"])

    family_splits: dict[str, set[str]] = defaultdict(set)
    for item in origins:
        family_splits[item["family_id"]].add(item["split"])

    for family, splits in family_splits.items():
        assert len(splits) == 1, f"family {family} is split across {splits}"

    for item in origins:
        if item["family_id"] in split["setup_families"]:
            assert item["split"] == "setup"
        if item["family_id"] in split["eval_families"]:
            assert item["split"] == "eval"
