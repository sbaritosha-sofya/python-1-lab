class SubmissionError(Exception):
    """Базовое доменное исключение."""


class SubmissionValidationError(SubmissionError):
    """Ошибка валидации одной сдачи.

    Атрибуты:
        code: категория ошибки (format, schema, conflict).
        field: имя поля, к которому относится ошибка; пустая строка, если ошибка
               не привязана к конкретному полю.
        message: человекочитаемое пояснение.
    """

    def __init__(self, code: str, field: str, message: str) -> None:
        self.code = code
        self.field = field
        self.message = message
        super().__init__(f"[{code}] {field}: {message}")
