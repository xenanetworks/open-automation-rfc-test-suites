import asyncio
from ..utils.field import NonNegativeDecimal

from .test_result_structure import BoutEntry
from .setup_source_port_rates import setup_source_port_rates
from .statistics import (
    set_stream_packet_limit,
    start_traffic,
)
from typing import TYPE_CHECKING, List
from xoa_driver.utils import apply

if TYPE_CHECKING:
    from .test_operations import StateChecker
    from ..model import TestConfiguration
    from .structure import Structure, StreamInfo


async def add_flow_based_learning_preamble_steps(
    stream_lists: List["StreamInfo"],
    source_ports: List["Structure"],
    test_conf: "TestConfiguration",
    current_packet_size: NonNegativeDecimal,
    state_checker: "StateChecker",
) -> None:  # AddFlowBasedLearningPreambleSteps
    if not test_conf.use_flow_based_learning_preamble:
        return
    rate_percent_dic = {
        port_struct.properties.identity: BoutEntry(
            port_struct.properties.identity, rate=test_conf.learning_rate_pct
        )
        for port_struct in source_ports
    }

    await setup_source_port_rates(
        source_ports,
        stream_lists,
        test_conf.flow_creation_type,
        rate_percent_dic,
        current_packet_size,
    )
    await set_stream_packet_limit(
        source_ports, test_conf.flow_based_learning_frame_count
    )

    await start_traffic(source_ports)
    while state_checker.test_running():
        await check_status(source_ports)
        await asyncio.sleep(0.1)
    await asyncio.sleep(test_conf.delay_after_flow_based_learning_ms / 1000)
    await set_stream_packet_limit(source_ports, 0)  # clear packet limit


from xoa_driver.internals.ports.port_l23.chimera.port_chimera import PortChimera


async def check_status(source_ports: List["Structure"]) -> None:
    for port_struct in source_ports:
        port = port_struct.port
        if isinstance(port, PortChimera):
            return
        print((await port_struct.port.traffic.state.get()).on_off)
