import asyncio
import json
import os
from xoa_core import types, controller
from loguru import logger
INPUT_DATA_PATH = os.path.abspath(
    "test/2.v2544",
)
INPUT_DATA_PATH = "test/2.v2544"
JSON_PATH = "test/hello.json"

from pluginlib.plugin2544.conversion.adapter import Converter


async def subscribe_executions(c: controller.MainController):
    async for msg in c.listen_changes(types.PIPE_EXECUTOR):
        logger.debug(msg)

async def subscribe(id: str, c: controller.MainController):
    async for msg in c.listen_changes(id):
        # logger.debug(msg)
        logger.debug(msg.json(indent=2))


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
    with open(INPUT_DATA_PATH) as f:
        d = json.load(f)
        data = Converter(config_data=d).gen()
    with open('test/model.txt', 'w') as f:
        f.write(data.config.schema_json(indent=2))
    with open(JSON_PATH, "w") as f:
        f.write(data.json(indent=2))
    c = await controller.MainController()
    c.register_lib("./pluginlib")
    for t in new:
        await c.add_tester(t)

    with open("./test/hello.json", "r") as f:
        data2 = json.load(f)
        # print('@@@@', data2)
    asyncio.create_task(subscribe_executions(c))
    try:
        id = c.start_test_suite("RFC-2544", data2)

    except Exception as err:
        logger.debug(err)
    else:
        asyncio.create_task(subscribe(id, c))
        # await force_sleep(500)
        # await c.running_test_toggle_pause(id)
        # await force_sleep()
        # await c.running_test_toggle_pause(id)
        # await force_sleep()
        # await c.running_test_stop(id)


async def force_sleep(time=60):
    print(f"ready to sleep {time}")
    for i in range(60):
        print(f'sleeping {i}')
        await asyncio.sleep(1)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(playground())
    loop.run_forever()
