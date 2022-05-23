import asyncio
from decimal import Decimal
import math
from typing import TYPE_CHECKING, Iterator, List, Optional, Tuple, Union
from xoa_driver import misc, enums, utils
from pluginlib.plugin2544.plugin.structure import ArpRefreshData, RXTableData
from .test_operations import StateChecker
from ..utils.field import NonNegativeDecimal

from ..utils.scheduler import schedule
from .test_result_structure import BoutEntry
from pluginlib.plugin2544.utils.constants import (
    MIN_REFRESH_TIMER_INTERNAL,
    IPPrefixLength,
    SegmentType,
    TestState,
)

from .common import filter_port_structs
from .setup_source_port_rates import setup_source_port_rates
from .statistics import set_port_txtime_limit, start_traffic
from ..utils.field import IPv4Address, IPv6Address
from ..utils.packet import ARPPacket, MacAddress, NDPPacket

if TYPE_CHECKING:
    from ..model import TestConfiguration
    from .structure import StreamInfo, Structure


def get_dest_ip_modifier_addr_range(
    port_struct: "Structure",
) -> Optional[range]:
    header_segments = port_struct.port_conf.profile.header_segments
    flag = False
    addr_range = None
    for header_segment in header_segments:
        if header_segment.segment_type in (SegmentType.IP, SegmentType.IPV6):
            flag = True
        for modifier in header_segment.hw_modifiers:
            if modifier.field_name in ["Dest IP Addr", "Dest IPv6 Addr"]:
                addr_range = range(
                    modifier.start_value,
                    modifier.stop_value + 1,
                    modifier.step_value,
                )
        if flag:
            break
    return addr_range


def add_address_refresh_entry(
    port_struct: "Structure",
    source_ip: Union["IPv4Address", "IPv6Address", None],
    source_mac: Union["MacAddress", None],
) -> None:  # AddAddressRefreshEntry
    """ARP REFRESH STEP 1: generate address_refresh_data_set"""
    is_ipv4 = port_struct.port_conf.profile.protocol_version.is_ipv4
    addr_range = get_dest_ip_modifier_addr_range(port_struct)
    port_struct.properties.address_refresh_data_set.add(
        ArpRefreshData(is_ipv4, source_ip, source_mac, addr_range)
    )


async def setup_arp_rx_tables(
    control_ports: List["Structure"],
) -> None:  # SetupArpRxTables
    """generate ARP RX TABLE if multiple stream mode"""
    # An ARP entry is: <IPv4 address> <prefix=32> <patch off> <MAC address>
    # An NDP entry is: <IPv6 address> <prefix=128> <patch off> <MAC address>
    tokens = []
    for port_struct in control_ports:
        arp_chunk: List[misc.ArpChunk] = []
        ndp_chunk: List[misc.NdpChunk] = []
        port = port_struct.port
        for rx_data in port_struct.properties.rx_table_set:
            if isinstance(rx_data.destination_ip, IPv4Address):
                arp_chunk.append(
                    misc.ArpChunk(
                        *[
                            rx_data.destination_ip,
                            IPPrefixLength.IPv4.value,
                            enums.OnOff.OFF,
                            rx_data.dmac,
                        ]
                    )
                )
            elif isinstance(rx_data.destination_ip, IPv6Address):
                ndp_chunk.append(
                    misc.NdpChunk(
                        *[
                            rx_data.destination_ip,
                            IPPrefixLength.IPv6.value,
                            enums.OnOff.OFF,
                            rx_data.dmac,
                        ]
                    )
                )
        if arp_chunk:
            tokens.append(port.arp_rx_table.set(arp_chunk))
        if ndp_chunk:
            tokens.append(port.ndp_rx_table.set(ndp_chunk))
    await utils.apply(*tokens)


def get_bytes_from_macaddress(dmac: "MacAddress") -> Iterator[str]:
    for i in range(0, len(dmac), 3):
        yield dmac[i : i + 2]


def get_link_local_uci_ipv6address(dmac: "MacAddress") -> str:
    b = get_bytes_from_macaddress(dmac)
    return f"FE80000000000000{int(next(b)) | 2 }{next(b)}{next(b)}FFFE{next(b)}{next(b)}{next(b)}"


def get_address_list(
    source_ip: Union["IPv4Address", "IPv6Address"],
    addr_range: Optional[range],
) -> List[Union["IPv4Address", "IPv6Address"]]:
    if not addr_range:
        return [source_ip]
    source_ip_list = []
    for i in addr_range:
        if isinstance(source_ip, IPv4Address):
            splitter = "."
            typing = IPv4Address
        else:
            splitter = ":"
            typing = IPv6Address

        addr = str(source_ip).split(splitter)
        addr[-1] = str(i)
        addr_str = splitter.join(addr)
        source_ip_list.append(typing(addr_str))

    return source_ip_list


