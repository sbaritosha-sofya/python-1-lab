# Лабораторная работа 1, этап А: приём и валидация сдач

Основа системы онлайн-школы, которая принимает версии сдач лабораторных работ и валидирует их.

## Установка

```bash
cd /home/sofya/lab1_online_school
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest
```

## Использование

### Импорт сдач

```bash
python -m school_submissions import data/submissions.jsonl
school-submissions import data/submissions.jsonl
```

Вывод — JSON с полями `accepted`, `duplicates`, `conflicts`, `errors`.

## Архитектура

- **Модель** — неизменяемый `Submission` с вычисляемым `content_hash`.
- **Парсер** — преобразует сырой JSON в модель и не модифицирует вход.
- **Сервис приёма** — отличает `accepted`, `duplicate` и `conflict` по хешу.
- **Репозиторий** — in-memory хранилище сдач.
- **CLI** — читает JSONL, повреждённая строка не останавливает обработку.
- **Доменный слой** не читает stdin и не обращается к HTTP.

