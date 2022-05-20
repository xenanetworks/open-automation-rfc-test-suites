from ipaddress import IPv4Network, IPv6Network
from typing import Union

from pydantic import validator

from ..utils.constants import FECModeStr, PortGroup

from decimal import Decimal
from typing import Union
from pydantic import (
    BaseModel,
    validator,
    NonNegativeInt,
)

from ..utils.constants import (
    IPVersion,
    PortGroup,
    PortSpeedStr,
    MdiMdixMode,
    BRRModeStr,
    PortRateCapProfile,
    PortRateCapUnit,
)
from ..utils.field import MacAddress, IPv4Address, IPv6Address, Prefix
from .m_protocol_segment import ProtocolSegmentProfileConfig


class IPV6AddressProperties(BaseModel):
    address: IPv6Address = IPv6Address("::")
    routing_prefix: Prefix = Prefix(24)
    public_address: IPv6Address = IPv6Address("::")
    public_routing_prefix: Prefix = Prefix(24)
    gateway: IPv6Address = IPv6Address("::")
    remote_loop_address: IPv6Address = IPv6Address("::")
    ip_version: IPVersion = IPVersion.IPV6

    @property
    def network(self):
        return IPv6Network(f"{self.address}/{self.routing_prefix}", strict=False)

    @staticmethod
    def is_ip_zero(ip_address: IPv6Address) -> bool:
        return ip_address == IPv6Address("::") or (not ip_address)

    @validator("address", "public_address", "gateway", "remote_loop_address", pre=True)
    def set_address(cls, v):
        return IPv6Address(v)

    @validator("routing_prefix", "public_routing_prefix", pre=True)
    def set_prefix(cls, v):
        return Prefix(v)


class IPV4AddressProperties(BaseModel):
    address: IPv4Address = IPv4Address("0.0.0.0")
    routing_prefix: Prefix = Prefix(24)
    public_address: IPv4Address = IPv4Address("0.0.0.0")
    public_routing_prefix: Prefix = Prefix(24)
    gateway: IPv4Address = IPv4Address("0.0.0.0")
    remote_loop_address: IPv4Address = IPv4Address("0.0.0.0")
    ip_version: IPVersion = IPVersion.IPV4

    @property
    def network(self):
        return IPv4Network(f"{self.address}/{self.routing_prefix}", strict=False)

    @staticmethod
    def is_ip_zero(ip_address: IPv4Address) -> bool:
        return ip_address == IPv4Address("0.0.0.0") or (not ip_address)

    @validator("address", "public_address", "gateway", "remote_loop_address", pre=True)
    def set_address(cls, v):
        return IPv4Address(v)

    @validator("routing_prefix", "public_routing_prefix", pre=True)
    def set_prefix(cls, v):
        return Prefix(v)


class PortConfiguration(BaseModel):
    port_slot: str
    port_config_slot: str = ""
    peer_config_slot: str
    port_group: PortGroup
    port_speed_mode: PortSpeedStr

    # PeerNegotiation
    auto_neg_enabled: bool
    anlt_enabled: bool
    mdi_mdix_mode: MdiMdixMode
    broadr_reach_mode: BRRModeStr

    # PortRateCap
    # port_rate_cap_enabled: bool
    port_rate_cap_value: float
    port_rate_cap_profile: PortRateCapProfile
    port_rate_cap_unit: PortRateCapUnit

    # PhysicalPortProperties
    inter_frame_gap: NonNegativeInt
    speed_reduction_ppm: NonNegativeInt
    pause_mode_enabled: bool
    latency_offset_ms: int  # QUESTION: can be negative?
    fec_mode: FECModeStr

    profile_id: str

    ip_gateway_mac_address: MacAddress
    reply_arp_requests: bool
    reply_ping_requests: bool
    remote_loop_mac_address: MacAddress
    ipv4_properties: IPV4AddressProperties
    ipv6_properties: IPV6AddressProperties

    # Computed Properties
    is_tx_port: bool = True
    is_rx_port: bool = True
    port_rate: Decimal = Decimal("0.0")
    ip_properties: Union[
        IPV4AddressProperties, IPV6AddressProperties
    ] = IPV4AddressProperties()
    profile: ProtocolSegmentProfileConfig = ProtocolSegmentProfileConfig()

    def change_ip_gateway_mac_address(self, gateway_mac: MacAddress):
        self.ip_gateway_mac_address = gateway_mac

    @validator("port_rate", always=True, pre=True)
    def set_port_rate(cls, v, values):
        check = all(
            [
                (
                    i in values
                    for i in (
                        "port_rate_cap_value",
                        "port_rate_cap_profile",
                        "port_rate_cap_unit",
                    )
                )
            ]
        )
        if not check:
            return v
        return Decimal(
            str(
                {
                    PortRateCapUnit.GBPS: 1e9,
                    PortRateCapUnit.MBPS: 1e6,
                    PortRateCapUnit.KBPS: 1e3,
                    PortRateCapUnit.BPS: 1,
                }[values["port_rate_cap_unit"]]
                * values["port_rate_cap_value"]
            )
        )
