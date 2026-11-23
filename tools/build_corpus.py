from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "corpus"
CREATED_AT = "2026-11-01T10:00:00+03:00"

SUBMISSIONS: list[dict[str, Any]] = []
ORIGINS: list[dict[str, Any]] = []


def add(
    submission_id: str,
    assignment_id: str,
    student_id: str,
    code: str,
    family_id: str,
    variant: str,
    split: str,
    source_submission_id: str | None = None,
) -> None:
    SUBMISSIONS.append(
        {
            "submission_id": submission_id,
            "assignment_id": assignment_id,
            "student_id": student_id,
            "text": f"Решение задания {assignment_id}",
            "code": code,
            "used_ai": False,
            "ai_declaration": "",
            "timestamp": CREATED_AT,
        }
    )
    ORIGINS.append(
        {
            "submission_id": submission_id,
            "assignment_id": assignment_id,
            "student_id": student_id,
            "family_id": family_id,
            "variant": variant,
            "split": split,
            "source_submission_id": source_submission_id,
        }
    )


SORT_A_ORIGINAL = """def solve(items):
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    result.sort()
    return result
"""

SORT_A_REFORMATTED = """def solve( items ):

    result = [ ]

    for item in items :

        if item not in result :
            result . append( item )

    result . sort( )
    return result
"""

SORT_A_RENAMED = """def solve(values):
    unique = []
    for value in values:
        if value not in unique:
            unique.append(value)
    unique.sort()
    return unique
"""

SORT_A_COMMENTS = """# Сначала убираем повторы, потом сортируем.
def solve(items):
    result = []
    for item in items:  # проходим по исходному списку
        if item not in result:
            result.append(item)
    result.sort()
    return result
"""

SORT_B_ORIGINAL = """def solve(numbers):
    seen = set()
    ordered = []
    for number in numbers:
        if number in seen:
            continue
        seen.add(number)
        ordered.append(number)
    return sorted(ordered)
"""

SORT_B_REFORMATTED = """def solve( numbers ):

    seen = set( )
    ordered = [ ]

    for number in numbers :

        if number in seen :
            continue

        seen . add( number )
        ordered . append( number )

    return sorted( ordered )
"""

SORT_B_RENAMED = """def solve(values):
    visited = set()
    result = []
    for value in values:
        if value in visited:
            continue
        visited.add(value)
        result.append(value)
    return sorted(result)
"""

SORT_C_ORIGINAL = """def solve(items):
    return sorted(set(items))
"""

SORT_C_COMMENTS = """# set убирает повторы, sorted возвращает порядок.
def solve(items):
    return sorted(set(items))  # короткое решение
"""

SORT_D_ORIGINAL = """def solve(data):
    output = []
    for value in data:
        if value not in output:
            output.append(value)
    return sorted(output)
"""

SORT_D_REFORMATTED = """def solve( data ):

    output = [ ]

    for value in data :

        if value not in output :
            output . append( value )

    return sorted( output )
"""

SORT_D_RENAMED = """def solve(items):
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return sorted(result)
"""

TEMPLATE_CODE = """def solve(items):
    return sorted(items)
"""

SORT_INDEPENDENT = {
    "s17": """def solve(items):
    unique = list(dict.fromkeys(items))
    return sorted(unique)
""",
    "s18": """def solve(items):
    return sorted(item for item in set(items))
""",
    "s19": """def solve(items):
    result = list(set(items))
    result.sort()
    return result
""",
    "s20": """def solve(items):
    return sorted({value for value in items})
""",
    "s21": """def solve(items):
    unique_items = []
    for value in items:
        if value not in unique_items:
            unique_items.append(value)
    unique_items.sort()
    return unique_items
""",
    "s22": """def solve(items):
    return sorted(items) if len(set(items)) == len(items) else sorted(set(items))
""",
}

COUNTER_E_ORIGINAL = """def count_chars(text):
    counts = {}
    for char in text:
        counts[char] = counts.get(char, 0) + 1
    return counts
"""

COUNTER_E_RENAMED = """def count_chars(source):
    result = {}
    for symbol in source:
        result[symbol] = result.get(symbol, 0) + 1
    return result
"""

