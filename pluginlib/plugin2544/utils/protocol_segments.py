from typing import TYPE_CHECKING, Optional
from ..model import BinaryString

if TYPE_CHECKING:
    from ..model import ProtocolSegment, BinaryString


ETHERNET_ADDRESS_SRC = 'Src MAC addr'
ETHERNET_ADDRESS_DST = 'Dst MAC addr'
IPV4_ADDRESS_SRC = 'Src IP Addr'
IPV4_ADDRESS_DST = 'Dest IP Addr'
IPV6_ADDRESS_SRC = 'Src IPv6 Addr'
IPV6_ADDRESS_DST = 'Dest IPv6 Addr'


def setup_segment_ethernet(segment: "ProtocolSegment", src_mac: "BinaryString", dst_mac: "BinaryString", arp_mac: Optional["BinaryString"] = None):
    dst_mac = (dst_mac if not arp_mac or arp_mac.is_all_zero else arp_mac)
    if not dst_mac.is_all_zero and segment[ETHERNET_ADDRESS_SRC].is_all_zero:
        segment[ETHERNET_ADDRESS_SRC] = dst_mac
    if not src_mac.is_all_zero and segment[ETHERNET_ADDRESS_DST].is_all_zero:
        segment[ETHERNET_ADDRESS_DST] = src_mac

def setup_segment_ipv4(segment: "ProtocolSegment", src_ipv4: "BinaryString", dst_ipv4: "BinaryString"):
    if segment[IPV4_ADDRESS_SRC].is_all_zero:
        segment[IPV4_ADDRESS_SRC] = src_ipv4
    if segment[IPV4_ADDRESS_DST].is_all_zero:
        segment[IPV4_ADDRESS_DST] = dst_ipv4

def setup_segment_ipv6(segment: "ProtocolSegment", src_ipv6: "BinaryString", dst_ipv6: "BinaryString"):
    if segment[IPV6_ADDRESS_SRC].is_all_zero:
        segment[IPV6_ADDRESS_SRC] = src_ipv6
    if segment[IPV6_ADDRESS_DST].is_all_zero:
        segment[IPV6_ADDRESS_DST] = dst_ipv6
