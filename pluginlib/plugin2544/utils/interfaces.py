from typing import Any, Protocol


class TestSuitePipe(Protocol):
    def send_statistics(self, v: Any) -> None:
        ...

    def send_warning(self, v: Any) -> None:
        ...