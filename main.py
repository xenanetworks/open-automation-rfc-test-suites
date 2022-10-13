import asyncio
import json
from config import INPUT_DATA_PATH
from xoa_core import types, controller
import sys

sys.path.append("D:/Working/open-automation-config-converter")


from xoa_converter.entry import converter
from xoa_converter.types import TestSuiteType
from rich.live import Live
from rich.table import Table
from rich.console import Console
from pydantic import SecretStr
from typing import Dict, List


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


async def test():
    new = [
        types.Credentials(
            product=types.EProductType.VALKYRIE,
            host="192.168.1.198",
            password=SecretStr("xena"),
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
        "RFC-3918", json.loads(new_data), debug_connection=True
    )
    async for msg in c.listen_changes(test_id, _filter={types.EMsgType.STATISTICS}):
        print(T3918Displayer.display(msg.payload))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(test())
    loop.run_forever()
