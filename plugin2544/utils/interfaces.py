from typing import Protocol as Interface, Union, Dict
from pydantic import BaseModel


class TestSuitePipe(Interface):
    def send_statistics(self, data: Union[Dict, BaseModel]) -> None:
        ...

    def send_warning(self, warning: Exception) -> None:
        ...

    def send_progress(self, current: int, total: int, loop: int=1) -> None:
        ...

class PStateConditions(Interface):
    async def wait_if_paused(self) -> None:
        ...

    async def stop_if_stopped(self) -> None:
        ...
