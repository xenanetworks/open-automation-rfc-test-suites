import asyncio
from ..utils.field import NonNegativeDecimal

from .test_result_structure import BoutEntry
from .setup_source_port_rates import setup_source_port_rates
from .statistics import set_traffic_status
from typing import TYPE_CHECKING, List
from xoa_driver.utils import apply


if TYPE_CHECKING:
    from ..model import TestConfiguration, CommonOptions
    from .structure import Structure, StreamInfo


async def _setup_flow_based_learning_frame_count(
    source_port_structs: List["Structure"],
    flow_based_learning_frame_count: int,
) -> None:  # SetupFlowBasedLearningFrameCount
    tokens = []
    for port_struct in source_port_structs:
        for stream in port_struct.port.streams:
            tokens.append(stream.packet.limit.set(flow_based_learning_frame_count))
    await apply(*tokens)


async def add_flow_based_learning_preamble_steps(
    stream_lists: List["StreamInfo"],
    source_ports: List["Structure"],
    test_conf: "TestConfiguration",
    common_option: "CommonOptions",
    current_packet_size: NonNegativeDecimal,
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
        common_option,
        rate_percent_dic,
        current_packet_size,
        True,
    )
    await _setup_flow_based_learning_frame_count(
        source_ports, test_conf.flow_based_learning_frame_count
    )

    await set_traffic_status(source_ports, test_conf, common_option, True)
    await asyncio.sleep(test_conf.delay_after_flow_based_learning_ms / 1000)
    await set_traffic_status(source_ports, test_conf, common_option, False)
