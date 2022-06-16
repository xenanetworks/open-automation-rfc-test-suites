import re
from typing import TYPE_CHECKING, Dict, List, Tuple, Union
from ..utils.field import MacAddress, IPv4Address, IPv6Address
from ..utils.constants import (
    ARPSenarioType,
    TidAllocationScope,
    TestTopology,
)


if TYPE_CHECKING:
    from .structure import PortStruct
    from ..model import PortConfiguration


def gen_macaddress(first_three_bytes: str, index: int) -> "MacAddress":
    hex_num = hex(index)[2:].zfill(6)
    last_three_bytes = ":".join(re.findall(r".{2}", hex_num))
    return MacAddress(f"{first_three_bytes}:{last_three_bytes}")


def is_same_ipnetwork(port_struct: "PortStruct", peer_struct: "PortStruct") -> bool:
    port_properties = port_struct.port_conf.ip_properties
    peer_properties = peer_struct.port_conf.ip_properties
    if not port_properties or not peer_properties:
        raise ValueError("Please check IP properties values")
    return port_properties.network == peer_properties.network


def get_pair_address(
    port_struct: "PortStruct", peer_struct: "PortStruct", use_gateway_mac_as_dmac: bool
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
        True
        if port_config.is_pair(peer_config) and peer_config.is_pair(port_config)
        else False
    )


def is_peer_port(
    topology: "TestTopology",
    port_config: "PortConfiguration",
    peer_config: "PortConfiguration",
) -> bool:
    if topology.is_pair_topology:
        return is_port_pair(port_config, peer_config)
    elif topology.is_mesh_topology:
        return port_config != peer_config
    else:
        return port_config.port_group != peer_config.port_group


def get_peers_for_source(
    topology: "TestTopology",
    port_config: "PortConfiguration",
    control_ports: List["PortStruct"],
) -> List["PortStruct"]:
    dest_ports = []
    for peer_struct in control_ports:
        peer_config = peer_struct.port_conf
        if not peer_config.is_rx_port:
            continue
        if is_peer_port(topology, port_config, peer_config):
            dest_ports.append(peer_struct)
    return dest_ports


def filter_port_structs(
    control_ports: List["PortStruct"], is_source_port: bool = True
) -> List["PortStruct"]:
    return [
        port_struct
        for port_struct in control_ports
        if (is_source_port and port_struct.port_conf.is_tx_port)
        or (not is_source_port and port_struct.port_conf.is_rx_port)
    ]


