from typing import Protocol


class DatabaseHealth(Protocol):
    def is_healthy(self) -> bool: ...
