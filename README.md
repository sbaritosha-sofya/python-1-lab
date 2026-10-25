# Лабораторная работа 1: приём, валидация и анализ сдач

Основа системы онлайн-школы, которая принимает версии сдач лабораторных работ, валидирует их и запускает заменяемые анализаторы.

## Установка

```bash
cd /home/sofya/python
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

### Запуск анализатора

```bash
python -m school_submissions analyze --assignment data/assignments.json --analyzer length data/submissions.jsonl
python -m school_submissions analyze --assignment data/assignments.json --analyzer template data/submissions.jsonl
```

Если `--analyzer` не указан, запускаются все зарегистрированные анализаторы.

## Архитектура

- **Модель** — неизменяемый `Submission` с вычисляемым `content_hash` и `Assignment`.
- **Парсер** — преобразует сырой JSON в модель и не модифицирует вход.
- **Сервис приёма** — отличает `accepted`, `duplicate` и `conflict` по хешу.
- **Репозиторий** — in-memory хранилище сдач.
- **Источники** — `JSONLSource` (контекстный менеджер) и `InMemorySource`, реализующие `Source` Protocol.
- **Анализаторы** — `LengthAnalyzer` и `TemplateAnalyzer`, реализующие `Analyzer` Protocol.
- **Реестр** — `AnalyzerRegistry` хранит фабрики анализаторов по идентификатору.
- **Сервис анализа** — выбирает анализатор из реестра без ветвления по классам.
- **CLI** — читает JSONL, повреждённая строка не останавливает обработку.
- **Доменный слой** не читает stdin и не обращается к HTTP.

## Протокол vs наследование

`Analyzer` и `Source` объявлены как `Protocol`: любой класс с нужными методами и атрибутами подходит в качестве реализации, не требуя явного наследования. Это даёт слабую связанность и позволяет легко подменять реализации в тестах и расширять систему новыми анализаторами без изменения центрального сервиса.
