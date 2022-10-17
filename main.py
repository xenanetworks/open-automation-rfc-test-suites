import asyncio
import json
import platform
import pydantic
from pathlib import Path
from typing import Any, cast, Dict
from xoa_core import types, controller
from loguru import logger
import sys

sys.path.append("D:/Working/open-automation-config-converter")

from xoa_converter.entry import converter
from xoa_converter.types import TestSuiteType


DEBUG = True
BASE_PATH = Path.cwd()
PLUGINS_PATH = BASE_PATH / "pluginlib"
INPUT_DATA_PATH = BASE_PATH / "test" / "2.v2544"
JSON_PATH = BASE_PATH / "test" / "hello.json"
T_SUITE_NAME = "RFC-2544"


def set_windows_loop_policy():
    plat = platform.system().lower()

    if plat == "windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def subscribe(ctrl: controller.MainController, source: str) -> None:
    async for msg in ctrl.listen_changes(source):
        logger.debug(msg.json())


async def start_test(
    ctrl: controller.MainController, config: Dict[str, Any], test_suite_name: str
) -> None:
    exec_id = ctrl.start_test_suite(test_suite_name, config, debug_connection=DEBUG)
    await subscribe(ctrl, exec_id)


async def main() -> None:
    new = [
        types.Credentials(
            product=types.EProductType.VALKYRIE,
            host="192.168.1.198",
            password=cast(pydantic.SecretStr, "xena"),
        ),
    ]
    c = await controller.MainController()
    c.register_lib(str(PLUGINS_PATH))

    await asyncio.gather(*[c.add_tester(t) for t in new])
    asyncio.create_task(subscribe(c, types.PIPE_EXECUTOR))

    with open(INPUT_DATA_PATH) as f:
        app_data = f.read()
        info = c.get_test_suite_info(T_SUITE_NAME)
        if not info:
            logger.error("Test suite is not recognised.")
            return None
        new_data = converter(TestSuiteType(T_SUITE_NAME), app_data, info["schema"])
        config = json.loads(new_data)
        await start_test(c, config, T_SUITE_NAME)


if __name__ == "__main__":
    set_windows_loop_policy()
    asyncio.run(main())