COUNTER_F_ORIGINAL = """def count_chars(text):
    result = {}
    for symbol in text:
        if symbol in result:
            result[symbol] += 1
        else:
            result[symbol] = 1
    return result
"""

COUNTER_F_REFORMATTED = """def count_chars( text ):

    result = { }

    for symbol in text :

        if symbol in result :
            result[ symbol ] += 1
        else :
            result[ symbol ] = 1

    return result
"""


add("s01", "lab-sort", "student-s01", SORT_A_ORIGINAL, "sort-a", "original", "setup")
add("s02", "lab-sort", "student-s02", SORT_A_ORIGINAL, "sort-a", "exact_copy", "setup", "s01")
add("s03", "lab-sort", "student-s03", SORT_A_REFORMATTED, "sort-a", "reformatted_copy", "setup", "s01")
add("s04", "lab-sort", "student-s04", SORT_A_RENAMED, "sort-a", "renamed_copy", "setup", "s01")
add("s05", "lab-sort", "student-s05", SORT_A_COMMENTS, "sort-a", "comment_change", "setup", "s01")

add("s06", "lab-sort", "student-s06", SORT_B_ORIGINAL, "sort-b", "original", "eval")
add("s07", "lab-sort", "student-s07", SORT_B_ORIGINAL, "sort-b", "exact_copy", "eval", "s06")
add("s08", "lab-sort", "student-s08", SORT_B_RENAMED, "sort-b", "renamed_copy", "eval", "s06")
add("s09", "lab-sort", "student-s09", SORT_B_REFORMATTED, "sort-b", "reformatted_copy", "eval", "s06")

add("s10", "lab-sort", "student-s10", SORT_C_ORIGINAL, "sort-c", "original", "setup")
add("s11", "lab-sort", "student-s11", SORT_C_ORIGINAL, "sort-c", "exact_copy", "setup", "s10")
add("s12", "lab-sort", "student-s12", SORT_C_COMMENTS, "sort-c", "comment_change", "setup", "s10")

add("s13", "lab-sort", "student-s13", SORT_D_ORIGINAL, "sort-d", "original", "eval")
add("s14", "lab-sort", "student-s14", SORT_D_ORIGINAL, "sort-d", "exact_copy", "eval", "s13")
add("s15", "lab-sort", "student-s15", SORT_D_RENAMED, "sort-d", "renamed_copy", "eval", "s13")
add("s16", "lab-sort", "student-s16", SORT_D_REFORMATTED, "sort-d", "reformatted_copy", "eval", "s13")

for index, submission_id in enumerate(["s17", "s18", "s19", "s20", "s21", "s22"]):
    split = "setup" if index < 3 else "eval"
    add(
        submission_id,
        "lab-sort",
        f"student-{submission_id}",
        SORT_INDEPENDENT[submission_id],
        f"sort-independent-{submission_id}",
        "independent",
        split,
    )

for index in range(5):
    submission_id = f"s{23 + index}"
    add(
        submission_id,
        "lab-sort",
        f"student-{submission_id}",
        TEMPLATE_CODE,
        "sort-template",
        "template",
        "eval",
    )

add("e01", "lab-counter", "student-e01", COUNTER_E_ORIGINAL, "counter-e", "original", "setup")
add("e02", "lab-counter", "student-e02", COUNTER_E_ORIGINAL, "counter-e", "exact_copy", "setup", "e01")
add("e03", "lab-counter", "student-e03", COUNTER_E_RENAMED, "counter-e", "renamed_copy", "setup", "e01")
add("e04", "lab-counter", "student-e04", COUNTER_F_ORIGINAL, "counter-f", "original", "eval")
add("e05", "lab-counter", "student-e05", COUNTER_F_ORIGINAL, "counter-f", "exact_copy", "eval", "e04")
add("e06", "lab-counter", "student-e06", COUNTER_F_REFORMATTED, "counter-f", "reformatted_copy", "eval", "e04")

PAIRS: list[dict[str, Any]] = []
_pair_counter = 0


def pair(
    left: str,
    right: str,
    assignment_id: str,
    family_id: str,
    derivation_relation: str,
    template_only: bool = False,
) -> None:
    global _pair_counter
    _pair_counter += 1
    PAIRS.append(
        {
            "pair_id": f"pair-{_pair_counter:03d}",
            "left_submission_id": left,
            "right_submission_id": right,
            "assignment_id": assignment_id,
            "family_id": family_id,
            "derivation_relation": derivation_relation,
            "template_only": template_only,
        }
    )


