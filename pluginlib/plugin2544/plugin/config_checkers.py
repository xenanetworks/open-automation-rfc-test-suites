import asyncio
from typing import TYPE_CHECKING, List, Union
from xoa_driver.enums import ProtocolOption
from ..utils import field, exceptions, constants as const
from .common import (
    filter_port_structs,
)

if TYPE_CHECKING:
    from .structure import PortStruct
    from xoa_driver import testers as xoa_testers
    from ..model import (
        ProtocolSegmentProfileConfig,
        PortConfiguration,
        TestConfiguration,
    )
    from xoa_driver.internals.core.commands import (
        P_CAPABILITIES,
    )


def check_port_config_profile(
    capabilities: "P_CAPABILITIES.GetDataAttr", profile: "ProtocolSegmentProfileConfig"
) -> None:
    segment_id_list = profile.segment_id_list
    if capabilities.max_protocol_segments < len(segment_id_list):
        raise exceptions.ProtocolSegmentExceed(
            len(segment_id_list), capabilities.max_protocol_segments
        )
    if (
        ProtocolOption.TCPCHECK in segment_id_list
        and not capabilities.can_tcp_checksum
    ):
        raise exceptions.ProtocolNotSupport("TCPCHECK")
    if (
        ProtocolOption.UDPCHECK in segment_id_list
        and  not capabilities.can_udp_checksum
    ):
        raise exceptions.ProtocolNotSupport("UDPCHECK")

    if profile.packet_header_length > capabilities.max_header_length:
        raise exceptions.PacketHeaderExceed(
            profile.packet_header_length, capabilities.max_header_length
        )

    for header_segment in profile.header_segments:
        for modifier in header_segment.hw_modifiers:
            if modifier.repeat_count > capabilities.max_repeat:
                raise exceptions.ModifierRepeatCountExceed(
                    modifier.repeat_count, capabilities.max_repeat
                )


def check_can_fec(can_fec: int, fec_mode: const.FECModeStr) -> None:
    bin_str = bin(can_fec)[2:].zfill(32)
    is_mandatory = int(bin_str[-32])
    cap_mode = bin_str[-3:]
    supported_mode = [] if is_mandatory else [const.FECModeStr.OFF]
    if fec_mode == const.FECModeStr.OFF:
        if is_mandatory:
            raise exceptions.FECModeRequired()
    elif cap_mode == "100" and fec_mode != const.FECModeStr.FC_FEC:
        supported_mode.append(const.FECModeStr.FC_FEC)
        raise exceptions.FECModeTypeNotSupport(supported_mode)
    elif cap_mode in ["010", "001"] and fec_mode != const.FECModeStr.ON:
        supported_mode.append(const.FECModeStr.ON)
        raise exceptions.FECModeTypeNotSupport(supported_mode)


async def check_custom_port_config(
    capabilities: "P_CAPABILITIES.GetDataAttr", port_conf: "PortConfiguration"
) -> None:

    if port_conf.port_rate > capabilities.max_speed * 1_000_000:
        raise exceptions.PortRateError(port_conf.port_rate, capabilities.max_speed * 1_000_000)
    if port_conf.speed_reduction_ppm > capabilities.max_speed_reduction:
        raise exceptions.SpeedReductionError(
            port_conf.speed_reduction_ppm, capabilities.max_speed_reduction
        )
    if (
        capabilities.min_interframe_gap > port_conf.inter_frame_gap
        or port_conf.inter_frame_gap > capabilities.max_interframe_gap
    ):
        raise exceptions.InterFrameGapError(
            port_conf.inter_frame_gap, capabilities.min_interframe_gap, capabilities.max_interframe_gap
        )
    check_can_fec(capabilities.can_fec, port_conf.fec_mode)
    check_port_config_profile(capabilities, port_conf.profile)


async def check_ports(control_ports: List["PortStruct"]) -> None:
    await asyncio.gather(
        *[
            check_custom_port_config(port_struct.capabilities, port_struct.port_conf)
            for port_struct in control_ports
        ]
    )


async def check_port_modifiers(
    capabilities: "P_CAPABILITIES.GetDataAttr",
    port_conf: "PortConfiguration",
    is_stream_based: bool,
) -> None:
    if not port_conf.is_tx_port:
        return

    modifier_count = port_conf.profile.modifier_count
    if is_stream_based:
        if modifier_count > capabilities.max_modifiers:
            raise exceptions.ModifierExceed(
                modifier_count, capabilities.max_modifiers
            )
    else:
        if modifier_count > 0:
            raise exceptions.ModifierBasedNotSupportDefineModifier()


async def check_stream_limitations(
    port_struct: "PortStruct", per_port_stream_count: int, is_stream_based: bool
) -> None:
    if not is_stream_based:
        return
    if not port_struct.port_conf.is_tx_port:
        return
    stream_count = len(port_struct.properties.peers) * per_port_stream_count
    if stream_count > port_struct.capabilities.max_streams_per_port:
        raise exceptions.StreamExceed(
            stream_count, port_struct.capabilities.max_streams_per_port
        )


def count_source_port(
    control_ports: List["PortStruct"], peer_struct: "PortStruct"
) -> int:
    count = 0
    for port_struct in control_ports:
        if peer_struct in port_struct.properties.peers:
            count += 1
    return count


