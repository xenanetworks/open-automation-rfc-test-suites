import re
from typing import TYPE_CHECKING, Dict, List, Tuple, Union
from ..utils.field import MacAddress, IPv4Address, IPv6Address
from ..utils.constants import (
    ARPSenarioType,
    TidAllocationScope,
    TestTopology,
    MICRO_TPLD_TOTAL_LENGTH,
    STANDARD_TPLD_TOTAL_LENGTH,
)

from xoa_driver.enums import ProtocolOption

if TYPE_CHECKING:
    from xoa_driver.ports import GenericL23Port
    from .structure import Structure
    from ..model import PortConfiguration, IPV4AddressProperties, IPV6AddressProperties


async def get_native_mac_address(port: "GenericL23Port") -> "MacAddress":
    mac_address = (await port.net_config.mac_address.get()).mac_address
    return MacAddress(mac_address)


def get_mac_address_by_index(first_three_bytes: str, index: int) -> "MacAddress":
    hex_num = hex(index)[2:].zfill(6)
    last_three_bytes = ":".join(re.findall(r".{2}", hex_num))
    return MacAddress(f"{first_three_bytes}:{last_three_bytes}")


async def setup_macaddress(
    port_struct: "Structure", is_stream_based: bool, mac_base_address: str
) -> None:
    if is_stream_based:
        port_struct.properties.change_mac_address(
            await get_native_mac_address(port_struct.port)
        )
    else:
        # mac address according to test_port_index
        port_struct.properties.change_mac_address(
            get_mac_address_by_index(
                mac_base_address, port_struct.properties.test_port_index
            )
        )


def is_same_ipnetwork(port_struct: "Structure", peer_struct: "Structure") -> bool:
    port_properties = port_struct.port_conf.ip_properties
    peer_properties = peer_struct.port_conf.ip_properties
    if not port_properties or not peer_properties:
        raise ValueError("Please check IP properties values")
    return port_properties.network == peer_properties.network


def get_pair_address(
    port_struct: "Structure", peer_struct: "Structure", use_gateway_mac_as_dmac: bool
) -> Tuple[Union["IPv4Address", "IPv6Address"], "ARPSenarioType"]:
    port_conf = port_struct.port_conf
    ip_properties = port_conf.ip_properties

    if not ip_properties:
        raise ValueError("Please check IP properties")
    peer_conf = peer_struct.port_conf
    peer_ip_properties = peer_conf.ip_properties
    if not peer_ip_properties:
        raise ValueError("Please check peer IP properties")
    senario_type = ARPSenarioType.DEFAULT
    destination_ip = peer_ip_properties.address
    peer_conf = peer_struct.port_conf
    if use_gateway_mac_as_dmac and port_conf.profile.protocol_version.is_l3:
        if (
            not is_same_ipnetwork(port_struct, peer_struct)
            and not ip_properties.gateway == peer_ip_properties.gateway
        ):
            destination_ip = ip_properties.gateway
            senario_type = ARPSenarioType.GATEWAY
        elif ip_properties.gateway.is_empty and ip_properties.remote_loop_address:
            destination_ip = ip_properties.remote_loop_address
            senario_type = ARPSenarioType.REMOTE
        else:
            destination_ip = peer_ip_properties.public_address
            senario_type = ARPSenarioType.PUBLIC
    return destination_ip, senario_type


def is_byte_values_zero(array: bytearray, start: int = 0, length: int = 0) -> bool:
    if length == 0:
        length = len(array)
    if len(array) < start + length:
        return False

    for i in range(start, start + length):
        if array[i] != 0:
            return False
    return True


def copy_to(src: bytearray, dest: bytearray, start_from: int) -> None:
    length = len(src)
    if start_from < 0:
        start_from = len(dest) + start_from
    dest[start_from : start_from + length] = src


class TPLDControl:
    # TPLD is relative to test port index
    def __init__(self, tid_scope: "TidAllocationScope") -> None:
        self.curr_tpld_index = 0
        self.curr_tpld_map: Dict[int, int] = {}
        self.tid_scope = tid_scope

    def config_scope_add(self) -> int:
        next_index = self.curr_tpld_index
        self.curr_tpld_index += 1
        return next_index

    def port_scope_add(self, peer_index: int) -> int:
        if peer_index not in self.curr_tpld_map:
            self.curr_tpld_map[peer_index] = 0
        next_index = self.curr_tpld_map[peer_index]
        self.curr_tpld_map[peer_index] += 1
        return next_index

    def src_port_id_add(self, port_index: int) -> int:
        return port_index

    def get_tpldid(self, port_index: int, peer_index: int) -> int:
        if self.tid_scope == TidAllocationScope.CONFIGURATION_SCOPE:
            return self.config_scope_add()
        elif self.tid_scope == TidAllocationScope.RX_PORT_SCOPE:
            return self.port_scope_add(peer_index)
        else:
            return self.src_port_id_add(port_index)


def is_port_pair(
    port_config: "PortConfiguration", peer_config: "PortConfiguration"
) -> bool:
    return (
        True if port_config.peer_config_slot == peer_config.port_config_slot else False
    )


def is_peer_port(
    topology: "TestTopology",
    port_config: "PortConfiguration",
    peer_config: "PortConfiguration",
) -> bool:
    if topology == TestTopology.PAIRS:
        return is_port_pair(port_config, peer_config)
    elif topology == TestTopology.BLOCKS:
        return port_config.port_group != peer_config.port_group
    elif topology == TestTopology.MESH:
        return port_config.port_config_slot != peer_config.port_config_slot
    else:
        raise Exception(f"illegal topology! {topology}")


def get_peers_for_source(
    topology: "TestTopology",
    port_config: "PortConfiguration",
    control_ports: List["Structure"],
) -> List["Structure"]:
    dest_ports = []
    for peer_struct in control_ports:
        peer_config = peer_struct.port_conf
        if not peer_config.is_rx_port:
            continue
        if is_peer_port(topology, port_config, peer_config):
            dest_ports.append(peer_struct)
    return dest_ports


def filter_port_structs(
    control_ports: List["Structure"], is_source_port: bool = True
) -> List["Structure"]:
    return [
        port_struct
        for port_struct in control_ports
        if (is_source_port and port_struct.port_conf.is_tx_port)
        or (not is_source_port and port_struct.port_conf.is_rx_port)
    ]


def get_usable_dest_ip_address(
    ip_properties: Union["IPV4AddressProperties", "IPV6AddressProperties"]
) -> Union["IPv4Address", "IPv6Address"]:
    public_ip_address = ip_properties.public_address
    public_ip_address_empty = ip_properties.public_address.is_empty
    address = ip_properties.address
    return public_ip_address if not public_ip_address_empty else address


def get_tpld_total_length(
    port: "GenericL23Port", use_micro_tpld_on_demand: bool
) -> int:
    if use_micro_tpld_on_demand and port.info.capabilities.can_micro_tpld:
        return MICRO_TPLD_TOTAL_LENGTH
    return STANDARD_TPLD_TOTAL_LENGTH


def may_change_segment_id_list(
    port: "GenericL23Port", segment_id_list: List[ProtocolOption]
) -> List[ProtocolOption]:
    id_list_copy = segment_id_list[:]
    for i, segment_id in enumerate(segment_id_list):
        if segment_id == ProtocolOption.TCP and port.info.capabilities.can_tcp_checksum:
            id_list_copy[i] = ProtocolOption.TCPCHECK
    return id_list_copy
