from typing import TYPE_CHECKING, List

from ..utils.exceptions import ConfigError
from ..model import (
    HwModifier,
    TestConfiguration,
)
from .structure import AddressCollection, StreamInfo
from .common import get_source_port_structs, get_usable_dest_ip_address
from .stream_base_settings import (
    get_modifier_range_by_test_port_index,
    get_rx_ports_by_range,
)
from ..utils.constants import FlowCreationType
from ..utils.field import IPv4Address, IPv6Address

if TYPE_CHECKING:
    from .control_ports import Structure
    from .common import TPLDControl


def setup_standard_streams(
    control_ports: List["Structure"],
    tpld_controller: "TPLDControl",
    test_conf: "TestConfiguration",
) -> List["StreamInfo"]:
    stream_lists: List["StreamInfo"] = []
    source_port_structs = get_source_port_structs(control_ports)
    for port_struct in source_port_structs:

        stream_id_counter = 0
        if test_conf.flow_creation_type.is_stream_based:
            for peer_struct in port_struct.properties.peers:
                stream_info = create_stream_for_stream_base(
                    port_struct, peer_struct, stream_id_counter, tpld_controller
                )
                stream_lists.append(stream_info)
                stream_id_counter += 1
        else:
            for i in range(port_struct.properties.num_modifiersL2):
                stream_info = create_stream_for_modifier_mode(
                    control_ports, port_struct, stream_id_counter
                )
                stream_lists.append(stream_info)
                stream_id_counter += 1
    return stream_lists


def create_stream_for_modifier_mode(
    control_ports: List["Structure"], port_struct: "Structure", stream_id: int
) -> "StreamInfo":
    tpldid = 2 * port_struct.properties.test_port_index + stream_id

    addr_coll = AddressCollection(
        smac_address=port_struct.properties.mac_address,
        dmac_address=port_struct.properties.mac_address,
        src_ipv4_address=IPv4Address(port_struct.port_conf.ipv4_properties.address),
        dest_ipv4_address=IPv4Address(
            get_usable_dest_ip_address(port_struct.port_conf.ipv4_properties)
        ),
        src_ipv6_address=IPv6Address(port_struct.port_conf.ipv6_properties.address),
        dest_ipv6_address=IPv6Address(
            get_usable_dest_ip_address(port_struct.port_conf.ipv6_properties)
        ),
    )

    modifier_range = get_modifier_range_by_test_port_index(port_struct, stream_id)
    rx_ports = get_rx_ports_by_range(control_ports, modifier_range)
    new_modifier = HwModifier(
        field_name="Dst MAC addr",
        offset=4,
        mask="0x00FF0000",
        start_value=modifier_range[0],
        stop_value=modifier_range[1],
    )
    return StreamInfo(
        flow_creation_type=FlowCreationType.MODIFIER,
        port_struct=port_struct,
        peer_struct=port_struct,
        stream_id=stream_id,
        tpldid=tpldid,
        addr_coll=addr_coll,
        modifiers=[new_modifier],
        rx_ports=rx_ports,
    )


def create_stream_for_stream_base(
    port_struct: "Structure",
    peer_struct: "Structure",
    stream_id: int,
    tpld_controller: "TPLDControl",
) -> "StreamInfo":
    tpldid = tpld_controller.get_tpldid(
        port_struct.properties.test_port_index, peer_struct.properties.test_port_index
    )
    if tpldid > port_struct.port.info.capabilities.max_tpid:
        raise ConfigError(f"current tpldid ({tpldid}) is larger than port capability ({port_struct.port.info.capabilities.max_tpid})")
    addr_coll = AddressCollection(
        smac_address=port_struct.properties.mac_address,
        dmac_address=peer_struct.properties.mac_address,
        src_ipv4_address=IPv4Address(port_struct.port_conf.ipv4_properties.address),
        dest_ipv4_address=IPv4Address(
            get_usable_dest_ip_address(port_struct.port_conf.ipv4_properties)
        ),
        src_ipv6_address=IPv6Address(port_struct.port_conf.ipv6_properties.address),
        dest_ipv6_address=IPv6Address(
            get_usable_dest_ip_address(port_struct.port_conf.ipv6_properties)
        ),
    )

    modifiers = [
        modifier
        for header_segment in port_struct.port_conf.profile.header_segments
        for modifier in header_segment.hw_modifiers
    ]
    return StreamInfo(
        flow_creation_type=FlowCreationType.STREAM,
        port_struct=port_struct,
        peer_struct=peer_struct,
        stream_id=stream_id,
        tpldid=tpldid,
        addr_coll=addr_coll,
        modifiers=modifiers,
        rx_ports=[peer_struct],
    )
