import asyncio
import math
from typing import TYPE_CHECKING
from decimal import Decimal
from ..utils.field import NonNegativeDecimal

if TYPE_CHECKING:
    from .test_resource import ResourceManager
    from .structure import PortStruct


async def setup_source_port_rates(
    resources: "ResourceManager",
    current_packet_size: NonNegativeDecimal,
) -> None:  # SetupSourcePortRatesForLearning
    for port_struct in resources.tx_ports:
        if resources.test_conf.flow_creation_type.is_stream_based:
            await _setup_source_port_rate_stream_mode(
                port_struct,
                current_packet_size,
            )
        else:
            await _setup_source_port_rate_modifier_mode(
                port_struct,
                current_packet_size,
            )

async def _setup_source_port_rate_stream_mode(
    port_struct: "PortStruct", current_packet_size: NonNegativeDecimal
) -> None:  # SetupSourcePortRateStreamMode
    inter_frame_gap = port_struct.port_conf.inter_frame_gap
    src_port_speed = await port_struct.get_use_port_speed()
    for peer_struct in port_struct.properties.peers:
        stream_info_list = [
            stream_info
            for stream_info in port_struct.stream_structs
            if stream_info.is_rx_port(peer_struct)
        ]
        port_stream_count = len(port_struct.properties.peers) * len(stream_info_list)
        stream_rate_percent = Decimal(str(port_struct.rate)) / Decimal(
            str(port_stream_count)
        )
        stream_rate_bps_L1 = (
            Decimal(str(stream_rate_percent)) * src_port_speed / Decimal("100")
        )
        stream_rate_bps_L2 = math.floor(
            stream_rate_bps_L1
            * Decimal(str(current_packet_size))
            / (Decimal(str(current_packet_size)) + Decimal(str(inter_frame_gap)))
        )
        await asyncio.gather(
            *[
                stream_struct.set_l2bps_rate(stream_rate_bps_L2)
                for stream_struct in stream_info_list
            ]
        )

async def _setup_source_port_rate_modifier_mode(
    port_struct: "PortStruct",
    current_packet_size: NonNegativeDecimal,
) -> None:  # SetupSourcePortRateModifierMode
    inter_frame_gap = port_struct.port_conf.inter_frame_gap
    src_port_speed = await port_struct.get_use_port_speed()
    port_rate_bps_L1 = Decimal(str(port_struct.rate)) * src_port_speed / Decimal(100)
    port_rate_bps_L2 = (
        Decimal(str(port_rate_bps_L1))
        * Decimal(str(current_packet_size))
        / (Decimal(str(current_packet_size)) + Decimal(str(inter_frame_gap)))
    )
    if port_struct.properties.num_modifiersL2 > 1:
        low_rate = floor(
            port_rate_bps_L2
            * port_struct.properties.low_dest_port_count
            / port_struct.properties.dest_port_count
        )
        high_rate = floor(port_rate_bps_L2 - low_rate)
        stream_rate_list = [low_rate, high_rate]
    else:
        stream_rate_list = [floor(port_rate_bps_L2)]
    await asyncio.gather(
        *[
            port_struct.stream_structs[stream_id].set_l2bps_rate(stream_rate)
            for stream_id, stream_rate in enumerate(stream_rate_list)
        ]
    )