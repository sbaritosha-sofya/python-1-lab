class SubmissionError(Exception):
    pass


class SubmissionValidationError(SubmissionError):
    def __init__(self, code: str, field: str, message: str) -> None:
        self.code = code
        self.field = field
        self.message = message
        super().__init__(f"[{code}] {field}: {message}")
