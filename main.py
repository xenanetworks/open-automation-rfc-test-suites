import asyncio
import json
from valhalla_core import types, controller

INPUT_DATA_PATH = "test/2.v2544"
JSON_PATH = "test/hello.json"

from pluginlib.plugin2544.conversion.adapter import Converter


async def playground():
    new = [
        # types.Credentials( product=types.EProductType.VALKYRIE, host="87.61.110.114", password="xena"),
        # types.Credentials( product=types.EProductType.VALKYRIE, host="192.168.1.198", password="xena"), # wrong password
        types.Credentials(
            product=types.EProductType.VALKYRIE, host="192.168.1.197", password="xena"
        ),  # tester is turned off
        # types.Credentials( product=types.EProductType.VALKYRIE, host="87.61.110.118", password="xena"),
    ]
    with open(INPUT_DATA_PATH) as f:
        d = json.load(f)
        data = Converter(config_data=d).gen()
    with open(JSON_PATH, "w") as f:
        f.write(data.json(indent=2))
    c = await controller.MainController()
    c.register_lib("./pluginlib")
    # for t in new:
    #     await c.add_tester(t)

    with open("./test/hello.json", "r") as f:
        data = json.load(f)
    print(c.get_avaliable_test_suites())

    id = c.start_test_suite("RFC-2544", data)
    async for msg in c.listen_changes(id, _filter={types.EMsgType.STATISTICS}):
        print(msg)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(playground())
    loop.run_forever()
