import asyncio
import json
from config import INPUT_DATA_PATH, JSON_PATH
from xoa_core import types, controller
from pluginlib.plugin3918 import Model3918
from pluginlib.plugin3918.utils.constants import PayloadType
from xoa_converter.entry import converter
from xoa_converter.types import TestSuiteType


async def test():
    new = [
        types.Credentials(
            product=types.EProductType.VALKYRIE, host="192.168.1.198", password="xena"
        ),
    ]

    c = await controller.MainController()
    c.register_lib("./pluginlib")
    for t in new:
        await c.add_tester(t)

    with open(INPUT_DATA_PATH, "r") as f:
        app_data = f.read()
        info = c.get_test_suite_info("RFC-3918")
        new_data = converter(TestSuiteType.RFC3918, app_data, info["schema"])
    test_id = c.start_test_suite(
        "RFC-3918", json.loads(new_data), debug_connection=False
    )
    # async for msg in c.listen_changes(test_id):
    #     print(msg)


def s():
    with open('1.json', "r") as f:
        obj = json.load(f)
    print(Model3918.parse_obj(obj))

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(test())
    loop.run_forever()
    # s()
