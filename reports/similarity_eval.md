# Результаты оценки сходства

## Корпус

- Сдач: 33
- Пар: 41
- Пар с шаблоном: 10
- Задания: lab-counter, lab-sort
- Проверка утечки семейств: ok

## Сравнение методов

| метод | порог | TP | FP | TN | FN | precision | recall | F1 | неопр. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| token-3gram | 0.610 | 9 | 10 | 3 | 4 | 0.474 | 0.692 | 0.562 | 0 (0.000) |
| ast-normalized | 0.650 | 13 | 10 | 3 | 0 | 0.565 | 1.000 | 0.722 | 0 (0.000) |

## Eval без шаблонных пар

| метод | TP | FP | TN | FN | precision | recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| token-3gram | 9 | 0 | 3 | 4 | 1.000 | 0.692 | 0.818 |
| ast-normalized | 13 | 0 | 3 | 0 | 1.000 | 1.000 | 1.000 |

## Выбор порога на setup

- `token-3gram`: порог 0.610, F1 на setup 0.800, precision 1.000, recall 0.667; критерий: max_f0_5_then_balanced_accuracy_then_margin.
- `ast-normalized`: порог 0.650, F1 на setup 1.000, precision 1.000, recall 1.000; критерий: max_f0_5_then_balanced_accuracy_then_margin.

## Срез по отношениям на eval

### token-3gram

| отношение | пар | попало в review | неопределённых | средний score |
|---|---:|---:|---:|---:|
| exact_copy | 3 | 3 | 0 | 1.000 |
| independent | 3 | 0 | 0 | 0.150 |
| reformatted_copy | 6 | 6 | 0 | 1.000 |
| renamed_copy | 4 | 0 | 0 | 0.119 |
| same_template | 10 | 10 | 0 | 1.000 |

Шаблонные пары: 10, попали в review 10 (1.000), объяснены как `template_only`: 10.

### ast-normalized

| отношение | пар | попало в review | неопределённых | средний score |
|---|---:|---:|---:|---:|
| exact_copy | 3 | 3 | 0 | 1.000 |
| independent | 3 | 0 | 0 | 0.087 |
| reformatted_copy | 6 | 6 | 0 | 1.000 |
| renamed_copy | 4 | 4 | 0 | 1.000 |
| same_template | 10 | 10 | 0 | 1.000 |

Шаблонные пары: 10, попали в review 10 (1.000), объяснены как `template_only`: 10.

## Согласие методов на eval

- Оба отметили: 19
- Только token-3gram: 0
- Только ast-normalized: 4
- Ни один: 3

## Разбор ошибок

### 1. template_false_positive (token-3gram)

- Пара: `s23` / `s24`
- Отношение: `same_template`, шаблон: True
- Score: 1.000, порог: 0.610, review_required: True
- Объяснение: Совпадение целиком объяснено разрешённым шаблоном: пара попала в review_required из-за высокого сходства, но это не доказательство нарушения.

Evidence:
- `1-1` ↔ `1-1`: `( items )`
- `1-2` ↔ `1-2`: `) : return`
- `1-2` ↔ `1-2`: `: return sorted`

### 2. template_false_positive (ast-normalized)

- Пара: `s23` / `s24`
- Отношение: `same_template`, шаблон: True
- Score: 1.000, порог: 0.650, review_required: True
- Объяснение: Совпадение целиком объяснено разрешённым шаблоном: пара попала в review_required из-за высокого сходства, но это не доказательство нарушения.

Evidence:
- `2-2` ↔ `2-2`: `Call Name:id2 Load`
- `1-2` ↔ `1-2`: `FunctionDef:id0 arguments arg:id1`
- `2-2` ↔ `2-2`: `Load Name:id1 Load`

### 3. false_negative (token-3gram)

- Пара: `s13` / `s15`
- Отношение: `renamed_copy`, шаблон: False
- Score: 0.111, порог: 0.610, review_required: False
- Объяснение: token-3gram: переименование переменных снизило сходство ниже порога; именно такой случай должен ловить структурный метод.

Evidence:
- `5-6` ↔ `5-6`: `) return sorted`
- `5-5` ↔ `5-5`: `. append (`
- `2-2` ↔ `2-2`: `= [ ]`

### 4. false_negative (token-3gram)

- Пара: `s15` / `s16`
- Отношение: `renamed_copy`, шаблон: False
- Score: 0.111, порог: 0.610, review_required: False
- Объяснение: token-3gram: переименование переменных снизило сходство ниже порога; именно такой случай должен ловить структурный метод.

Evidence:
- `5-6` ↔ `8-10`: `) return sorted`
- `5-5` ↔ `8-8`: `. append (`
- `2-2` ↔ `3-3`: `= [ ]`

## Ограничения

- Корпус синтетический и малый; метрики не переносятся на реальных студентов.
- Порог выбран на setup, метрики посчитаны на eval без повторной настройки.
- `review_required` означает необходимость ручного разбора, а не нарушение.
- Общий шаблон даёт высокий score и объясняется отдельно через `template_only`.

