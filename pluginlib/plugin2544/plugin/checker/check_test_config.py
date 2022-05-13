import asyncio
from typing import TYPE_CHECKING, List, Union
from pluginlib.plugin2544.utils import field, exceptions, constants as const
from pluginlib.plugin2544.plugin.common import (
    get_dest_port_structs,
    get_tpld_total_length,
)

if TYPE_CHECKING:
    from xoa_driver.ports import GenericL23Port
    from pluginlib.plugin2544.plugin.structure import (
        Structure,
    )
    from pluginlib.plugin2544.model import (
        PortConfiguration,
        TestConfiguration,
    )


async def check_port_modifiers(
    port: "GenericL23Port",
    port_conf: "PortConfiguration",
    is_stream_based: bool,
) -> None:
    if not port_conf.is_tx_port:
        return

    modifier_count = port_conf.profile.modifier_count
    if is_stream_based:
        if modifier_count > port.info.capabilities.max_modifiers:
            raise exceptions.ModifierExceed(
                modifier_count, port.info.capabilities.max_modifiers
            )
    else:
        if modifier_count > 0:
            raise exceptions.ModifierBasedNotSupportDefineModifier()


async def check_stream_limitations(
    port_struct: "Structure", per_port_stream_count: int, is_stream_based: bool
) -> None:
    if not is_stream_based:
        return
    if not port_struct.port_conf.is_tx_port:
        return
    stream_count = len(port_struct.properties.peers) * per_port_stream_count
    if stream_count > port_struct.port.info.capabilities.max_streams_per_port:
        raise exceptions.StreamExceed(
            stream_count, port_struct.port.info.capabilities.max_streams_per_port
        )


def count_source_port(
    control_ports: List["Structure"], peer_struct: "Structure"
) -> int:
    count = 0
    for port_struct in control_ports:
        if peer_struct in port_struct.properties.peers:
            count += 1
    return count


def check_tid_limitations(
    control_ports: List["Structure"],
    scope: "const.TidAllocationScope",
    is_stream_based: bool,
) -> None:
    if not is_stream_based:
        return
    if not scope.is_config_scope:
        return

    tid_value = 0
    dest_port_structs = get_dest_port_structs(control_ports)
    for peer_struct in dest_port_structs:
        src_port_count = count_source_port(control_ports, peer_struct)
        tid_value += src_port_count
        max_tpld_stats = peer_struct.port.info.capabilities.max_tpld_stats
        if tid_value > max_tpld_stats:
            raise exceptions.TPLDIDExceed(tid_value, max_tpld_stats)


async def check_port_min_packet_length(
    port: "GenericL23Port",
    min_packet_size: Union[field.NonNegativeDecimal, int],
    packet_size_type: "const.PacketSizeType",
) -> None:
    if port.info.capabilities.min_packet_length > min_packet_size:
        raise exceptions.MinPacketLengthExceed(
            packet_size_type.value,
            int(min_packet_size),
            port.info.capabilities.min_packet_length,
        )


async def check_port_max_packet_length(
    port: "GenericL23Port",
    max_packet_size: Union[field.NonNegativeDecimal, int],
    packet_size_type: "const.PacketSizeType",
) -> None:
    if port.info.capabilities.max_packet_length < max_packet_size:
        raise exceptions.MaxPacketLengthExceed(
            packet_size_type.value,
            int(max_packet_size),
            port.info.capabilities.max_packet_length,
        )


def get_needed_packet_length(
    port_struct: "Structure", use_micro_tpld_on_demand: bool
) -> int:
    packet_header_length = port_struct.port_conf.profile.packet_header_length
    return packet_header_length + get_tpld_total_length(
        port_struct.port, use_micro_tpld_on_demand
    )


async def check_needed_packet_length(
    port_struct: "Structure",
    min_packet_size: Union[field.NonNegativeDecimal, int],
    use_micro_tpld_on_demand: bool,
) -> None:
    need_packet_length = get_needed_packet_length(port_struct, use_micro_tpld_on_demand)
    if min_packet_size < need_packet_length:
        raise exceptions.PacketSizeTooSmall(int(min_packet_size), need_packet_length)


async def check_payload_pattern(port: "GenericL23Port", payload_pattern: str) -> None:
    cur = len(payload_pattern) // 2
    if port.info.capabilities.max_pattern_length < cur:
        raise exceptions.PayloadPatternExceed(
            cur, port.info.capabilities.max_pattern_length
        )


async def check_micro_tpld(port: "GenericL23Port", use_mocro_tpld: bool) -> None:
    if not use_mocro_tpld:
        return
    if not bool(port.info.capabilities.can_micro_tpld):
        raise exceptions.MicroTPLDNotSupport()


async def check_port_test_config(
    port_struct: "Structure", test_conf: "TestConfiguration"
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
    await check_payload_pattern(port_struct.port, test_conf.payload_pattern)
    await check_micro_tpld(port_struct.port, test_conf.use_micro_tpld_on_demand)
    await check_port_min_packet_length(
        port_struct.port, min_packet_size, packet_size_type
    )
    await check_port_max_packet_length(
        port_struct.port, max_packet_size, packet_size_type
    )
    await check_needed_packet_length(
        port_struct, min_packet_size, test_conf.use_micro_tpld_on_demand
    )
    await check_port_modifiers(port_struct.port, port_struct.port_conf, is_stream_based)
    await check_stream_limitations(port_struct, per_port_stream_count, is_stream_based)


async def check_test_config(
    control_ports: List["Structure"], test_conf: "TestConfiguration"
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
