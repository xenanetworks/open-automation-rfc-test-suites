import asyncio
from typing import List, Dict, Union, Tuple
from ..utils.logger import logger
from ..utils.constants import ARPSenarioType
from ..utils.field import IPv4Address, IPv6Address, MacAddress
from ..utils.packet import Ether, IPV4Packet, IPV6Packet
from ..utils.traffic_definitions import EtherType
from .structure import StreamInfo
from .common import get_pair_address, may_change_segment_id_list
from xoa_driver.utils import apply
from xoa_driver.enums import LengthType


async def set_arp_request(
    stream_lists: List["StreamInfo"],
    use_gateway_mac_as_dmac: bool,
) -> None:
    arp_mac_map: Dict[
        Tuple[Union["IPv4Address", "IPv6Address"], Union["IPv4Address", "IPv6Address"]],
        MacAddress,
    ] = {}
    for stream_info in stream_lists:
        # ARP / NDP
        port_struct = stream_info.port_struct
        peer_struct = stream_info.peer_struct
        gwmac = port_struct.port_conf.ip_gateway_mac_address
        port = port_struct.port
        if (
            use_gateway_mac_as_dmac
            and port_struct.port_conf.profile.protocol_version.is_l3
        ):
            source_ip = port_struct.port_conf.ip_properties.address
            destination_ip, senario_type = get_pair_address(
                port_struct, peer_struct, use_gateway_mac_as_dmac
            )
            if (source_ip, destination_ip) in arp_mac_map:

                stream_info.change_arp_mac(arp_mac_map[(source_ip, destination_ip)])
            else:
                stream = await port.streams.create()
                logger.debug(
                    f"check packetheader for{port.kind.port_id} -> {source_ip}, {destination_ip}"
                )

                if port_struct.port_conf.profile.protocol_version.is_ipv4:
                    ip_header = IPV4Packet(
                        source_ip=IPv4Address(source_ip),
                        destination_ip=IPv4Address(destination_ip),
                    )
                    ether_type = EtherType.IPV4
                else:
                    ip_header = IPV6Packet(
                        source_ip=IPv6Address(source_ip),
                        destination_ip=IPv6Address(destination_ip),
                    )
                    ether_type = EtherType.IPV6
                mac_addr = await port.net_config.mac_address.get()
                packet_header = (
                    Ether(
                        smac=MacAddress(mac_addr.mac_address), type=ether_type
                    ).hexstring
                    + ip_header.hexstring
                )
                segment_id_list = may_change_segment_id_list(
                    port_struct.port,
                    port_struct.port_conf.profile.header_segment_id_list,
                )

                await apply(
                    stream.packet.limit.set(-1),
                    stream.comment.set("Stream number 0"),
                    stream.rate.fraction.set(0),
                    stream.burst.burstiness.set(-1, 100),
                    stream.burst.gap.set(0, 0),
                    stream.packet.header.protocol.set(segment_id_list),
                    stream.packet.header.data.set(packet_header),
                    stream.packet.length.set(
                        LengthType.FIXED, 64, 1518
                    ),  # PS_PACKETLENGTH
                    stream.payload.content.set_incrementing(["0x00"]),
                    stream.tpld_id.set(-1),
                    stream.insert_packets_checksum.set_on(),
                    stream.gateway.ipv4.set("0.0.0.0"),
                    stream.gateway.ipv6.set("::"),
                    stream.enable.set_on(),
                )
                await asyncio.sleep(1)
                result, *_ = await apply(stream.request.arp.get())
                peer_mac_address = MacAddress(result.mac_address)
                logger.debug(
                    f"[Set_arp_request] Successfully get mac address {peer_mac_address}"
                )
                await stream.delete()
                arp_mac_map[(source_ip, destination_ip)] = peer_mac_address
                stream_info.change_arp_mac(peer_mac_address)
                if senario_type == ARPSenarioType.GATEWAY and gwmac.is_empty:
                    port_struct.port_conf.change_ip_gateway_mac_address(
                        peer_mac_address
                    )
