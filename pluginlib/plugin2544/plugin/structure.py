import copy
from typing import List, TYPE_CHECKING, Optional, Set, Tuple, Union
from dataclasses import dataclass, field

from pluginlib.plugin2544.utils import exceptions
from pluginlib.plugin2544.utils.constants import FlowCreationType
from ..utils.field import MacAddress, IPv4Address, IPv6Address
from ..model import HwModifier
from xoa_core.core.test_suites.datasets import PortIdentity
from xoa_driver import enums, utils, ports as xoa_ports, testers as xoa_testers
if TYPE_CHECKING:
    from ..model import (
        PortConfiguration,
        ThroughputTest,
        LatencyTest,
        FrameLossRateTest,
        BackToBackTest,
    )

@dataclass(frozen=True)
class ArpRefreshData:
    is_ipv4: bool
    source_ip: Union[IPv4Address, IPv6Address, None]
    source_mac: Optional[MacAddress]
    addr_range: Optional[range]

@dataclass(frozen=True)
class RXTableData:
    destination_ip: Union[IPv4Address, IPv6Address]
    dmac: MacAddress


class Structure:
    def __init__(
        self,
        tester: "xoa_testers.L23Tester",
        port: "xoa_ports.GenericL23Port",
        port_conf: "PortConfiguration",
    ) -> None:
        self.tester: "xoa_testers.L23Tester" = tester
        self.port: "xoa_ports.GenericL23Port" = port
        self.port_conf = port_conf
        self.properties = Properties()

    async def reserve(self) -> None:
        if self.port.is_reserved_by_me():
            await self.free()
        elif self.port.is_reserved_by_others():
            await self.port.reservation.set(enums.ReservedAction.RELINQUISH)
        await utils.apply(
            self.port.reservation.set(enums.ReservedAction.RESERVE), self.port.reset.set()
        )

        self.port.on_reservation_change(self.__on_reservation_status)
        self.tester.on_disconnected(self.__on_disconnect_tester)
    
    async def __on_reservation_status(self, port: "xoa_ports.GenericL23Port", v):
        raise exceptions.LossofPortOwnership(self.port)

    async def __on_disconnect_tester(self, *args):
        chassis_id = self.properties.chassis_id
        raise exceptions.LossofTester(self.tester, chassis_id)

    async def free(self) -> None:
        await self.port.reservation.set(enums.ReservedAction.RELEASE)
    
    async def clear(self) -> None:
        await self.free()
        await self.tester.session.logoff()

@dataclass
class AddressCollection:
    smac_address: MacAddress = MacAddress("00:00:00:00:00:00")
    dmac_address: MacAddress = MacAddress("00:00:00:00:00:00")
    src_ipv4_address: IPv4Address = IPv4Address("0.0.0.0")
    dest_ipv4_address: IPv4Address = IPv4Address("0.0.0.0")
    src_ipv6_address: IPv6Address = IPv6Address("::")
    dest_ipv6_address: IPv6Address = IPv6Address("::")

    def change_dmac_address(self, mac_address: "MacAddress") -> None:
        self.dmac_address = mac_address

    def copy(self) -> "AddressCollection":
        return copy.deepcopy(self)


TypeConf = Union["ThroughputTest", "LatencyTest", "FrameLossRateTest", "BackToBackTest"]


@dataclass
class Properties:
    identity: str = ""
    chassis_id: str = ""
    test_port_index: int = 0
    num_modifiersL2: int = 1
    dest_port_count: int = 0
    high_dest_port_count: int = 0
    low_dest_port_count: int = 0
    lowest_dest_port_index: int = -1
    highest_dest_port_index: int = -1
    mac_address: MacAddress = MacAddress()
    is_max_frames_limit_set = False
    peers: List["Structure"] = field(default_factory=list)
    address_refresh_data_set: Set[ArpRefreshData] = field(default_factory=set)
    rx_table_set: Set[RXTableData] = field(default_factory=set)

    def set_identity(self, port_identity: "PortIdentity") -> None:
        self.identity = f"{port_identity.tester_index}-{port_identity.module_index}-{port_identity.port_index}"
        self.chassis_id = port_identity.tester_id

    def register_peer(self, peer: "Structure") -> None:
        if peer not in self.peers:
            self.peers.append(peer)
        if peer.properties.test_port_index == self.test_port_index:
            return
        self.dest_port_count += 1
        if peer.properties.test_port_index < self.test_port_index:
            self.low_dest_port_count += 1
        elif peer.properties.test_port_index > self.test_port_index:
            self.high_dest_port_count += 1
        self.num_modifiersL2 = (
            2 if (self.low_dest_port_count > 0 and self.high_dest_port_count > 0) else 1
        )
        self.lowest_dest_port_index = (
            peer.properties.test_port_index
            if self.lowest_dest_port_index == -1
            else min(self.lowest_dest_port_index, peer.properties.test_port_index)
        )
        self.highest_dest_port_index = (
            peer.properties.test_port_index
            if self.highest_dest_port_index == -1
            else max(self.highest_dest_port_index, peer.properties.test_port_index)
        )

    def change_mac_address(self, mac_address: "MacAddress") -> None:
        self.mac_address = mac_address

    def change_test_port_index(self, test_port_index: int) -> None:
        self.test_port_index = test_port_index

    def change_max_frames_limit_set_status(self, is_max_frames_set: bool) -> None:
        self.is_max_frames_limit_set = is_max_frames_set


@dataclass
class StreamInfo:
    flow_creation_type: FlowCreationType
    port_struct: Structure
    peer_struct: Structure
    stream_id: int
    arp_mac: MacAddress = MacAddress()
    tpldid: int = 0
    addr_coll: AddressCollection = AddressCollection()
    packet_header: bytearray = field(default_factory=bytearray)
    modifiers: List[HwModifier] = field(default_factory=list)
    rx_ports: List[Structure] = field(default_factory=list)

    def change_packet_header(self, packet_header: bytearray) -> None:
        self.packet_header = bytearray(packet_header)

    def change_arp_mac(self, arp_mac: "MacAddress") -> None:
        self.arp_mac = arp_mac
