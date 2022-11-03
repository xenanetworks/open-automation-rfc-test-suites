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
import colorama
import random

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
    # true = True
    # false = False
    # dic = {
    #     "test_case_type": "throughput",
    #     "test_suite_type": "xoa2544",
    #     "result_state": "pending",
    #     "tx_rate_percent": 100.0,
    #     "is_final": false,
    #     "frame_size": 512.0,
    #     "repetition": 1,
    #     "rate_result_scope": "common_result",
    #     "port_data": [
    #         {
    #             "port_id": "P-0-0-2",
    #             "is_final": false,
    #             "frame_size": 512.0,
    #             "duration": 10.0,
    #             "rate": 100.0,
    #             "interframe_gap": 20.0,
    #             "port_speed": 1000000000.0,
    #             "tx_counter": {
    #                 "frames": 254462,
    #                 "bps": 962402180,
    #                 "pps": 234961,
    #                 "bytes_count": 0,
    #                 "frame_rate": 25446.2,
    #                 "l2_bit_rate": 104227635.2,
    #                 "l1_bit_rate": 108299027.2,
    #                 "tx_l1_bps": 999996015.156,
    #                 "counter_type": 0,
    #                 "l2_bps": 962402180,
    #                 "l1_bps": 999996015,
    #                 "fps": 234961,
    #             },
    #             "rx_counter": {
    #                 "frames": 166598,
    #                 "bps": 962406960,
    #                 "pps": 234963,
    #                 "bytes_count": 85298176,
    #                 "frame_rate": 16659.8,
    #                 "l2_bit_rate": 68238540.8,
    #                 "l1_bit_rate": 70904108.8,
    #                 "tx_l1_bps": 1000000981.88,
    #                 "counter_type": 1,
    #                 "l2_bps": 962406960,
    #                 "l1_bps": 1000000981,
    #                 "fps": 234963,
    #             },
    #             "latency": {"minimum": 57, "maximum": 97, "average": 75},
    #             "jitter": {"minimum": 0, "maximum": 24, "average": 7},
    #             "stream_statistic": [
    #                 {
    #                     "src_port_id": "P-0-0-2",
    #                     "dest_port_id": "P-0-0-3",
    #                     "src_port_addr": "04:F4:BC:94:DA:E2",
    #                     "dest_port_addr": "04:F4:BC:94:DA:E3",
    #                     "tx_counter": {
    #                         "frames": 254462,
    #                         "bps": 962402180,
    #                         "pps": 234961,
    #                         "bytes_count": 0,
    #                         "frame_rate": 25446.2,
    #                         "l2_bit_rate": 104227635.2,
    #                         "l1_bit_rate": 108299027.2,
    #                         "tx_l1_bps": 999996015.156,
    #                     },
    #                     "rx_counter": {
    #                         "frames": 254523,
    #                         "bps": 127736860,
    #                         "pps": 31186,
    #                         "bytes_count": 130315776,
    #                         "frame_rate": 0.0,
    #                         "l2_bit_rate": 0.0,
    #                         "l1_bit_rate": 0.0,
    #                         "tx_l1_bps": 0.0,
    #                     },
    #                     "latency": {"minimum": 41, "maximum": 81, "average": 59},
    #                     "jitter": {"minimum": 0, "maximum": 24, "average": 7},
    #                     "live_loss_frames": 0,
    #                     "burst_frames": 0,
    #                 }
    #             ],
    #             "fcs_error_frames": 0,
    #             "burst_frames": 0,
    #             "burst_bytes_count": 130315776,
    #             "loss_frames": 0,
    #             "loss_ratio": 0.0,
    #             "actual_rate_percent": 10.83,
    #             "tx_rate_l1_bps_theor": 1000000000,
    #             "tx_rate_fps_theor": 234962,
    #         },
    #         {
    #             "port_id": "P-0-0-3",
    #             "is_final": false,
    #             "frame_size": 512.0,
    #             "duration": 10.0,
    #             "rate": 100.0,
    #             "interframe_gap": 20.0,
    #             "port_speed": 1000000000.0,
    #             "tx_counter": {
    #                 "frames": 166743,
    #                 "bps": 201724980,
    #                 "pps": 49249,
    #                 "bytes_count": 0,
    #                 "frame_rate": 16674.3,
    #                 "l2_bit_rate": 68297932.8,
    #                 "l1_bit_rate": 70965820.8,
    #                 "tx_l1_bps": 209604862.031,
    #                 "counter_type": 0,
    #                 "l2_bps": 201724980,
    #                 "l1_bps": 209604862,
    #                 "fps": 49249,
    #             },
    #             "rx_counter": {
    #                 "frames": 254523,
    #                 "bps": 127736860,
    #                 "pps": 31186,
    #                 "bytes_count": 130315776,
    #                 "frame_rate": 25452.3,
    #                 "l2_bit_rate": 104252620.8,
    #                 "l1_bit_rate": 108324988.8,
    #                 "tx_l1_bps": 132726581.094,
    #                 "counter_type": 1,
    #                 "l2_bps": 127736860,
    #                 "l1_bps": 132726581,
    #                 "fps": 31186,
    #             },
    #             "latency": {"minimum": 41, "maximum": 81, "average": 59},
    #             "jitter": {"minimum": 0, "maximum": 24, "average": 7},
    #             "stream_statistic": [
    #                 {
    #                     "src_port_id": "P-0-0-3",
    #                     "dest_port_id": "P-0-0-2",
    #                     "src_port_addr": "04:F4:BC:94:DA:E3",
    #                     "dest_port_addr": "04:F4:BC:94:DA:E2",
    #                     "tx_counter": {
    #                         "frames": 166743,
    #                         "bps": 201724980,
    #                         "pps": 49249,
    #                         "bytes_count": 0,
    #                         "frame_rate": 16674.3,
    #                         "l2_bit_rate": 68297932.8,
    #                         "l1_bit_rate": 70965820.8,
    #                         "tx_l1_bps": 209604862.031,
    #                     },
    #                     "rx_counter": {
    #                         "frames": 166598,
    #                         "bps": 962406960,
    #                         "pps": 234963,
    #                         "bytes_count": 85298176,
    #                         "frame_rate": 0.0,
    #                         "l2_bit_rate": 0.0,
    #                         "l1_bit_rate": 0.0,
    #                         "tx_l1_bps": 0.0,
    #                     },
    #                     "latency": {"minimum": 57, "maximum": 97, "average": 75},
    #                     "jitter": {"minimum": 0, "maximum": 24, "average": 7},
    #                     "live_loss_frames": 0,
    #                     "burst_frames": 0,
    #                 }
    #             ],
    #             "fcs_error_frames": 0,
    #             "burst_frames": 0,
    #             "burst_bytes_count": 85298176,
    #             "loss_frames": 0,
    #             "loss_ratio": 0.0,
    #             "actual_rate_percent": 7.097,
    #             "tx_rate_l1_bps_theor": 1000000000,
    #             "tx_rate_fps_theor": 234962,
    #         },
    #     ],
    #     "tx_rate_nominal_percent": 0.0,
    #     "total": {
    #         "tx_counter": {
    #             "frames": 421205,
    #             "l1_bps": 1209600877,
    #             "l2_bps": 1164127160,
    #             "fps": 284210,
    #             "bytes_count": 0,
    #         },
    #         "rx_counter": {
    #             "frames": 421121,
    #             "l1_bps": 1132727562,
    #             "l2_bps": 1090143820,
    #             "fps": 266149,
    #             "bytes_count": 215613952,
    #         },
    #         "fcs_error_frames": 0,
    #         "rx_loss_percent": 0.0,
    #         "rx_loss_frames": 0,
    #         "tx_rate_l1_bps_theor": 2000000000,
    #         "tx_rate_fps_theor": 469924,
    #         "tx_burst_frames": 0,
    #         "tx_burst_bytes": 215613952,
    #         "ber_percent": 0.0,
    #     },
    # }

    # T2544Displayer.display(dic)
