import asyncio
import json
from config import INPUT_DATA_PATH, JSON_PATH

from plugin2544.conversion.adapter import Converter
from plugin2544.plugin import TestSuit2544
from plugin2544 import function_factory
import os


async def test():
    try:
        with open(INPUT_DATA_PATH) as f:
            d = json.load(f)
            data = Converter(config_data=d).gen()
        with open(JSON_PATH, "w") as f:
            f.write(data.json(indent=2))
        await TestSuit2544(function_factory, data).start()
    except Exception as e:
        print(e)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(test())
    loop.run_forever()
