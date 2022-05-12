from typing import Any


class BXMPWarning:
    def __init__(self, para: str, value: Any, port: Any, feature: str) -> None:
        self.str = f"<{para}> can only be set to {value} since port {port} does not support '{feature}' feature!"

    def __repr__(self) -> str:
        return self.str

    def __str__(self) -> str:
        return self.str

class ConfigError(Exception):
    pass


class NotSupportL47Tester(Exception):
    def __init__(self) -> None:
        self.msg = "Not Support L47Tester"
        super().__init__(self.msg)
