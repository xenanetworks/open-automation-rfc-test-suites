import math
from typing import TYPE_CHECKING, Dict, List
from math import floor
from decimal import Decimal
from ..utils.field import NonNegativeDecimal
from .test_operations import get_port_rate, get_use_port_speed
from .test_result_structure import IterationEntry
from ..utils.constants import MAX_PACKET_LIMIT_VALUE
from xoa_driver.utils import apply

if TYPE_CHECKING:
    from .structure import Structure, StreamInfo
    from ..model import CommonOptions
    from ..utils.constants import FlowCreationType

    from xoa_driver.misc import GenuineStream
    from xoa_driver.misc import Token


async def setup_source_port_rates(
    source_port_structs: List["Structure"],
    stream_lists: List["StreamInfo"],
    flow_creation_type: "FlowCreationType",
    common_option: "CommonOptions",
    rate_percent_dic: Dict[str, IterationEntry],
    current_packet_size: NonNegativeDecimal,
    is_learning: bool,
) -> None:  # SetupSourcePortRatesForLearning
    for port_struct in source_port_structs:
        src_port_speed = await get_use_port_speed(port_struct)
        dest_port_list = port_struct.properties.peers

        if flow_creation_type.is_stream_based:
            await _setup_source_port_rate_stream_mode(
                stream_lists,
                port_struct,
                dest_port_list,
                src_port_speed,
                rate_percent_dic,
                current_packet_size,
                common_option,
                is_learning,
            )
        else:
            await _setup_source_port_rate_modifier_mode(
                port_struct,
                src_port_speed,
                rate_percent_dic,
                current_packet_size,
                common_option,
            )


async def _setup_source_port_rate_stream_mode(
    stream_lists: List["StreamInfo"],
    port_struct: "Structure",
    dest_port_list: List["Structure"],
    src_port_speed: Decimal,
    rate_percent_dic: Dict[str, IterationEntry],
    current_packet_size: NonNegativeDecimal,
    common_options: "CommonOptions",
    is_learning: bool,
) -> None:  # SetupSourcePortRateStreamMode
    tokens = []
    inter_frame_gap = port_struct.port_conf.inter_frame_gap
    for peer_struct in dest_port_list:
        stream_info_list = [
            stream_info
            for stream_info in stream_lists
            if stream_info.port_struct == port_struct
            and stream_info.peer_struct == peer_struct
        ]
        port_stream_count = len(dest_port_list) * len(stream_info_list)
        rate_percent = get_port_rate(port_struct, rate_percent_dic)
        stream_rate_percent = Decimal(str(rate_percent)) / Decimal(
            str(port_stream_count)
        )
        stream_rate_bps_L1 = (
            Decimal(str(stream_rate_percent))
            * src_port_speed
            / Decimal("100")
        )
        stream_rate_bps_L2 = math.floor(
            stream_rate_bps_L1
            * Decimal(str(current_packet_size))
            / (Decimal(str(current_packet_size)) + Decimal(str(inter_frame_gap)))
        )
        for stream_info in stream_info_list:
            stream = port_struct.port.streams.obtain(stream_info.stream_id)
            tokens.append(stream.rate.l2bps.set(stream_rate_bps_L2))
            if not is_learning:
                stream_packet_rate = (
                    Decimal(str(stream_rate_bps_L2))
                    / Decimal("8.0")
                    / Decimal(str(current_packet_size))
                )

                tokens += _set_stream_packet_limit(
                    port_struct,
                    stream,
                    stream_packet_rate,
                    common_options,
                    port_stream_count,
                )
    await apply(*tokens)


def _set_stream_packet_limit(
    port_struct: "Structure",
    stream: "GenuineStream",
    stream_packet_rate: Decimal,
    common_option: "CommonOptions",
    stream_count: int,
) -> List["Token"]:
    if common_option.duration_type.is_time_duration:
        actual_duration = common_option.get_set_actual_duration()
        total_frames_for_stream = Decimal(str(stream_packet_rate)) * Decimal(
            str(actual_duration)
        )

    else:
        duration_frame_unit = common_option.duration_frame_unit
        total_frames_for_stream = (
            Decimal(str(common_option.duration_frames))
            * Decimal(str(duration_frame_unit.scale))
            / Decimal(str(stream_count))
        )
        actual_duration = common_option.get_set_actual_duration(
            Decimal(str(total_frames_for_stream)) / Decimal(str(stream_packet_rate))
        )

    is_max_frames_limit_set = 0 < total_frames_for_stream <= MAX_PACKET_LIMIT_VALUE
    total_frames_for_stream = total_frames_for_stream if is_max_frames_limit_set else Decimal('0')
    port_struct.properties.change_max_frames_limit_set_status(is_max_frames_limit_set)
    return [stream.packet.limit.set(math.floor(total_frames_for_stream))]




async def _setup_source_port_rate_modifier_mode(
    port_struct: "Structure",
    src_port_speed: Decimal,
    rate_percent_dic: Dict[str, IterationEntry],
    current_packet_size: NonNegativeDecimal,
    common_option: "CommonOptions",
) -> None:  # SetupSourcePortRateModifierMode
    tokens = []
    inter_frame_gap = port_struct.port_conf.inter_frame_gap
    rate_percent = get_port_rate(port_struct, rate_percent_dic)
    port_rate_bps_L1 = (
        Decimal(str(rate_percent)) * src_port_speed / Decimal(100)
    )
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

    for stream_id, stream_rate in enumerate(stream_rate_list):
        stream = port_struct.port.streams.obtain(stream_id)
        tokens.append(stream.rate.l2bps.set(int(stream_rate)))
        stream_packet_rate = (
            Decimal(str(stream_rate))
            / Decimal("8.0")
            / Decimal(str(current_packet_size))
        )

        tokens += _set_stream_packet_limit(
            port_struct,
            stream,
            stream_packet_rate,
            common_option,
            len(stream_rate_list),
        )
    await apply(*tokens)
