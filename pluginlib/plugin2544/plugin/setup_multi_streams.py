from typing import List, Dict, Tuple

from ..utils.errors import ConfigError
from .structure import Structure, AddressCollection, StreamInfo
from ..model import TestConfiguration, MultiStreamConfig
from .common import get_mac_address_by_index, get_source_port_structs, TPLDControl
from ..utils.field import IPv4Address, IPv6Address


def get_address_collection(
    port_struct: "Structure",
    peer_struct: "Structure",
    src_offset: int,
    dest_offset: int,
    mac_base_address: str,
) -> "AddressCollection":
    port_network_v4 = port_struct.port_conf.ipv4_properties.address.network(
        port_struct.port_conf.ipv4_properties.routing_prefix
    )
    peer_network_v4 = peer_struct.port_conf.ipv4_properties.address.network(
        port_struct.port_conf.ipv4_properties.routing_prefix
    )
    port_network_v6 = port_struct.port_conf.ipv6_properties.address.network(
        port_struct.port_conf.ipv6_properties.routing_prefix
    )
    peer_network_v6 = peer_struct.port_conf.ipv6_properties.address.network(
        port_struct.port_conf.ipv6_properties.routing_prefix
    )
    return AddressCollection(
        smac_address=get_mac_address_by_index(mac_base_address, src_offset),
        dmac_address=get_mac_address_by_index(mac_base_address, dest_offset),
        src_ipv4_address=IPv4Address(port_network_v4[src_offset]),
        dest_ipv4_address=IPv4Address(peer_network_v4[dest_offset]),
        src_ipv6_address=IPv6Address(port_network_v6[src_offset]),
        dest_ipv6_address=IPv6Address(peer_network_v6[dest_offset]),
    )


def create_stream_for_multi_stream(
    port_struct: "Structure",
    peer_struct: "Structure",
    stream_id: int,
    tpld_controller: "TPLDControl",
    test_conf: "TestConfiguration",
    src_offset: int,
    dest_offset: int,
) -> "StreamInfo":
    tpldid = tpld_controller.get_tpldid(
        port_struct.properties.test_port_index, peer_struct.properties.test_port_index
    )
    if tpldid > port_struct.port.info.capabilities.max_tpid:
        raise ConfigError(f"current tpldid ({tpldid}) is larger than port capability ({port_struct.port.info.capabilities.max_tpid})")
    addr_coll = get_address_collection(
        port_struct,
        peer_struct,
        src_offset,
        dest_offset,
        test_conf.multi_stream_config.multi_stream_mac_base_address,
    )

    modifiers = [
        modifier
        for header_segment in port_struct.port_conf.profile.header_segments
        for modifier in header_segment.hw_modifiers
    ]
    return StreamInfo(
        flow_creation_type=test_conf.flow_creation_type,
        port_struct=port_struct,
        peer_struct=peer_struct,
        tpldid=tpldid,
        stream_id=stream_id,
        addr_coll=addr_coll,
        modifiers=modifiers,
        rx_ports=[peer_struct],
    )


def setup_multi_source_streams(
    control_ports: List["Structure"],
    tpld_controller: "TPLDControl",
    test_conf: "TestConfiguration",
    offset_table: Dict[Tuple[str, str], List[List[int]]],
) -> List["StreamInfo"]:
    stream_lists: List["StreamInfo"] = []
    source_port_structs = get_source_port_structs(control_ports)
    for port_struct in source_port_structs:
        stream_id_counter = 0
        for peer_struct in port_struct.properties.peers:
            peer_index = peer_struct.properties.identity
            offsets_list = get_stream_offsets(
                offset_table, port_struct.properties.identity, peer_index
            )
            if not offsets_list:
                raise ValueError("Offsets table calculate error")

            for offsets in offsets_list:
                stream_info = create_stream_for_multi_stream(
                    port_struct,
                    peer_struct,
                    stream_id_counter,
                    tpld_controller,
                    test_conf,
                    offsets[0],
                    offsets[1],
                )
                # stream_info.set_stream_id(stream_id_counter)
                stream_lists.append(stream_info)
                stream_id_counter += 1
    return stream_lists


def get_stream_offsets(
    offset_table: Dict[Tuple[str, str], List[List[int]]],
    port_index: str,
    peer_index: str,
) -> List[List[int]]:
    if (port_index, peer_index) in offset_table:
        return offset_table[(port_index, peer_index)]
    elif (peer_index, port_index) in offset_table:
        return [[v, k] for [k, v] in offset_table[(peer_index, port_index)]]
    return []


def setup_offset_table(
    control_ports: List["Structure"],
    multi_stream_config: "MultiStreamConfig",
) -> Dict[Tuple[str, str], List[List[int]]]:
    offset_table = {}
    offset = multi_stream_config.multi_stream_address_offset
    inc = multi_stream_config.multi_stream_address_increment
    source_port_structs = get_source_port_structs(control_ports)
    for port_struct in source_port_structs:
        port_index = port_struct.properties.identity
        for peer_struct in port_struct.properties.peers:
            peer_index = peer_struct.properties.identity
            if not (
                (port_index, peer_index) in offset_table
                or (peer_index, port_index) in offset_table
            ):
                offsets = []
                for i in range(multi_stream_config.per_port_stream_count):
                    offsets.append([offset, offset + inc])
                    offset += inc * 2
                offset_table[(port_index, peer_index)] = offsets
    return offset_table
