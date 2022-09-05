from dataclasses import dataclass
from pydantic import BaseModel
from typing import Optional, Union, Tuple

from ..utils.constants import PortProtocolVersion
from ..utils.field import IPv4Address, IPv6Address, MacAddress


@dataclass(frozen=True)
class ArpRefreshData:
    # is_ipv4: bool
    source_ip: Union[IPv4Address, IPv6Address, None]
    source_mac: Optional[MacAddress]
    addr_range: Optional[range]


@dataclass(frozen=True)
class RXTableData:
    destination_ip: Union[IPv4Address, IPv6Address]
    dmac: MacAddress


class StreamOffset(BaseModel):
    tx_offset: int
    rx_offset: int

    def reverse(self) -> "StreamOffset":
        return StreamOffset(tx_offset=self.rx_offset, rx_offset=self.tx_offset)


@dataclass
class AddressCollection:
    smac: MacAddress = MacAddress()
    dmac: MacAddress = MacAddress()
    arp_mac: MacAddress = MacAddress()
    src_ipv4_addr: IPv4Address = IPv4Address("0.0.0.0")
    dst_ipv4_addr: IPv4Address = IPv4Address("0.0.0.0")
    src_ipv6_addr: IPv6Address = IPv6Address("::")
    dst_ipv6_addr: IPv6Address = IPv6Address("::")

    def get_addr_pair_by_protocol(self, protocol: PortProtocolVersion) -> Tuple:
        if protocol.is_ipv4:
            return self.src_ipv4_addr, self.dst_ipv4_addr
        elif protocol.is_ipv6:
            return self.src_ipv6_addr, self.dst_ipv6_addr
        else:
            return self.smac, self.dmac
