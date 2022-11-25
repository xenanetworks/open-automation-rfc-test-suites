from decimal import getcontext
from typing import Any, Dict, Tuple
from pydantic import BaseModel, validator
from .utils import exceptions, constants as const
from .model import (
    TestConfiguration,
    TestTypesConfiguration,
    PortConfiguration,
    ProtocolSegmentProfileConfig,
)


getcontext().prec = 6

ProtoSegType = Dict[str, ProtocolSegmentProfileConfig]
PortConfType = Dict[str, PortConfiguration]


class PluginModel2544(BaseModel):  # Main Model
    test_configuration: TestConfiguration
    protocol_segments: ProtoSegType
    ports_configuration: PortConfType
    test_types_configuration: TestTypesConfiguration

    def set_ports_rx_tx_type(self) -> None:
        direction = self.test_configuration.direction
        for config_index, port_config in self.ports_configuration.items():
            port_config.set_name(config_index)
            if port_config.is_loop:
                continue
            elif direction == const.TrafficDirection.EAST_TO_WEST:
                if port_config.port_group.is_east:
                    port_config.set_rx_port(False)
                elif port_config.port_group.is_west:
                    port_config.set_tx_port(False)
            elif direction == const.TrafficDirection.WEST_TO_EAST:
                if port_config.port_group.is_east:
                    port_config.set_tx_port(False)
                elif port_config.port_group.is_west:
                    port_config.set_rx_port(False)

    def set_profile(self) -> None:
        for port_config in self.ports_configuration.values():
            profile_id = port_config.profile_id
            port_config.set_profile(self.protocol_segments[profile_id].copy(deep=True))

    def __init__(self, **data: Dict[str, Any]) -> None:
        super().__init__(**data)
        self.set_ports_rx_tx_type()
        self.check_port_groups_and_peers()
        self.set_profile()

    @validator("ports_configuration", always=True)
    def check_ip_properties(cls, v: "PortConfType") -> "PortConfType":
        for _, port_config in v.items():
            if (
                port_config.profile.protocol_version.is_l3
                and port_config.ip_properties.address.is_empty
            ):
                raise exceptions.IPAddressMissing()
        return v

    @validator("ports_configuration", always=True)
    def check_port_count(
        cls, v: "PortConfType", values: Dict[str, Any]
    ) -> "PortConfType":
        require_ports = 2
        if "test_configuration" in values:
            topology: const.TestTopology = values["test_configuration"].topology
            if topology.is_pair_topology:
                require_ports = 1
            if len(v) < require_ports:
                raise exceptions.PortConfigNotEnough(require_ports)
        return v

    def check_port_groups_and_peers(self) -> None:
        topology = self.test_configuration.topology
        ports_in_east = ports_in_west = 0
        uses_port_peer = topology.is_pair_topology
        for port_config in self.ports_configuration.values():
            if not topology.is_mesh_topology:
                ports_in_east, ports_in_west = self.count_port_group(
                    port_config, uses_port_peer, ports_in_east, ports_in_west
                )
            if uses_port_peer:
                self.check_port_peer(port_config, self.ports_configuration)
        if not topology.is_mesh_topology:
            for i, group in (ports_in_east, "East"), (ports_in_west, "West"):
                if not i:
                    raise exceptions.PortGroupError(group)

    @validator("ports_configuration", always=True)
    def check_modifier_mode_and_segments(
        cls, v: "PortConfType", values: Dict[str, Any]
    ) -> "PortConfType":
        if "test_configuration" in values:
            flow_creation_type = values["test_configuration"].flow_creation_type
            for _, port_config in v.items():
                if (
                    not flow_creation_type.is_stream_based
                ) and port_config.profile.protocol_version.is_l3:
                    raise exceptions.ModifierBasedNotSupportL3()
        return v

    @validator("ports_configuration", always=True)
    def check_port_group(
        cls, v: "PortConfiguration", values: Dict[str, Any]
    ) -> "PortConfiguration":
        if "ports_configuration" in values and "test_configuration" in values:
            for k, p in values["ports_configuration"].items():
                if (
                    p.port_group == const.PortGroup.UNDEFINED
                    and not values["test_configuration"].topology.is_mesh_topology
                ):
                    raise exceptions.PortGroupNeeded()
        return v

    @validator("test_types_configuration", always=True)
    def check_test_type_enable(
        cls, v: "TestTypesConfiguration"
    ) -> "TestTypesConfiguration":
        if not any(
            {
                v.throughput_test.enabled,
                v.latency_test.enabled,
                v.frame_loss_rate_test.enabled,
                v.back_to_back_test.enabled,
            }
        ):
            raise exceptions.TestTypesError()
        return v

    @validator("test_types_configuration", always=True)
    def check_result_scope(
        cls, v: "TestTypesConfiguration", values: Dict[str, Any]
    ) -> "TestTypesConfiguration":
        if "test_configuration" not in values:
            return v
        if (
            v.throughput_test.enabled
            and v.throughput_test.rate_iteration_options.result_scope
            == const.RateResultScopeType.PER_SOURCE_PORT
            and not values["test_configuration"].flow_creation_type.is_stream_based
        ):
            raise exceptions.ModifierBasedNotSupportPerPortResult()
        return v

    @staticmethod
    def count_port_group(
        port_config: "PortConfiguration",
        uses_port_peer: bool,
        ports_in_east: int,
        ports_in_west: int,
    ) -> Tuple[int, int]:
        if port_config.port_group.is_east:
            ports_in_east += 1
            if uses_port_peer and port_config.is_loop:
                ports_in_west += 1

        elif port_config.port_group.is_west:
            ports_in_west += 1
            if uses_port_peer and port_config.is_loop:
                ports_in_east += 1

        return ports_in_east, ports_in_west

    @staticmethod
    def check_port_peer(
        port_config: "PortConfiguration",
        ports_configuration: Dict[str, "PortConfiguration"],
    ) -> None:
        peer_config_slot = port_config.peer_config_slot
        if not peer_config_slot or peer_config_slot not in ports_configuration:
            raise exceptions.PortPeerNeeded()
        peer_config = ports_configuration[peer_config_slot]
        if not port_config.is_pair(peer_config) or not peer_config.is_pair(port_config):
            raise exceptions.PortPeerInconsistent()

    @property
    def in_same_ipnetwork(self) -> bool:
        networks = set(
            [
                p.ip_properties.address.network(p.ip_properties.routing_prefix)
                for p in self.ports_configuration.values()
            ]
        )
        return len(networks) == 1

    @property
    def with_same_gateway(self) -> bool:
        gateways = set(
            [p.ip_properties.gateway for p in self.ports_configuration.values()]
        )
        return len(gateways) == 1
