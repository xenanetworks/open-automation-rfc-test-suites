from typing import List, TYPE_CHECKING
from pluginlib.plugin2544.plugin.common import filter_port_structs, get_peers_for_source

if TYPE_CHECKING:
    from .structure import Structure
    from pluginlib.plugin2544.utils import constants as const


def resolve_port_relations_main(
    topology: "const.TestTopology",
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
            if port_struct.port_conf.port_group.is_east
        ]
        west_ports = [
            port_struct
            for port_struct in control_ports
            if port_struct.port_conf.port_group.is_west
        ]
        for port_struct in east_ports:
            port_struct.properties.change_test_port_index(test_port_index)
            test_port_index += 1
        for port_struct in west_ports:
            port_struct.properties.change_test_port_index(test_port_index)
            test_port_index += 1

    source_port_structs = filter_port_structs(control_ports)
    for port_struct in source_port_structs:
        port_config = port_struct.port_conf
        dest_ports = get_peers_for_source(topology, port_config, control_ports)
        for peer_struct in dest_ports:
            port_struct.properties.register_peer(peer_struct)