pair("s01", "s02", "lab-sort", "sort-a", "exact_copy")
pair("s01", "s03", "lab-sort", "sort-a", "reformatted_copy")
pair("s01", "s04", "lab-sort", "sort-a", "renamed_copy")
pair("s01", "s05", "lab-sort", "sort-a", "comment_change")
pair("s02", "s03", "lab-sort", "sort-a", "reformatted_copy")
pair("s03", "s04", "lab-sort", "sort-a", "renamed_copy")

pair("s06", "s07", "lab-sort", "sort-b", "exact_copy")
pair("s06", "s08", "lab-sort", "sort-b", "renamed_copy")
pair("s06", "s09", "lab-sort", "sort-b", "reformatted_copy")
pair("s07", "s09", "lab-sort", "sort-b", "reformatted_copy")
pair("s08", "s09", "lab-sort", "sort-b", "renamed_copy")

pair("s10", "s11", "lab-sort", "sort-c", "exact_copy")
pair("s10", "s12", "lab-sort", "sort-c", "comment_change")
pair("s11", "s12", "lab-sort", "sort-c", "comment_change")

pair("s13", "s14", "lab-sort", "sort-d", "exact_copy")
pair("s13", "s15", "lab-sort", "sort-d", "renamed_copy")
pair("s13", "s16", "lab-sort", "sort-d", "reformatted_copy")
pair("s14", "s16", "lab-sort", "sort-d", "reformatted_copy")
pair("s15", "s16", "lab-sort", "sort-d", "renamed_copy")

template_teams = ["s23", "s24", "s25", "s26", "s27"]
for left_index, left in enumerate(template_teams):
    for right in template_teams[left_index + 1 :]:
        pair(left, right, "lab-sort", "sort-template", "same_template", template_only=True)

independent_pairs = [
    ("s17", "s18"),
    ("s17", "s19"),
    ("s17", "s20"),
    ("s18", "s19"),
    ("s18", "s20"),
    ("s19", "s20"),
    ("s20", "s21"),
    ("s21", "s22"),
    ("s17", "s22"),
    ("s18", "s22"),
]
for left, right in independent_pairs:
    pair(left, right, "lab-sort", "sort-independent", "independent")

pair("e01", "e02", "lab-counter", "counter-e", "exact_copy")
pair("e01", "e03", "lab-counter", "counter-e", "renamed_copy")
pair("e02", "e03", "lab-counter", "counter-e", "renamed_copy")

pair("e04", "e05", "lab-counter", "counter-f", "exact_copy")
pair("e04", "e06", "lab-counter", "counter-f", "reformatted_copy")
pair("e05", "e06", "lab-counter", "counter-f", "reformatted_copy")

ASSIGNMENTS = {
    "lab-sort": {
        "assignment_id": "lab-sort",
        "name": "Сортировка уникальных значений",
        "description": "Вернуть отсортированный список без повторов.",
        "allowed_templates": ["def solve(items):", "return sorted(items)"],
    },
    "lab-counter": {
        "assignment_id": "lab-counter",
        "name": "Подсчёт символов",
        "description": "Вернуть частоты символов в строке.",
        "allowed_templates": [],
    },
}

SPLIT = {
    "setup_families": ["sort-a", "sort-c", "counter-e"],
    "eval_families": ["sort-b", "sort-d", "sort-template", "counter-f"],
    "setup_submissions": ["s17", "s18", "s19"],
    "eval_submissions": ["s20", "s21", "s22"],
}


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(DATA_DIR / "submissions.jsonl", SUBMISSIONS)
    write_jsonl(DATA_DIR / "origins.jsonl", ORIGINS)
    write_jsonl(DATA_DIR / "pairs.jsonl", PAIRS)
    for assignment_id, payload in ASSIGNMENTS.items():
        (DATA_DIR / f"{assignment_id}.assignment.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    (DATA_DIR / "split.json").write_text(
        json.dumps(SPLIT, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"submissions={len(SUBMISSIONS)} origins={len(ORIGINS)} pairs={len(PAIRS)}"
    )


if __name__ == "__main__":
    main()
