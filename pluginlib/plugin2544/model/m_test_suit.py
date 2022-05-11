from decimal import getcontext
from typing import Dict,  Tuple
from pydantic import (
    BaseModel,
    validator,
)

from .m_test_config import TestConfiguration
from .m_port_config import  PortConfiguration
from .m_protocol_segment import ProtocolSegmentProfileConfig
from .m_test_type_config import TestTypesConfiguration
from ..utils.constants import (
    RateResultScopeType,
    PortGroup,
    TrafficDirection,
)
from ..utils.errors import ConfigError

getcontext().prec = 6

class Model2544(BaseModel):  # Main Model
    test_configuration: TestConfiguration
    protocol_segments: Dict[str, ProtocolSegmentProfileConfig]
    ports_configuration: Dict[str, PortConfiguration]
    test_types_configuration: TestTypesConfiguration

    # Computed Properties
    in_same_ipnetwork: bool = False
    with_same_gateway: bool = False
    has_l3: bool = False

    @validator("ports_configuration", always=True)
    def set_ports_rx_tx_type(cls, v, values):
        if "test_configuration" in values:
            direction = values["test_configuration"].direction
            for config_index, port in v.items():
                if not port.port_config_slot:
                    port.port_config_slot = config_index
                if port.port_config_slot == port.peer_config_slot:
                    pass
                elif direction == TrafficDirection.EAST_TO_WEST:
                    if port.port_group.is_east:
                        port.is_rx_port = False
                    elif port.port_group.is_west:
                        port.is_tx_port = False
                elif direction == TrafficDirection.WEST_TO_EAST:
                    if port.port_group.is_east:
                        port.is_tx_port = False
                    elif port.port_group.is_west:
                        port.is_rx_port = False
        return v

    @validator("ports_configuration", always=True)
    def set_ip_properties(cls, v, values):
        if "protocol_segments" in values:
            for _, port_config in v.items():
                profile_id = port_config.profile_id
                port_config.profile = values["protocol_segments"][profile_id]
                if port_config.profile.protocol_version.is_ipv4:
                    port_config.ip_properties = port_config.ipv4_properties
                elif port_config.profile.protocol_version.is_ipv6:
                    port_config.ip_properties = port_config.ipv6_properties
                if (
                    port_config.profile.protocol_version.is_l3
                    and port_config.ip_properties.address.is_empty
                ):
                    raise ConfigError("You must assign an IP address to the port!")
        return v

    @validator("ports_configuration", always=True)
    def check_port_count(cls, v, values):
        require_ports = 2
        if "test_configuration" in values:
            topology = values["test_configuration"].topology
            if topology.is_pair_topology:
                require_ports = 1
            if len(v) < require_ports:
                raise ConfigError(
                    f"The configuration must have at least {require_ports} testport{'s'  if require_ports > 1 else ''}!"
                )
        return v

    @validator("ports_configuration", always=True)
    def check_port_groups_and_peers(cls, v, values):
        if "test_configuration" in values:
            topology = values["test_configuration"].topology
            ports_in_east = 0
            ports_in_west = 0
            uses_port_peer = topology.is_pair_topology
            for _, port_config in v.items():
                if not topology.is_mesh_topology:
                    ports_in_east, ports_in_west = cls.count_port_group(
                        port_config, uses_port_peer, ports_in_east, ports_in_west
                    )
                if uses_port_peer:
                    cls.check_port_peer(port_config, v)
            if not topology.is_mesh_topology:
                for i, s in (ports_in_east, "East"), (ports_in_west, "West"):
                    if not i:
                        raise ConfigError(
                            f"At least one port must be assigned to the {s} port group!"
                        )
        return v

    @validator("ports_configuration", always=True)
    def check_modifier_mode_and_segments(cls, v, values):
        if "test_configuration" in values:
            flow_creation_type = values["test_configuration"].flow_creation_type
            for _, port_config in v.items():
                if (
                    not flow_creation_type.is_stream_based
                ) and port_config.profile.protocol_version.is_l3:
                    raise ConfigError(
                        f"Cannot use modifier-based flow creation for layer-3 tests!"
                    )
        return v

    @validator("test_types_configuration", always=True)
    def check_test_type_enable(cls, v, values):
        if not any(
            {
                v.throughput_test.enabled,
                v.latency_test.enabled,
                v.frame_loss_rate_test.enabled,
                v.back_to_back_test.enabled,
            }
        ):
            raise ConfigError("You have not enabled any test types.")
        return v

    @validator("test_types_configuration", always=True)
    def check_result_scope(cls, v, values):
        if not "test_configuration" in values:
            return v
        if (
            v.throughput_test.enabled
            and v.throughput_test.rate_iteration_options.result_scope
            == RateResultScopeType.PER_SOURCE_PORT
            and not values["test_configuration"].flow_creation_type.is_stream_based
        ):
            raise ConfigError(
                "Cannot use per-port result for modifier-based flows."
            )
        return v





    @staticmethod
    def count_port_group(
        port_config: "PortConfiguration",
        uses_port_peer: bool,
        ports_in_east: int,
        ports_in_west: int,
    ) -> Tuple[int, int]:
        is_looped = port_config.port_config_slot == port_config.peer_config_slot
        if port_config.port_group.is_east:
            ports_in_east += 1
            if uses_port_peer and is_looped:
                ports_in_west += 1

        elif port_config.port_group.is_west:
            ports_in_west += 1
            if uses_port_peer and is_looped:
                ports_in_east += 1

        return ports_in_east, ports_in_west

    @staticmethod
    def check_port_peer(
        port_config: "PortConfiguration",
        ports_configuration: Dict[str, "PortConfiguration"],
    ):
        peer_config_slot = port_config.peer_config_slot
        if not peer_config_slot:
            raise ConfigError("You must assign a peer to the port!")
        if (
            peer_config_slot not in ports_configuration
            or ports_configuration[peer_config_slot].peer_config_slot
            != port_config.port_config_slot
        ):
            raise ConfigError("Inconsistent port peer definition!")

    @validator("in_same_ipnetwork", always=True)
    def set_in_same_ipnetwork(cls, v, values):
        if "ports_configuration" in values:
            conf = values["ports_configuration"]
            networks = set(
                [
                    p.ip_properties.address.network(p.ip_properties.routing_prefix)
                    for p in conf.values()
                ]
            )

            v = len(networks) == 1
        return v

    @validator("with_same_gateway", always=True)
    def set_with_same_gateway(cls, v, values):
        if "ports_configuration" in values:
            confs = values["ports_configuration"]
            gateways = set([p.ip_properties.gateway for p in confs.values()])
            v = len(gateways) == 1
        return v

    @validator("has_l3", always=True)
    def set_has_l3(cls, v, values):
        if "ports_configuration" in values:
            confs = values["ports_configuration"]
            return any([conf.profile.protocol_version.is_l3 for conf in confs.values()])
        return False

    @validator("ports_configuration", always=True)
    def check_port_group(cls, v, values):
        if "ports_configuration" in values and "test_configuration" in values:
            for k, p in values["ports_configuration"].items():
                if (
                    p.port_group == PortGroup.UNDEFINED
                    and not values["test_configuration"].topology.is_mesh_topology
                ):
                    raise ConfigError("You must assign the port to a port group!")
        return v