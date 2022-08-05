import asyncio
import json
import os
from xoa_core import types, controller
from loguru import logger

from xoa_converter.entry import converter
from xoa_converter.types import TestSuiteType

INPUT_DATA_PATH = os.path.abspath("test/2.v2544")
JSON_PATH = os.path.abspath("test/hello.json")


async def subscribe_executions(c: controller.MainController):
    async for msg in c.listen_changes(types.PIPE_EXECUTOR):
        logger.debug(msg)


async def subscribe(id: str, c: controller.MainController):
    async for msg in c.listen_changes(id):
        logger.debug(msg)


async def playground():
    new = [
        # types.Credentials( product=types.EProductType.VALKYRIE, host="87.61.110.114", password="xena"),
        types.Credentials(
            product=types.EProductType.VALKYRIE, host="192.168.1.198", password="xena"
        ),  # wrong password
        types.Credentials(
            product=types.EProductType.VALKYRIE, host="192.168.1.197", password="xena"
        ),  # tester is turned off
        # types.Credentials( product=types.EProductType.VALKYRIE, host="87.61.110.118", password="xena"),
    ]
    c = await controller.MainController()
    c.register_lib("./pluginlib")
    for t in new:
        await c.add_tester(t)

    with open(INPUT_DATA_PATH) as f:
        app_data = f.read()
        info = c.get_test_suite_info("RFC-2544")
        new_data = converter(TestSuiteType.RFC2544,  app_data, info["schema"])

    asyncio.create_task(subscribe_executions(c))
    try:
        id = c.start_test_suite("RFC-2544", json.loads(new_data))
    except Exception as err:
        logger.debug(err)
    else:
        asyncio.create_task(subscribe(id, c))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(playground())
    loop.run_forever()
