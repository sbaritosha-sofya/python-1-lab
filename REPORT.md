# Отчёт по лабораторной работе 1, этап А

## Выбранная траектория и уровень

- **Траектория:** Python Core (основной вариант).
- Этап А: приём и валидация сдач.

## Выполненные требования

- [x] Пакет в `src`-layout (`src/school_submissions`).
- [x] `Submission` на `dataclass` с неизменяемыми полями и `content_hash`.
- [x] Разбор JSON и валидация обязательных полей, типов, временной зоны,
      AI-декларации, неизвестных полей.
- [x] Доменные исключения с `code`, `field`, `message`.
- [x] In-memory репозиторий, различие дубликата и конфликта по хешу.
- [x] CLI `import`, который не останавливается на повреждённой строке.
- [x] Публичные функции аннотированы; доменный слой не читает stdin/HTTP.

## Команды проверки

```bash
cd /home/sofya/lab1_online_school
source .venv/bin/activate
pytest -q
python -m school_submissions import data/submissions.jsonl
python -m school_submissions import data/invalid_submissions.jsonl
```
