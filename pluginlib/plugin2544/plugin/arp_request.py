import asyncio
from dataclasses import dataclass
from typing import List, Dict, Union
from ..utils.logger import logger
from ..utils.constants import ARPSenarioType
from ..utils.field import IPv4Address, IPv6Address, MacAddress, IPAddress
from ..utils.packet import Ether, IPV4Packet, IPV6Packet
from ..utils.traffic_definitions import EtherType
from .structure import StreamInfo, Structure
from .common import get_pair_address, is_same_ipnetwork
from xoa_driver import utils, enums


@dataclass
class Pair:
    source_ip: Union[IPv4Address, IPv6Address]
    destination_ip: Union[IPv4Address, IPv6Address]


async def set_arp_request(
    stream_lists: List["StreamInfo"],
    use_gateway_mac_as_dmac: bool,
) -> None:
    arp_mac_map: Dict[Pair, MacAddress] = {}
    for stream_info in stream_lists:
        # ARP / NDP
        port_struct = stream_info.port_struct
        peer_struct = stream_info.peer_struct
        if (
            not use_gateway_mac_as_dmac
            or not port_struct.port_conf.profile.protocol_version.is_l3
            or is_same_ipnetwork(port_struct, peer_struct)
        ):
            continue
        gwmac = port_struct.port_conf.ip_gateway_mac_address
        port = port_struct.port
        source_ip = port_struct.port_conf.ip_properties.address
        destination_ip, senario_type = get_pair_address(
            port_struct, peer_struct, use_gateway_mac_as_dmac
        )
        pair = Pair(source_ip, destination_ip)
        if pair in arp_mac_map:
            stream_info.change_arp_mac(arp_mac_map[pair])
            continue
        logger.debug(
            f"check packetheader for{port.kind.port_id} -> {source_ip}, {destination_ip}"
        )
        peer_mac_address = await send_arp_request(
            port_struct, source_ip, destination_ip
        )
        arp_mac_map[pair] = peer_mac_address
        stream_info.change_arp_mac(peer_mac_address)
        if senario_type == ARPSenarioType.GATEWAY and gwmac.is_empty:
            port_struct.port_conf.change_ip_gateway_mac_address(peer_mac_address)


async def get_packet_header(
    port_struct: "Structure", source_ip: IPAddress, destination_ip: IPAddress
) -> str:
    if port_struct.port_conf.profile.protocol_version.is_ipv4:
        # ip_header = (
        #     source_ip=IPv4Address(source_ip),
        #     destination_ip=IPv4Address(destination_ip),
        # )
        packet_cls = IPV4Packet
        addr_type = IPv4Address
        ether_type = EtherType.IPV4
    else:
        # ip_header = (
        #     source_ip=IPv6Address(source_ip),
        #     destination_ip=IPv6Address(destination_ip),
        # )
        ether_type = EtherType.IPV6
        addr_type = IPv6Address
        packet_cls = IPV6Packet
    ip_header = packet_cls(
        source_ip=addr_type(source_ip), destination_ip=destination_ip
    )
    mac_addr = await port_struct.port.net_config.mac_address.get()
    packet_header = (
        Ether(smac=MacAddress(mac_addr.mac_address), type=ether_type).hexstring
        + ip_header.hexstring
    )
    return packet_header


async def send_arp_request(
    port_struct: "Structure", source_ip, destination_ip
) -> MacAddress:
    port = port_struct.port
    packet_header = await get_packet_header(port_struct, source_ip, destination_ip)
    stream = await port.streams.create()
    await utils.apply(
        stream.packet.limit.set(-1),
        stream.comment.set("Stream number 0"),
        stream.rate.fraction.set(0),
        stream.burst.burstiness.set(-1, 100),
        stream.burst.gap.set(0, 0),
        stream.packet.header.protocol.set(
            [enums.ProtocolOption.ETHERNET, enums.ProtocolOption.IP]
        ),
        stream.packet.header.data.set(packet_header),
        stream.packet.length.set(enums.LengthType.FIXED, 64, 1518),  # PS_PACKETLENGTH
        stream.payload.content.set(enums.PayloadType.INCREMENTING, "0x00"),
        stream.tpld_id.set(-1),
        stream.insert_packets_checksum.set(enums.OnOff.ON),
        stream.gateway.ipv4.set("0.0.0.0"),
        stream.gateway.ipv6.set("::"),
        stream.enable.set(enums.OnOffWithSuppress.ON),
    )
    await asyncio.sleep(1)
    result, *_ = await utils.apply(stream.request.arp.get())
    peer_mac_address = MacAddress(result.mac_address)
    logger.debug(f"[Set_arp_request] Successfully get mac address {peer_mac_address}")
    await stream.delete()
    return peer_mac_address
