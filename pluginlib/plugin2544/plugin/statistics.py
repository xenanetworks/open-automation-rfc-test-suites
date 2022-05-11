import asyncio
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List
from xoa_driver.utils import apply
from xoa_driver.enums import OnOff

if TYPE_CHECKING:
    from .structure import Structure
    from ..model import TestConfiguration
    from xoa_driver.testers import L23Tester


async def clear_port_stats(control_ports: List["Structure"]) -> None:
    tokens = []
    for port_struct in control_ports:
        tokens.append(port_struct.port.statistics.rx.clear.set())  # PR_CLEAR
        tokens.append(port_struct.port.statistics.tx.clear.set())  # PT_CLEAR
    await apply(*tokens)
    await asyncio.sleep(1)


async def set_port_txtime_limit(
    control_ports: List["Structure"], tx_timelimit: Decimal
) -> None:
    await asyncio.gather(
        *[
            port_struct.port.tx_config.time_limit.set(int(tx_timelimit))
            for port_struct in control_ports
        ]
    )

async def set_stream_packet_limit(source_port_structs: List["Structure"], frame_count: int) -> None:
    await asyncio.gather(*[stream.packet.limit.set(frame_count) for port_struct in source_port_structs for stream in port_struct.port.streams])


async def start_traffic_sync(tester: "L23Tester", module_port_list: List[int]) -> None:
    local_time = (await tester.time.get()).local_time
    delay_seconds = 2
    # logger.error(
    #     f"SYNC {tester.management_interface.ip_address} -> {local_time + delay_seconds}"
    # )
    await apply(
        tester.traffic_sync.set_on(local_time + delay_seconds, module_port_list)
    )


async def handle_port_traffic_sync_start(
    source_port: List["Structure"],
    traffic_status: bool,
) -> None:
    mapping: Dict[str, List[int]] = {}
    testers_dict: Dict[str, "L23Tester"] = {}
    for port_struct in source_port:
        chassis_id = port_struct.properties.chassis_id
        if chassis_id not in mapping:
            mapping[chassis_id] = []
            testers_dict[chassis_id] = port_struct.tester
        mapping[chassis_id] += [
            port_struct.port.kind.module_id,
            port_struct.port.kind.port_id,
        ]

    if len(mapping) == 1:
        # same tester
        chassis_id = list(mapping.keys())[0]
        tester = testers_dict[chassis_id]
        await apply(tester.traffic.set(OnOff(traffic_status), mapping[chassis_id]))
    else:
        # multi tester need to use c_trafficsync cmd
        await asyncio.gather(
            *[
                start_traffic_sync(testers_dict[chassis_id], module_port_list)
                for chassis_id, module_port_list in mapping.items()
            ]
        )


async def handle_port_traffic_individually(
    source_port: List["Structure"],
    traffic_status: bool,
) -> None:
    tokens = []
    for port_struct in source_port:
        port = port_struct.port
        if port_struct.port_conf.is_tx_port:
            if traffic_status:
                tokens.append(port.traffic.state.set_start())
            else:
                tokens.append(port.traffic.state.set_stop())
    await apply(*tokens)


async def set_traffic_status(
    source_ports: List["Structure"],
    test_conf: "TestConfiguration",
    traffic_status: bool,
) -> None:
    if traffic_status and test_conf.use_port_sync_start:
        await handle_port_traffic_sync_start(source_ports, traffic_status)
    else:
        await handle_port_traffic_individually(
            source_ports,
            traffic_status,
        )


async def start_traffic(control_ports: List["Structure"]) -> None:
    await asyncio.gather(
        *[
            port_struct.port.traffic.state.set_start()
            for port_struct in control_ports
            if port_struct.port_conf.is_tx_port
        ]
    )


async def stop_traffic(control_ports: List["Structure"]) -> None:
    await asyncio.gather(
        *[port_struct.port.traffic.state.set_stop() for port_struct in control_ports]
    )
    await asyncio.sleep(1)
