from typing import Protocol as Interface, Union, Dict
from pydantic import BaseModel


class TestSuitePipe(Interface):
    def send_statistics(self, data: Union[Dict, BaseModel]) -> None:
        ...

    def send_warning(self, warning: Exception) -> None:
        ...
