import asyncio
import json
import platform
import pydantic
from pathlib import Path
from typing import Any, cast, Dict
from loguru import logger
from math import ceil
from xoa_converter.entry import converter
from xoa_converter.types import TestSuiteType
from xoa_core import types, controller

DEBUG = False
BASE_PATH = Path.cwd()
PLUGINS_PATH = BASE_PATH / "pluginlib"
INPUT_DATA_PATH = BASE_PATH / "test" / "2.v2544"
JSON_PATH = BASE_PATH / "test" / "hello.json"
T_SUITE_NAME = "RFC-2544"

from rich.live import Live
from rich.table import Table
from rich.console import Console
from pydantic import SecretStr
from typing import Dict, List


class T2544Displayer:
    console = Console()
    separate = 5

    @classmethod
    def assign_table(
        cls, results: Dict[str, str], exclude_keys: List[str], common_column_name: str
    ):
        rephrase = {k: v for k, v in results.items() if k not in exclude_keys}
        length = len(rephrase)
        table_num = ceil(length / cls.separate)
        tables = []
        for _ in range(table_num):
            t = Table()
            t.add_column(common_column_name)
            tables.append(t)
        table_rows = [[""] for _ in range(table_num)]
        count = 0
        ti = 0
        for i, (k, v) in enumerate(rephrase.items()):

            this_table = tables[ti]
            this_table.add_column(k)
            table_rows[ti].append(str(v))
            count += 1
            if count == cls.separate:
                count = 0
                ti += 1

        for i, r in enumerate(table_rows):
            tables[i].add_row(*r)
        return tables

    @classmethod
    def generate_table(cls, results: Dict) -> List[Table]:
        """Make a new table."""

        all_tables = cls.assign_table(results, ["total", "port_data"], f"general")
        all_tables += cls.assign_table(
            results["total"],
            ["tx_counter", "rx_counter"],
            f"total_other",
        )
        all_tables += cls.assign_table(results["total"]["tx_counter"], [], f"total_tx")
        all_tables += cls.assign_table(results["total"]["rx_counter"], [], f"total_rx")

        for port in results["port_data"]:
            all_tables += cls.assign_table(
                port,
                [
                    "tx_counter",
                    "rx_counter",
                    "stream_statistic",
                    "jitter",
                    "latency",
                    "port_id",
                ],
                f"port {port['port_id']}",
            )
            all_tables += cls.assign_table(
                port["tx_counter"], [], f"port {port['port_id']} tx"
            )
            all_tables += cls.assign_table(
                port["rx_counter"], [], f"port {port['port_id']} rx"
            )
            all_tables += cls.assign_table(
                port["jitter"], [], f"port {port['port_id']} jitter"
            )
            all_tables += cls.assign_table(
                port["latency"], [], f"port {port['port_id']} latency"
            )
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
        T2544Displayer.display(json.loads(msg.payload.json()))


async def start_test(
    ctrl: controller.MainController, config: Dict[str, Any], test_suite_name: str
) -> None:
    exec_id = ctrl.start_test_suite(test_suite_name, config, debug_connection=DEBUG)
    await subscribe(ctrl, exec_id)


async def main() -> None:
    new = [
        types.Credentials(
            product=types.EProductType.VALKYRIE,
            host="demo.xenanetworks.com",
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
        with open("2544.json", "w") as f:
            f.write(new_data)
        config = json.loads(new_data)
        await start_test(c, config, T_SUITE_NAME)


if __name__ == "__main__":
    set_windows_loop_policy()
    asyncio.run(main())
