from asyncio import sleep

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Union
from xoa_driver import utils
from .test_result import AddressCollection
from ..utils.constants import (
    ETHER_TYPE_IPV4,
    ETHER_TYPE_IPV6,
    RIPVersion,
    RProtocolOption,
)
from ..model.protocol_segments import (
    HeaderSegment,
    ParseMode,
    ProtocolChange,
    ProtocolSegmentProfileConfig,
)
from ..model.port_config import PortConfiguration
from ..utils.field import NewIPv4Address, NewIPv6Address, MacAddress
from ..plugin.resource_manager import PortInstance, get_ip_property
from ..model.protocol_segments import DEFAULT_SEGMENT_DIC, SegmentDefinition


## SendGatewayArpRequests
@dataclass
class PortArpRefreshData:
    ip_version: RIPVersion
    port_config: PortConfiguration
    # source_ip_address: Union[IPv4Address, IPv6Address]
    # source_mac_address: MacAddress
    stream_config: str
    gateway_mac: MacAddress = MacAddress("00:00:00:00:00:00")


def has_ip_segment(
    stream_config: "ProtocolSegmentProfileConfig",
) -> Optional[RIPVersion]:
    for i in stream_config.header_segments:
        if i.segment_type == RProtocolOption.IPV4:
            return RIPVersion.IPV4
        elif i.segment_type == RProtocolOption.IPV6:
            return RIPVersion.IPV6
    return None


def add_address_refresh_entry(
    address_refresh_map: Dict[str, List["PortArpRefreshData"]],
    port_config: "PortConfiguration",
    ip_version: RIPVersion,
    # src_ip_address: Union[IPv4Address, IPv6Address],
    # source_mac_address: MacAddress,
    stream_config,
) -> Dict[str, List["PortArpRefreshData"]]:
    if not port_config.port_slot in address_refresh_map:
        address_refresh_map[port_config.port_slot] = []
    new_entry = PortArpRefreshData(
        ip_version=ip_version,
        port_config=port_config,
        # source_ip_address=src_ip_address,
        # source_mac_address=source_mac_address,
        stream_config=stream_config,
    )
    if new_entry not in address_refresh_map[port_config.port_slot]:
        address_refresh_map[port_config.port_slot].append(new_entry)

    return address_refresh_map


def wrap_add_16(data: bytearray, offset_num: int) -> bytearray:
    # Needs validation
    checksum = 0
    data[offset_num + 0] = 0
    data[offset_num + 1] = 0
    for i in range(0, len(data), 2):
        w = (data[i + 0] << 8) + data[i + 1]
        checksum += w
        if checksum > 0xFFFF:
            checksum = (1 + checksum) & 0xFFFF  # add carry back in as lsb
    data[offset_num + 0] = 0xFF + 1 + (~(checksum >> 8))
    data[offset_num + 1] = 0xFF + 1 + (~(checksum & 0xFF))
    return data


def calculate_checksum(
    segment: "HeaderSegment",
    segment_dic: Dict[str, "SegmentDefinition"],
    patched_value: bytearray,
) -> bytearray:
    key = segment.segment_type.value.legacy.lower()
    offset_num = segment_dic[key].checksum_offset if key in segment_dic else -1
    if offset_num and offset_num != -1:
        return wrap_add_16(patched_value, offset_num)
    return patched_value


