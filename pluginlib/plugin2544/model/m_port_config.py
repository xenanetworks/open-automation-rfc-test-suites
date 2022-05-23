from ipaddress import IPv4Network, IPv6Network
from typing import Union
from decimal import Decimal
from pydantic import (
    BaseModel,
    validator,
    NonNegativeInt,
)

from pluginlib.plugin2544.utils import exceptions
from ..utils import constants as const
from ..utils.field import MacAddress, IPv4Address, IPv6Address, Prefix
from .m_protocol_segment import ProtocolSegmentProfileConfig


class IPV6AddressProperties(BaseModel):
    address: IPv6Address = IPv6Address("::")
    routing_prefix: Prefix = Prefix(24)
    public_address: IPv6Address = IPv6Address("::")
    public_routing_prefix: Prefix = Prefix(24)
    gateway: IPv6Address = IPv6Address("::")
    remote_loop_address: IPv6Address = IPv6Address("::")
    ip_version: const.IPVersion = const.IPVersion.IPV6

    @property
    def network(self) -> IPv6Network:
        return IPv6Network(f"{self.address}/{self.routing_prefix}", strict=False)

    @validator("address", "public_address", "gateway", "remote_loop_address", pre=True)
    def set_address(cls, v) -> IPv6Address:
        return IPv6Address(v)

    @validator("routing_prefix", "public_routing_prefix", pre=True)
    def set_prefix(cls, v) -> Prefix:
        return Prefix(v)


class IPV4AddressProperties(BaseModel):
    address: IPv4Address = IPv4Address("0.0.0.0")
    routing_prefix: Prefix = Prefix(24)
    public_address: IPv4Address = IPv4Address("0.0.0.0")
    public_routing_prefix: Prefix = Prefix(24)
    gateway: IPv4Address = IPv4Address("0.0.0.0")
    remote_loop_address: IPv4Address = IPv4Address("0.0.0.0")
    ip_version: const.IPVersion = const.IPVersion.IPV4

    @property
    def network(self) -> IPv4Network:
        return IPv4Network(f"{self.address}/{self.routing_prefix}", strict=False)

    @validator("address", "public_address", "gateway", "remote_loop_address", pre=True)
    def set_address(cls, v) -> IPv4Address:
        return IPv4Address(v)

    @validator("routing_prefix", "public_routing_prefix", pre=True)
    def set_prefix(cls, v) -> Prefix:
        return Prefix(v)


class PortConfiguration(BaseModel):
    port_slot: str
    peer_config_slot: str
    port_group: const.PortGroup
    port_speed_mode: const.PortSpeedStr

    # PeerNegotiation
    auto_neg_enabled: bool
    anlt_enabled: bool
    mdi_mdix_mode: const.MdiMdixMode
    broadr_reach_mode: const.BRRModeStr

    # PortRateCap
    # port_rate_cap_enabled: bool
    port_rate_cap_value: float
    port_rate_cap_profile: const.PortRateCapProfile
    port_rate_cap_unit: const.PortRateCapUnit

    # PhysicalPortProperties
    inter_frame_gap: NonNegativeInt
    speed_reduction_ppm: NonNegativeInt
    pause_mode_enabled: bool
    latency_offset_ms: int  # QUESTION: can be negative?
    fec_mode: const.FECModeStr

    profile_id: str

    ip_gateway_mac_address: MacAddress
    reply_arp_requests: bool
    reply_ping_requests: bool
    remote_loop_mac_address: MacAddress
    ipv4_properties: IPV4AddressProperties
    ipv6_properties: IPV6AddressProperties

    _profile: ProtocolSegmentProfileConfig = ProtocolSegmentProfileConfig()
    _port_config_slot: str = ""
    _is_tx: bool = True
    _is_rx: bool = True

    class Config:
        underscore_attrs_are_private = True

    @property
    def is_tx_port(self) -> bool:
        return self._is_tx

    def set_tx_port(self, value: bool) -> None:
        self._is_tx = value

    @property
    def is_rx_port(self) -> bool:
        return self._is_rx

    def set_rx_port(self, value: bool) -> None:
        self._is_rx = value

    @property
    def is_loop(self) -> bool:
        return self._port_config_slot == self.peer_config_slot

    def is_pair(self, peer_config: "PortConfiguration") -> bool:
        return peer_config.peer_config_slot == self._port_config_slot

    def set_name(self, name: str) -> None:
        self._port_config_slot = name

    @property
    def port_rate(self) -> Decimal:
        return Decimal(self.port_rate_cap_value * self.port_rate_cap_unit.scale())

    @property
    def profile(self) -> ProtocolSegmentProfileConfig:
        return self._profile

    def set_profile(self, value: ProtocolSegmentProfileConfig) -> None:
        self._profile = value

    @property
    def ip_properties(self) -> Union[IPV4AddressProperties, IPV6AddressProperties]:
        if self._profile.protocol_version.is_ipv6:
            return self.ipv6_properties
        else:
            return self.ipv4_properties

    def change_ip_gateway_mac_address(self, gateway_mac: MacAddress) -> None:
        self.ip_gateway_mac_address = gateway_mac