def get_address_learning_packet(
    port_struct: "Structure",
    arp_refresh_data: ArpRefreshData,
    use_gateway=False,
) -> List[str]:  # GetAddressLearningPacket
    """ARP REFRESH STEP 2: generate learning packet according to address_refresh_data_set"""
    dmac = MacAddress("FF:FF:FF:FF:FF:FF")
    gateway = port_struct.port_conf.ip_properties.gateway
    sender_ip = port_struct.port_conf.ip_properties.address
    if use_gateway and not gateway.is_empty:
        gwmac = port_struct.port_conf.ip_gateway_mac_address
        if not gwmac.is_empty:
            dmac = gwmac
    smac = (
        port_struct.properties.mac_address
        if not arp_refresh_data.source_mac or arp_refresh_data.source_mac.is_empty
        else arp_refresh_data.source_mac
    )
    source_ip = (
        sender_ip
        if not arp_refresh_data.source_ip or arp_refresh_data.source_ip.is_empty
        else arp_refresh_data.source_ip
    )
    source_ip_list = get_address_list(source_ip, arp_refresh_data.addr_range)
    packet_list = []
    for source_ip in source_ip_list:
        if arp_refresh_data.is_ipv4:
            destination_ip = sender_ip if gateway.is_empty else gateway
            packet = ARPPacket(
                smac=smac,
                source_ip=IPv4Address(source_ip),
                destination_ip=IPv4Address(destination_ip),
                dmac=dmac,
            ).make_arp_packet()

        else:
            destination_ip = get_link_local_uci_ipv6address(dmac)
            packet = NDPPacket(
                smac=smac,
                source_ip=IPv6Address(source_ip),
                destination_ip=IPv6Address(destination_ip),
                dmac=dmac,
            ).make_ndp_packet()
        packet_list.append(packet)
    return packet_list


def setup_address_refresh(
    control_ports: List["Structure"],
    use_gateway: bool,
) -> List[Tuple["misc.Token", bool]]:  # SetupAddressRefresh
    address_refresh_tokens: List[Tuple["misc.Token", bool]] = []
    for port_struct in control_ports:
        arp_data_set = port_struct.properties.address_refresh_data_set
        for arp_data in arp_data_set:
            packet_list = get_address_learning_packet(
                port_struct,
                arp_data,
                use_gateway,
            )
            is_rx_only = (
                port_struct.port_conf.is_rx_port
                and not port_struct.port_conf.is_tx_port
            )
            for packet in packet_list:
                address_refresh_tokens.append(
                    (port_struct.port.tx_single_pkt.send.set(packet), is_rx_only)
                )
    return address_refresh_tokens


async def setup_multi_stream_address_arp_refresh(
    control_ports: List["Structure"],
    stream_lists: List["StreamInfo"],
) -> None:  # SetupMultiStreamAddressArpRefresh
    dest_structs = filter_port_structs(control_ports, is_source_port=False)
    for dest_struct in dest_structs:
        if not dest_struct.port_conf.profile.protocol_version.is_l3:
            continue
        for stream_info in stream_lists:
            if stream_info.peer_struct == dest_struct:
                is_ipv4 = (
                    stream_info.port_struct.port_conf.profile.protocol_version.is_ipv4
                )
                addr_coll = stream_info.addr_coll
                dest_ip_address = (
                    addr_coll.dest_ipv4_address
                    if is_ipv4
                    else addr_coll.dest_ipv6_address
                )
                add_address_refresh_entry(
                    dest_struct,
                    dest_ip_address,
                    addr_coll.dmac_address,
                )
                dest_struct.properties.rx_table_set.add(
                    RXTableData(dest_ip_address, addr_coll.dmac_address)
                )
    await setup_arp_rx_tables(control_ports)


def setup_normal_address_arp_refresh(
    control_ports: List["Structure"],
) -> None:  # SetupNormalAddressArpRefresh
    dest_structs = filter_port_structs(control_ports, is_source_port=False)
    for dest_struct in dest_structs:
        if not dest_struct.port_conf.profile.protocol_version.is_l3:
            continue
        add_address_refresh_entry(dest_struct, None, None)


def gateway_arp_refresh(
    control_ports: List["Structure"],
    test_conf: "TestConfiguration",
) -> None:
    # Add Gateway ARP Refresh
    source_port_structs = filter_port_structs(control_ports)
    for port_struct in source_port_structs:
        protocol_version = port_struct.port_conf.profile.protocol_version
        if test_conf.use_gateway_mac_as_dmac and protocol_version.is_l3:
            add_address_refresh_entry(
                port_struct,
                None,
                None,
            )


async def setup_address_arp_refresh(
    control_ports: List["Structure"],
    stream_lists: List["StreamInfo"],
    test_conf: "TestConfiguration",
) -> "AddressRefreshHandler":  # SetupAddressArpRefresh
    if test_conf.multi_stream_config.enable_multi_stream:
        await setup_multi_stream_address_arp_refresh(control_ports, stream_lists)
    else:
        setup_normal_address_arp_refresh(control_ports)
    gateway_arp_refresh(control_ports, test_conf)
    address_refresh_tokens = setup_address_refresh(
        control_ports, test_conf.use_gateway_mac_as_dmac
    )
    return AddressRefreshHandler(
        address_refresh_tokens, test_conf.arp_refresh_period_second
    )


