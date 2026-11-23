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

---

# Отчёт по лабораторной работе 2, этап А

## Траектория и уровень

- **Траектория:** Python Core (основной вариант).
- **Этап:** А — потоковый baseline и второй метод сравнения.
- **Вход:** результаты ЛР1 плюс учебный корпус `data/corpus`.

## Выполненные требования

- [x] Ленивый конвейер `FeatureStream`: чтение JSONL через итератор, проверка
      уже выполнена `JSONLSource`/парсером, признаки строятся по одной сдаче.
- [x] Признаки через `tokenize`: комментарии и служебные токены исключены,
      строки разрешённого шаблона отмечены отдельно.
- [x] Множества троек подряд идущих токенов и мера Jaccard
      (`|пересечение| / |объединение|`).
- [x] Пустое объединение возвращает `status=insufficient_data`, `score=null`.
- [x] Сравниваются только разные студенты одного задания; self-match и чужие
      задания исключены, повторные версии студента вынесены в
      `same_student_revisions`.
- [x] Для пары сохраняются диапазоны исходных строк; evidence проверяется на
      попадание в существующие строки.
- [x] Второй метод `ast-normalized`: имена нормализуются по порядку первого
      появления, структуры сравниваются; при `SyntaxError` возвращается
      понятная ошибка.
- [x] Пара, где все общие признаки — разрешённый шаблон, помечается
      `template_only` с пояснением, а не выдаётся за нарушение.
- [x] Корпус расширен до 33 сдач и 45 размеченных пар, есть происхождение,
      `assignment_id`, `family_id`, 10 пар с разрешённым шаблоном.
- [x] Семейства целиком разделены между `setup` и `eval`.
- [x] Добавлена команда `find-similar` с top-k и оценкой размера индекса.

## Команды проверки

```bash
cd /home/sofya/python
source .venv/bin/activate
pytest -q
python tools/build_corpus.py
python -m school_submissions find-similar data/corpus/submissions.jsonl \
  --assignment data/corpus/lab-sort.assignment.json --method token-3gram --top-k 5
python -m school_submissions find-similar data/corpus/submissions.jsonl \
  --assignment data/corpus/lab-sort.assignment.json --method ast-normalized --top-k 5
```

## Наблюдения по корпусу

- Точная копия и изменённое форматирование дают `score=1.0` у токенного метода.
- Переименование переменных снижает токенное сходство, но AST-метод сохраняет
  `score=1.0` и `structure_equal=true`.
- Пары из семейства `sort-template` получают `status=template_only`: совпадение
  объяснено разрешённым шаблоном.
- Для 27 сдач `lab-sort` оценка индекса: около 23 КБ для токенов, 30 КБ для AST.
- 52 теста проходят, включая проверки корпуса и отсутствия утечки семейств.

## Известные ограничения

- Корпус синтетический; метрики качества на нём учебные.
- AST-нормализация не трогает имена атрибутов и константы.
- Полный индекс top-k хранит признаки всех сдач в памяти; потоковое чтение
  снижает пиковую память на этапе чтения, но не делает индекс константным.
- Порог `review_required`, матрица ошибок, precision/recall/F1 и замеры
  производительности относятся к этапу Б и здесь не заявляются.
