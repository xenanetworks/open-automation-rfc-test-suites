import asyncio
import json
from config import INPUT_DATA_PATH, JSON_PATH
from pluginlib.plugin3918.conversion.adapter import Converter, model_3918_encoder
from pluginlib.plugin3918.utils  import logger
from valhalla_core import types, controller


async def test():
    with open(INPUT_DATA_PATH) as f:
        d = json.load(f)
        data = Converter(config_data=d).gen()

    with open(JSON_PATH, "w") as f:
        content = data.json(indent=2, encoder=model_3918_encoder)
        f.write(content)

    new = [
        types.Credentials(
            product=types.EProductType.VALKYRIE, host="192.168.1.198", password="xena"
        ),
    ]

    c = await controller.MainController()
    c.register_lib("./pluginlib")
    for t in new:
        await c.add_tester(t)

    with open(JSON_PATH, "r") as f:
        data = json.load(f)
    test_id = c.start_test_suite("RFC-3918", data)
    async for msg in c.listen_changes(test_id):
        print(msg)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(test())
    loop.run_forever()
