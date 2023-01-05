from __future__ import annotations
import asyncio
import json
import platform
import pydantic
from xoa_core import types, controller
from xoa_converter.entry import converter
from xoa_converter.types import TestSuiteType
from rich.live import Live
from rich.table import Table
from rich.console import Console
from typing import Dict, List, Any, cast
from pathlib import Path
from loguru import logger


DEBUG = True
BASE_PATH = Path.cwd()
PLUGINS_PATH = BASE_PATH / "pluginlib"
INPUT_DATA_PATH = BASE_PATH / "test" / "2.v3918"
JSON_PATH = BASE_PATH / "test" / "hello.json"
T_SUITE_NAME = "RFC-3918"


class T3918Displayer:
    console = Console()

    @classmethod
    def generate_table(cls, results: Dict) -> List[Table]:
        """Make a new table."""
        all_tables = []
        total_table = Table()
        total_table_row = []
        for k, v in results.items():
            if k not in {"Source Ports", "Destination Ports"}:
                total_table.add_column(k, no_wrap=True)
                total_table_row.append(str(v))
            else:
                for p in v:
                    port_table = Table()
                    port_table_row = []
                    for t, m in p.items():
                        port_table.add_column(t, no_wrap=True)
                        port_table_row.append(str(m))
                    port_table.add_row(*port_table_row)
                    all_tables.append(port_table)

        total_table.add_row(*total_table_row)
        all_tables.append(total_table)

        return all_tables

    @classmethod
    def display(cls, result: Dict) -> None:
        cls.console.clear()
        tables = cls.generate_table(result)
        for table in tables:
            with Live(console=cls.console, screen=False, refresh_per_second=1) as live:
                live.update(table)


def set_windows_loop_policy():
    plat = platform.system().lower()
    if plat == "windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def subscribe(ctrl: controller.MainController, source: str) -> None:
    async for msg in ctrl.listen_changes(source, _filter={types.EMsgType.STATISTICS}):
        # T2544Displayer.display(json.loads(msg.payload.json()))
        print(msg.payload)
        pass


async def start_test(
    ctrl: controller.MainController, config: dict[str, Any], test_suite_name: str
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
        with open(JSON_PATH, "w") as f:
            f.write(new_data)
        config = json.loads(new_data)
        await start_test(c, config, T_SUITE_NAME)


if __name__ == "__main__":
    set_windows_loop_policy()
    asyncio.run(main())