def get_segment_value(
    header_segments: List["HeaderSegment"],
    segment_index: int,
    address_collection: "AddressCollection",
    can_tcp_checksum: bool,
) -> bytearray:
    segment = header_segments[segment_index]
    if segment.segment_type == RProtocolOption.TCP and can_tcp_checksum:
        header_segments[segment_index].segment_type = RProtocolOption.TCPCHECK
    segment_value_bytearray = bytearray.fromhex(segment.segment_value)
    patched_value = bytearray()
    if (segment.segment_type) == RProtocolOption.ETHERNET:
        # patch first Ethernet segment with the port S/D MAC addresses
        if segment_index == 0:
            # patched_value = setup_ethernet_segment(
            #     segment_value_bytearray, address_collection
            # )
            seg_types = [s.segment_type for s in header_segments]
            e_type = (
                ETHER_TYPE_IPV4
                if RProtocolOption.IPV4 in seg_types
                else ETHER_TYPE_IPV6
            )
            patched_value = (
                ProtocolChange(RProtocolOption.ETHERNET)
                .change_segment(
                    "Dst MAC addr",
                    address_collection.dmac.bytearrays,
                    ParseMode.BYTE,
                )
                .change_segment(
                    "Src MAC addr",
                    address_collection.smac.bytearrays,
                    ParseMode.BYTE,
                )
                .change_segment("EtherType", e_type, ParseMode.BYTE)
            ).bytearrays

    elif (segment.segment_type) == RProtocolOption.IPV4:
        change = ProtocolChange(RProtocolOption.IPV4)
        if segment_index + 1 <= len(header_segments) - 1:
            next_prot = header_segments[segment_index + 1]
            if next_prot.segment_type == RProtocolOption.UDP:
                change = change.change_segment("Protocol", 17, ParseMode.BIT)
            elif next_prot.segment_type == RProtocolOption.TCP:
                change = change.change_segment("Protocol", 6, ParseMode.BIT)
            elif next_prot.segment_type == RProtocolOption.ICMP:
                change = change.change_segment("Protocol", 1, ParseMode.BIT)
            elif next_prot.segment_type == RProtocolOption.SCTP:
                change = change.change_segment("Protocol", 132, ParseMode.BIT)
            elif next_prot.segment_type in (
                RProtocolOption.IGMPV1,
                RProtocolOption.IGMPV2,
                RProtocolOption.IGMPV3L0,
                RProtocolOption.IGMPV3L1,
            ):
                change = change.change_segment("Protocol", 2, ParseMode.BIT)
        patched_value = (
            change.change_segment(
                "Src IP Addr",
                address_collection.src_ipv4_addr.bytearrays,
                ParseMode.BYTE,
            ).change_segment(
                "Dest IP Addr",
                address_collection.dst_ipv4_addr.bytearrays,
                ParseMode.BYTE,
            )
        ).bytearrays
    elif (segment.segment_type) == RProtocolOption.IPV6:
        # patched_value = setup_ipv6_segment(segment_value_bytearray, address_collection)
        change = ProtocolChange(RProtocolOption.IPV6)
        if segment_index + 1 <= len(header_segments) - 1:
            next_prot = header_segments[segment_index + 1]
            if next_prot.segment_type == RProtocolOption.UDP:
                change = change.change_segment("Next Header", 17, ParseMode.BIT)
            elif next_prot.segment_type == RProtocolOption.TCP:
                change = change.change_segment("Next Header", 6, ParseMode.BIT)
            elif next_prot.segment_type == RProtocolOption.ICMP:
                change = change.change_segment("Next Header", 1, ParseMode.BIT)
            elif next_prot.segment_type == RProtocolOption.SCTP:
                change = change.change_segment("Next Header", 132, ParseMode.BIT)
            elif next_prot.segment_type in (
                RProtocolOption.IGMPV1,
                RProtocolOption.IGMPV2,
                RProtocolOption.IGMPV3L0,
                RProtocolOption.IGMPV3L1,
            ):
                change = change.change_segment("Next Header", 2, ParseMode.BIT)

        patched_value = (
            change.change_segment(
                "Src IPv6 Addr",
                address_collection.src_ipv6_addr.bytearrays,
                ParseMode.BYTE,
            ).change_segment(
                "Dest IPv6 Addr",
                address_collection.dest_ipv6_addr.bytearrays,
                ParseMode.BYTE,
            )
        ).bytearrays

    # set to default value if not assigned
    if patched_value == bytearray():
        patched_value = segment_value_bytearray

    return patched_value


def get_packet_header_inner(
    address_collection: "AddressCollection",
    header_segments: List["HeaderSegment"],
    can_tcp_checksum: bool,
    # arp_mac: "MacAddress",
) -> bytearray:
    packet_header_list = bytearray()

    # Insert all configured header segments in order

    for segment_index, segment in enumerate(header_segments):
        addr_coll = address_collection.copy()
        patched_value = get_segment_value(
            header_segments, segment_index, addr_coll, can_tcp_checksum
        )
        real_value = calculate_checksum(segment, DEFAULT_SEGMENT_DIC, patched_value)

        packet_header_list += real_value

    return packet_header_list


def make_address_collection(
    target_ip_address: Union["NewIPv4Address", "NewIPv6Address"],
    src_instance: "PortInstance",
    dmac: MacAddress = MacAddress("FF:FF:FF:FF:FF:FF"),
) -> AddressCollection:
    addr_coll = AddressCollection(
        smac=src_instance.native_mac_address,
        dmac=dmac,
        src_ipv4_addr=src_instance.config.ipv4_properties.address,
        src_ipv6_addr=src_instance.config.ipv6_properties.address,
    )

    if isinstance(target_ip_address, NewIPv6Address):
        addr_coll.dest_ipv6_addr = NewIPv6Address(target_ip_address)
    else:
        addr_coll.dst_ipv4_addr = NewIPv4Address(target_ip_address)
    return addr_coll


async def send_arp_learning_request(
    target_ip_address: Union["NewIPv4Address", "NewIPv6Address"],
    port_instance: "PortInstance",
    stream_config: "ProtocolSegmentProfileConfig",
):
    await port_instance.port.streams.server_sync()
    for s in port_instance.port.streams:
        await s.delete()
    stream = await port_instance.port.streams.create()
    await sleep(3)
    addr_coll = make_address_collection(target_ip_address, port_instance)
    packet_header = get_packet_header_inner(
        addr_coll, stream_config.header_segments, port_instance.can_tcp_checksum
    )
    *_, arp = await utils.apply(
        stream.packet.header.protocol.set(stream_config.header_segment_id_list),
        stream.packet.header.data.set(f"0x{bytes(packet_header).hex()}"),
        stream.enable.set_on(),
        stream.request.arp.get(),
    )

    addr_coll.change_dmac_address(arp)


async def send_gateway_learning_request(
    address_refresh_map: Dict[str, List["PortArpRefreshData"]],
    port_instance: "PortInstance",
    stream_config: "ProtocolSegmentProfileConfig",
) -> Dict[str, List["PortArpRefreshData"]]:
    ip_version = has_ip_segment(stream_config)
    if not ip_version:
        return address_refresh_map

    gateway = port_instance.config.ip_gateway_mac_address
    gateway_not_empty = not gateway.is_empty
    if gateway_not_empty:
        address_refresh_map = add_address_refresh_entry(
            address_refresh_map, port_instance.config, ip_version, stream_config
        )

    else:
        target_ip_address = get_ip_property(port_instance.config, ip_version).gateway
        await send_arp_learning_request(target_ip_address, port_instance, stream_config)
        address_refresh_map = add_address_refresh_entry(
            address_refresh_map, port_instance.config, ip_version, stream_config
        )
    return address_refresh_map


## SendGatewayArpRequests
