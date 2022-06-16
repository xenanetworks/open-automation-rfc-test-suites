import asyncio
from typing import Optional

from .common import is_same_ipnetwork
from ..utils.field import IPv4Address, IPv6Address, MacAddress, IPAddress
from ..utils.packet import Ether, IPV4Packet, IPV6Packet
from ..utils.traffic_definitions import EtherType
from .structure import PortStruct
from xoa_driver import utils, enums


async def set_arp_request(
    port_struct: "PortStruct",
    peer_struct: "PortStruct",
    use_gateway_mac_as_dmac: bool,
) -> Optional[MacAddress]:

    if (
        not use_gateway_mac_as_dmac
        or not port_struct.port_conf.profile.protocol_version.is_l3
        or is_same_ipnetwork(port_struct, peer_struct)
    ):
        return None
    ip_properties = port_struct.port_conf.ip_properties
    peer_ip_properties = peer_struct.port_conf.ip_properties
    is_gateway_scenario = not ip_properties.gateway == peer_ip_properties.gateway
    if is_gateway_scenario:
        destination_ip = ip_properties.gateway
    elif ip_properties.gateway.is_empty and ip_properties.remote_loop_address:
        destination_ip = ip_properties.remote_loop_address
    else:
        destination_ip = peer_ip_properties.public_address
    arp_mac = await send_arp_request(port_struct, ip_properties.address, destination_ip)
    if is_gateway_scenario:
        port_struct.port_conf.ip_gateway_mac_address = arp_mac
    return arp_mac


async def get_packet_header(
    port_struct: "PortStruct", source_ip: IPAddress, destination_ip: IPAddress
) -> str:
    if port_struct.port_conf.profile.protocol_version.is_ipv4:
        packet_cls = IPV4Packet
        addr_type = IPv4Address
        ether_type = EtherType.IPV4
    else:
        ether_type = EtherType.IPV6
        addr_type = IPv6Address
        packet_cls = IPV6Packet
    ip_header = packet_cls(
        source_ip=addr_type(source_ip), destination_ip=destination_ip
    )
    mac_address = await port_struct.get_mac_address()
    packet_header = (
        Ether(smac=mac_address, type=ether_type).hexstring + ip_header.hexstring
    )
    return packet_header


async def send_arp_request(
    port_struct: "PortStruct", source_ip, destination_ip
) -> MacAddress:
    packet_header = await get_packet_header(port_struct, source_ip, destination_ip)
    stream = await port_struct.create_stream()
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
    # logger.debug(f"[Set_arp_request] Successfully get mac address {peer_mac_address}")
    await stream.delete()
    return peer_mac_address
