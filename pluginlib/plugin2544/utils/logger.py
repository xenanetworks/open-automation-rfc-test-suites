import sys
from loguru import logger
import typing

FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} {message}"

FILE_PATH_FORMAT = "{time:HH:mm:ss.SSS} | <level>{level: <8}</level> | <cyan>{file.path}:{line:}</cyan> <green>{function}</green> | {message}"

__all__ = ("logger",)


class TestSuitePipe(typing.Protocol):
    # def send_data(self, data: typing.Union[typing.Dict, "BaseModel"]) -> None: ...
    def send_statistics(self, data) -> None:
        ...

    def send_progress(self, progress: int) -> None:
        ...

    def send_warning(self, worning: Exception) -> None:
        ...

    def send_error(self, error: Exception) -> None:
        ...


logger.remove()


logger.add(
    sink="log/valhalla_core_request.log",
    format=FORMAT,
    level="DEBUG",
    encoding="utf-8",
    mode="w",
    filter=lambda x: "->" in x["message"],
)
logger.add(
    sink="log/valhalla_core_response.log",
    format=FORMAT,
    level="DEBUG",
    encoding="utf-8",
    mode="w",
    filter=lambda x: "<-" in x["message"],
)
logger.add(
    sink="log/valhalla_core_push_notification.log",
    format=FORMAT,
    level="DEBUG",
    encoding="utf-8",
    mode="w",
    filter=lambda x: "-P" in x["message"],
)
logger.add(
    sink="log/core-debug.log",
    format=FORMAT,
    level="DEBUG",
    mode="w",
    encoding="utf-8",
)
logger.add(
    sink="log/core-info.log",
    format=FORMAT,
    level="INFO",
    mode="w",
    encoding="utf-8",
)
logger.add(
    sink="log/core-warning.log",
    format=FORMAT,
    level="WARNING",
    mode="w",
    encoding="utf-8",
)
logger.add(
    sink="log/core-error.log",
    format=FORMAT,
    level="ERROR",
    mode="w",
    encoding="utf-8",
)
logger.add(
    sink="log/message_pool.log",
    format=FORMAT,
    level="DEBUG",
    mode="w",
    encoding="utf-8",
    filter=lambda x: "message_handler" in x["module"],
)


logger.add(sys.stdout, colorize=True, level="DEBUG", format=FILE_PATH_FORMAT)
