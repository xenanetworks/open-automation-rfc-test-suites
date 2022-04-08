from ..utils.constants import PortGroup
from typing import List, TYPE_CHECKING
from .common import get_source_port_structs, get_peers_for_source

if TYPE_CHECKING:
    from .structure import Structure
    from ..model import TestTopology


def resolve_port_relations_main(
    topology: "TestTopology",
    control_ports: List["Structure"],
) -> None:
    test_port_index = 0
    if topology.is_mesh_topology:
        for port_struct in control_ports:
            port_struct.properties.change_test_port_index(test_port_index)
            test_port_index += 1
    else:
        east_ports = [
            port_struct
            for port_struct in control_ports
            if port_struct.port_conf.port_group == PortGroup.EAST
        ]
        west_ports = [
            port_struct
            for port_struct in control_ports
            if port_struct.port_conf.port_group == PortGroup.WEST
        ]
        for port_struct in east_ports:
            port_struct.properties.change_test_port_index(test_port_index)
            test_port_index += 1
        for port_struct in west_ports:
            port_struct.properties.change_test_port_index(test_port_index)
            test_port_index += 1

    source_port_structs = get_source_port_structs(control_ports)
    for port_struct in source_port_structs:
        port_config = port_struct.port_conf
        dest_ports = get_peers_for_source(topology, port_config, control_ports)
        for peer_struct in dest_ports:
            port_struct.properties.register_peer(peer_struct)
