# Отчёт по лабораторной работе 1

## Выбранная траектория и уровень

- **Траектория:** Python Core (основной вариант).
- **Этап А:** приём и валидация сдач.
- **Этап Б:** контракты и расширения.

## Выполненные требования

### Этап А

- [x] Пакет в `src`-layout (`src/school_submissions`).
- [x] `Submission` на `dataclass` с неизменяемыми полями и `content_hash`.
- [x] Разбор JSON и валидация обязательных полей, типов, временной зоны,
      AI-декларации, неизвестных полей.
- [x] Доменные исключения с `code`, `field`, `message`.
- [x] In-memory репозиторий, различие дубликата и конфликта по хешу.
- [x] CLI `import`, который не останавливается на повреждённой строке.
- [x] Публичные функции аннотированы; доменный слой не читает stdin/HTTP.

### Этап Б

- [x] `Analyzer` Protocol: `analyze(submission, context)` возвращает `AnalysisReport`.
- [x] `AnalysisContext` передаёт требования `Assignment`.
- [x] `AnalysisReport` включает `analyzer_id` и `analyzer_version`.
- [x] `LengthAnalyzer`: считает непустые строки текста и кода, `score=None`, пояснение в `rubric_feedback`.
- [x] `TemplateAnalyzer`: находит точные строки разрешённого шаблона, возвращает `similarity`/`score` и пояснение, что совпадение разрешено; номера строк `evidence` относятся к исходному содержимому.
- [x] `JSONLSource` и `InMemorySource`; один набор контрактных тестов проверяет оба источника и оба анализатора.
- [x] Центральный сервис `AnalysisService` выбирает анализатор по реестру и не содержит ветвления по классам.
- [x] Контекстный менеджер для файлового источника; файл закрывается при ошибке и досрочном `break`.
- [x] Объяснено различие между протоколом и наследованием в `README.md`.

## Команды проверки

```bash
cd /home/sofya/python
source .venv/bin/activate
pytest -q
python -m school_submissions import data/submissions.jsonl
python -m school_submissions import data/invalid_submissions.jsonl
python -m school_submissions analyze --assignment data/assignments.json --analyzer length data/submissions.jsonl
python -m school_submissions analyze --assignment data/assignments.json --analyzer template data/submissions.jsonl
```

## Известные ограничения

- Репозиторий остаётся in-memory.
- Анализаторы синхронные.
- Подключение третьего анализатора на защите не требует изменения центрального сервиса: достаточно зарегистрировать его в реестре.
