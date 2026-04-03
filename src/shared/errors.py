"""Domain errors."""


class VideoJobError(Exception):
    """Recoverable or fatal pipeline error."""

    def __init__(self, message: str, *, fatal: bool = True) -> None:
        super().__init__(message)
        self.fatal = fatal