class AddressRefreshHandler:
    """set packet interval and return batch"""

    def __init__(
        self,
        address_refresh_tokens: List[Tuple["misc.Token", bool]],
        refresh_period: "NonNegativeDecimal",
    ) -> None:
        self.index = 0
        self.refresh_burst_size = 1
        self.tokens: List["misc.Token"] = []
        self.address_refresh_tokens: List[
            Tuple["misc.Token", bool]
        ] = address_refresh_tokens
        self.interval = 0.0  # unit: second
        self.refresh_period = refresh_period
        self.state = TestState.L3_LEARNING

    def get_batch(self) -> List["misc.Token"]:
        packet_list = []
        if self.index >= len(self.tokens):
            self.index = 0
        for i in range(self.refresh_burst_size):
            if self.index < len(self.tokens):
                packet_list.append(self.tokens[self.index])
                self.index += 1
        return packet_list

    def _calc_refresh_time_interval(
        self, refresh_tokens: List["misc.Token"]
    ) -> None:  # CalcRefreshTimerInternal
        total_refresh_count = len(refresh_tokens)
        if total_refresh_count > 0:
            self.refresh_burst_size = 1
            interval = math.floor(self.refresh_period / total_refresh_count)
            if interval < MIN_REFRESH_TIMER_INTERNAL:
                self.refresh_burst_size = math.ceil(
                    MIN_REFRESH_TIMER_INTERNAL / interval
                )
                interval = MIN_REFRESH_TIMER_INTERNAL
            self.interval = interval / 1000.0  # ms -> second

    def set_current_state(self, state: "TestState") -> "AddressRefreshHandler":
        self.state = state
        if self.state == TestState.L3_LEARNING:
            self.tokens = [
                refresh_token[0] for refresh_token in self.address_refresh_tokens
            ]
        else:
            self.tokens = [
                refresh_token[0]
                for refresh_token in self.address_refresh_tokens
                if refresh_token[1]
            ]
        self._calc_refresh_time_interval(self.tokens)
        return self


async def generate_l3_learning_packets(
    count: int,
    state_checker: StateChecker,
    address_refresh_handler: "AddressRefreshHandler",
) -> bool:
    tokens = address_refresh_handler.get_batch()
    await utils.apply(*tokens)

    return not state_checker.test_running()


async def send_l3_learning_packets(
    state_checker: StateChecker,
    address_refresh_handler: "AddressRefreshHandler",
) -> None:
    await schedule(
        address_refresh_handler.interval,
        "s",
        generate_l3_learning_packets,
        state_checker,
        address_refresh_handler,
    )


async def schedule_arp_refresh(
    state_checker: StateChecker,
    address_refresh_handler: Optional["AddressRefreshHandler"],
    state: TestState = TestState.RUNNING_TEST,
):
    # arp refresh jobs
    if address_refresh_handler:
        address_refresh_handler.set_current_state(state)
        if address_refresh_handler.tokens:
            await send_l3_learning_packets(state_checker, address_refresh_handler)


async def add_L3_learning_preamble_steps(
    control_ports: List["Structure"],
    stream_lists: List["StreamInfo"],
    has_l3: bool,
    test_conf: "TestConfiguration",
    current_packet_size: NonNegativeDecimal,
    state_checker: "StateChecker",
) -> Optional["AddressRefreshHandler"]:  # AddL3LearningPreambleSteps
    if not test_conf.arp_refresh_enabled:
        return None
    if not has_l3:
        return None
    source_port_structs = filter_port_structs(control_ports)
    address_refresh_handler = await setup_address_arp_refresh(
        control_ports, stream_lists, test_conf
    )
    address_refresh_handler.set_current_state(TestState.L3_LEARNING)
    rate_percent_dic = {
        port_struct.properties.identity: BoutEntry(
            port_struct.properties.identity, rate=test_conf.learning_rate_pct
        )
        for port_struct in source_port_structs
    }
    await setup_source_port_rates(
        source_port_structs,
        stream_lists,
        test_conf.flow_creation_type,
        rate_percent_dic,
        current_packet_size,
    )
    await set_port_txtime_limit(
        source_port_structs,
        Decimal(test_conf.learning_duration_second * 1000),
    )
    await start_traffic(source_port_structs)
    await asyncio.gather(*address_refresh_handler.tokens)
    await schedule_arp_refresh(
        state_checker, address_refresh_handler, TestState.L3_LEARNING
    )
    while state_checker.test_running():
        await asyncio.gather(
            *[
                port_struct.port.traffic.state.get()
                for port_struct in source_port_structs
            ]
        )
        await asyncio.sleep(1)
    await set_port_txtime_limit(source_port_structs, Decimal(0))
    return address_refresh_handler
