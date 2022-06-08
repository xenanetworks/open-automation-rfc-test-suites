from dataclasses import dataclass, fields
import functools
from typing import Optional, Union
from pydantic import BaseModel
from pluginlib.plugin2544.utils.field import IPv4Address, IPv6Address, MacAddress


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


@dataclass(init=False, repr=False)
class PortMax:
    bps: int = 0
    pps: int = 0

    def reset(self) -> None:
        for field in fields(self):
            setattr(self, field.name, 0)

    def __update_value(self, name: str, value: int) -> None:
        current = getattr(self, name)
        setattr(self, name, max(current, value))

    update_bps = functools.partialmethod(__update_value, "bps")
    update_pps = functools.partialmethod(__update_value, "pps")