def check_tid_limitations(
    control_ports: List["PortStruct"],
    scope: "const.TidAllocationScope",
    is_stream_based: bool,
) -> None:
    if not is_stream_based:
        return
    if not scope.is_config_scope:
        return

    tid_value = 0
    dest_port_structs = filter_port_structs(control_ports, is_source_port=False)
    for peer_struct in dest_port_structs:
        src_port_count = count_source_port(control_ports, peer_struct)
        tid_value += src_port_count
        max_tpld_stats = peer_struct.capabilities.max_tpld_stats
        if tid_value > max_tpld_stats:
            raise exceptions.TPLDIDExceed(tid_value, max_tpld_stats)


async def check_port_min_packet_length(
    capabilities: "P_CAPABILITIES.GetDataAttr",
    min_packet_size: Union[field.NonNegativeDecimal, int],
    packet_size_type: "const.PacketSizeType",
) -> None:
    if capabilities.min_packet_length > min_packet_size:
        raise exceptions.MinPacketLengthExceed(
            packet_size_type.value,
            int(min_packet_size),
            capabilities.min_packet_length,
        )


async def check_port_max_packet_length(
    capabilities: "P_CAPABILITIES.GetDataAttr",
    max_packet_size: Union[field.NonNegativeDecimal, int],
    packet_size_type: "const.PacketSizeType",
) -> None:
    if capabilities.max_packet_length < max_packet_size:
        raise exceptions.MaxPacketLengthExceed(
            packet_size_type.value,
            int(max_packet_size),
            capabilities.max_packet_length,
        )


def get_tpld_total_length(
    capabilities: "P_CAPABILITIES.GetDataAttr", use_micro_tpld_on_demand: bool
) -> int:
    if use_micro_tpld_on_demand and capabilities.can_micro_tpld:
        return const.MICRO_TPLD_TOTAL_LENGTH
    return const.STANDARD_TPLD_TOTAL_LENGTH


def get_needed_packet_length(
    port_struct: "PortStruct", use_micro_tpld_on_demand: bool
) -> int:
    packet_header_length = port_struct.port_conf.profile.packet_header_length
    return packet_header_length + get_tpld_total_length(
        port_struct.capabilities, use_micro_tpld_on_demand
    )


async def check_needed_packet_length(
    port_struct: "PortStruct",
    min_packet_size: Union[field.NonNegativeDecimal, int],
    use_micro_tpld_on_demand: bool,
) -> None:
    need_packet_length = get_needed_packet_length(port_struct, use_micro_tpld_on_demand)
    if min_packet_size < need_packet_length:
        raise exceptions.PacketSizeTooSmall(int(min_packet_size), need_packet_length)


async def check_payload_pattern(capabilities: "P_CAPABILITIES.GetDataAttr", payload_pattern: str) -> None:
    cur = len(payload_pattern) // 2
    if capabilities.max_pattern_length < cur:
        raise exceptions.PayloadPatternExceed(
            cur, capabilities.max_pattern_length
        )


async def check_micro_tpld(capabilities: "P_CAPABILITIES.GetDataAttr", use_mocro_tpld: bool) -> None:
    if not use_mocro_tpld:
        return
    if not bool(capabilities.can_micro_tpld):
        raise exceptions.MicroTPLDNotSupport()


async def check_port_test_config(
    port_struct: "PortStruct", test_conf: "TestConfiguration"
) -> None:
    is_stream_based = test_conf.flow_creation_type.is_stream_based
    if test_conf.frame_sizes.packet_size_type.is_mix:
        packet_size_list = test_conf.frame_sizes.mixed_packet_length
    else:
        packet_size_list = test_conf.frame_sizes.packet_size_list
    packet_size_type = test_conf.frame_sizes.packet_size_type
    min_packet_size = min(packet_size_list)
    max_packet_size = max(packet_size_list)
    per_port_stream_count = test_conf.multi_stream_config.per_port_stream_count
    await check_payload_pattern(port_struct.capabilities, test_conf.payload_pattern)
    await check_micro_tpld(port_struct.capabilities, test_conf.use_micro_tpld_on_demand)
    await check_port_min_packet_length(
        port_struct.capabilities, min_packet_size, packet_size_type
    )
    await check_port_max_packet_length(
        port_struct.capabilities, max_packet_size, packet_size_type
    )
    await check_needed_packet_length(
        port_struct, min_packet_size, test_conf.use_micro_tpld_on_demand
    )
    await check_port_modifiers(
        port_struct.capabilities, port_struct.port_conf, is_stream_based
    )
    await check_stream_limitations(port_struct, per_port_stream_count, is_stream_based)


async def check_test_config(
    control_ports: List["PortStruct"], test_conf: "TestConfiguration"
) -> None:
    is_stream_based = test_conf.flow_creation_type.is_stream_based
    scope = test_conf.tid_allocation_scope
    await asyncio.gather(
        *[
            check_port_test_config(port_struct, test_conf)
            for port_struct in control_ports
        ]
    )

    check_tid_limitations(control_ports, scope, is_stream_based)


async def check_tester_sync_start(
    tester: "xoa_testers.L23Tester", use_sync_start: bool
) -> None:
    if not use_sync_start:
        return
    cap = await tester.capabilities.get()
    if not bool(cap.can_sync_traffic_start):
        raise exceptions.PortStaggeringNotSupport()


async def check_testers(
    testers: List["xoa_testers.L23Tester"], test_conf: "TestConfiguration"
) -> None:
    await asyncio.gather(
        *[
            check_tester_sync_start(tester, test_conf.use_port_sync_start)
            for tester in testers
        ]
    )


async def check_config(
    testers: List["xoa_testers.L23Tester"],
    control_ports: List["PortStruct"],
    test_conf: "TestConfiguration",
) -> None:
    await check_testers(testers, test_conf)
    await check_ports(control_ports)
    await check_test_config(control_ports, test_conf)
