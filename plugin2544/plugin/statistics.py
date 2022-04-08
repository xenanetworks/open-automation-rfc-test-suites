import asyncio
from typing import TYPE_CHECKING, Dict, List
from xoa_driver.utils import apply
from xoa_driver.enums import OnOff

if TYPE_CHECKING:
    from .structure import Structure
    from ..model import CommonOptions, TestConfiguration
    from ..utils.constants import DurationType
    from xoa_driver.misc import Token
    from xoa_driver.testers import L23Tester
    from xoa_driver.ports import GenericL23Port


async def clear_port_stats(control_ports: List["Structure"]) -> None:
    tokens = []
    for port_struct in control_ports:
        tokens.append(port_struct.port.statistics.rx.clear.set())  # PR_CLEAR
        tokens.append(port_struct.port.statistics.tx.clear.set())  # PT_CLEAR
    await apply(*tokens)
    await asyncio.sleep(1)


def should_set_tx_time_duration(
    port_struct: "Structure", duration_type: "DurationType"
) -> bool:
    # Do not set TX time duration if max frames has been set for streams on this port
    if (
        port_struct.properties.is_max_frames_limit_set
        and not port_struct.port_conf.pause_mode_enabled
    ):
        return False
    # Only set TX time duration if duration type is "Seconds"
    return duration_type.is_time_duration


async def reset_tx_time_limit(control_ports: List["Structure"]) -> None:
    tokens = []
    for port_struct in control_ports:
        tokens += set_tx_time_limit(port_struct.port, 0)
    await apply(*tokens)


def set_tx_time_limit(port: "GenericL23Port", tx_timelimit: int) -> List["Token"]:
    return [port.tx_config.time_limit.set(tx_timelimit)]


async def handle_port_traffic_sync_start(
    source_port: List["Structure"],
    traffic_status: bool,
) -> None:
    tokens: List["Token"] = []
    mapping: Dict[str, List[int]] = {}
    testers_dict: Dict[str, "L23Tester"] = {}
    for port_struct in source_port:
        chassis_id = port_struct.properties.chassis_id
        if chassis_id not in mapping:
            mapping[chassis_id] = []
            testers_dict[chassis_id] = port_struct.tester
        mapping[chassis_id] += [port_struct.port.kind.module_id, port_struct.port.kind.port_id]
    
    for chassis_id, module_port_list in mapping.items():
        tester = testers_dict[chassis_id]
        tokens.append(tester.traffic.set(OnOff(traffic_status), module_port_list))
    await apply(*tokens)


async def set_traffic_timelimit(
    source_port: List["Structure"],
    traffic_status: bool,
    common_option: "CommonOptions",
    tx_timelimit: int = 0,
) -> None:
    tokens = []
    for port_struct in source_port:
        port = port_struct.port
        if traffic_status and (
            tx_timelimit
            or should_set_tx_time_duration(port_struct, common_option.duration_type)
        ):
            if not tx_timelimit:
                tx_timelimit = round(
                    common_option.duration
                    * common_option.duration_time_unit.scale
                    * 1000000
                )
            tokens += set_tx_time_limit(port, tx_timelimit)
    await apply(*tokens)


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
    common_option: "CommonOptions",
    traffic_status: bool,
    is_learning: bool = False,
) -> None:

    tx_time_limit = test_conf.learning_duration_second * 1000 if is_learning else 0
    await set_traffic_timelimit(
        source_ports,
        traffic_status,
        common_option,
        tx_time_limit,
    )
    if traffic_status and test_conf.use_port_sync_start:
        await handle_port_traffic_sync_start(source_ports, traffic_status)
    else:
        await handle_port_traffic_individually(
            source_ports,
            traffic_status,
        )

async def stop_traffic(control_ports: List["Structure"]) -> None:
    await asyncio.gather(
        *[
            port_struct.port.traffic.state.set_stop()
            for port_struct in control_ports
        ]
    )
    await asyncio.sleep(1)
