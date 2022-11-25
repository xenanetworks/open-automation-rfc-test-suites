import sys
from statistics import fmean
from dataclasses import dataclass, field
from decimal import Decimal
from numbers import Number
from typing import Dict, List, NamedTuple, Tuple
from operator import attrgetter
from ipaddress import (
    IPv4Address as OldIPv4Address,
    IPv6Address as OldIPv6Address,
    IPv4Network,
    IPv6Network,
)
from xoa_driver import ports
from pydantic import (
    BaseModel,
)
from plugin2889.model.protocol_segment import BinaryString
from . import const


def hex_string_to_binary_string(hex: str) -> "BinaryString":
    """binary string with leading zeros
    """
    hex = hex.lower().replace('0x', '')
    return BinaryString(bin(int('1' + hex, 16))[3:])


class MacAddress(str):
    def to_hexstring(self):
        return self.replace(":", "").replace("-", "").upper()

    def first_three_bytes(self):
        return self.replace(":", "").replace("-", "").upper()[:6]

    def partial_replace(self, new_mac_address: "MacAddress"):
        return MacAddress(f"{new_mac_address}{self[len(new_mac_address):]}".lower())

    @classmethod
    def from_base_address(cls, base_address: str):
        prefix = [hex(int(i)) for i in base_address.split(",")]
        return cls(":".join([p.replace("0x", "").zfill(2).upper() for p in prefix]))

    @property
    def is_empty(self) -> bool:
        return not self or self == MacAddress("00:00:00:00:00:00")

    def to_bytearray(self) -> bytearray:
        return bytearray(bytes.fromhex(self.to_hexstring()))

    def to_binary_string(self) -> "BinaryString":
        return hex_string_to_binary_string(self.replace(':', ''))


class PortPair(BaseModel):
    west: str
    east: str

    @property
    def names(self) -> Tuple[str, str]:
        return self.west, self.east


class ResultData(BaseModel):
    result: List


class TestStatusModel(BaseModel):
    status: const.TestStatus = const.TestStatus.STOP


class TxStream(BaseModel):
    tpld_id: int
    packet: int = 0
    pps: int = 0


class RxTPLDId(BaseModel):
    packet: int = 0
    pps: int = 0


@dataclass
class PortLatency:
    check_value_ = True
    average_: Dict[int, Decimal] = field(default_factory=dict)
    minimum_: Decimal = Decimal(0)
    maximum_: Decimal = Decimal(0)

    def _pre_process(self, value: Decimal) -> Decimal:
        value = round(value / Decimal(1000), 3)
        if self.check_value_ and not value > ~sys.maxsize:
            value = Decimal(0)
        return value

    @property
    def minimum(self) -> Decimal:
        return self.minimum_

    @minimum.setter
    def minimum(self, value: Decimal) -> None:
        if value := self._pre_process(value):
            self.minimum_ = min(value, self.minimum_) if self.minimum_ else value

    @property
    def maximum(self) -> Decimal:
        return self.maximum_

    @maximum.setter
    def maximum(self, value: Decimal) -> None:
        self.maximum_ = max(self._pre_process(value), self.maximum_)

    @property
    def average(self) -> Decimal:
        return Decimal(fmean(self.average_.values()))

    def set_average(self, tpld_id: int, value: Decimal) -> None:
        if value := self._pre_process(value):
            self.average_[tpld_id] = value


class PortJitter(PortLatency):
    check_value_ = False


class StatisticsData(BaseModel):
    tx_packet: int = 0
    tx_bps_l1: int = 0
    tx_bps_l2: int = 0
    tx_pps: int = 0
    rx_packet: int = 0
    rx_bps_l1: int = 0
    rx_bps_l2: int = 0
    rx_pps: int = 0
    loss: int = 0
    loss_percent: Decimal = Decimal(0)
    fcs: int = 0
    flood: int = 0  # no tpld
    per_tx_stream: Dict[int, TxStream] = {}
    per_rx_tpld_id: Dict[int, RxTPLDId] = {}
    latency: PortLatency = PortLatency()
    jitter: PortJitter = PortJitter()

    def __add__(self, other: "StatisticsData") -> "StatisticsData":
        for name, value in self:
            if isinstance(value, Number):
                setattr(self, name, value + attrgetter(name)(other))
        return self


class CurrentIterProps(NamedTuple):
    iteration_number: int
    packet_size: int


AutoNegPorts = (
    ports.POdin1G3S6P,
    ports.POdin1G3S6P_b,
    ports.POdin1G3S6PE,
    ports.POdin1G3S2PT,
    ports.POdin5G4S6PCU,
    ports.POdin10G5S6PCU,
    ports.POdin10G5S6PCU_b,
    ports.POdin10G3S6PCU,
    ports.POdin10G3S2PCU,
)

MdixPorts = (
    ports.POdin1G3S6P,
    ports.POdin1G3S6P_b,
    ports.POdin1G3S6PE,
    ports.POdin1G3S2PT,
)


class IPv4Address(OldIPv4Address):
    def to_hexstring(self) -> str:
        return self.packed.hex().upper()

    def last_three_bytes(self) -> str:
        return self.to_hexstring()[-6:]

    def to_bytearray(self) -> bytearray:
        return bytearray(self.packed)

    def network(self, prefix: int) -> IPv4Network:
        return IPv4Network(f"{self}/{prefix}", strict=False)

    @property
    def is_empty(self) -> bool:
        return not self or self == IPv4Address("0.0.0.0")

    def to_binary_string(self) -> "BinaryString":
        return hex_string_to_binary_string(self.to_hexstring())


class IPv6Address(OldIPv6Address):
    def to_hexstring(self) -> str:
        return self.packed.hex().upper()

    def last_three_bytes(self) -> str:
        return self.to_hexstring()[-6:]

    def to_bytearray(self) -> bytearray:
        return bytearray(self.packed)

    @property
    def is_empty(self) -> bool:
        return not self or self == IPv6Address("::")

    def network(self, prefix: int) -> IPv6Network:
        return IPv6Network(f"{self}/{prefix}", strict=False)

    def to_binary_string(self) -> "BinaryString":
        return hex_string_to_binary_string(self.to_hexstring())


@dataclass
class AddressCollection:
    smac: MacAddress
    dmac: MacAddress
    src_ipv4_addr: IPv4Address
    dst_ipv4_addr: IPv4Address
    src_ipv6_addr: IPv6Address
    dst_ipv6_addr: IPv6Address
