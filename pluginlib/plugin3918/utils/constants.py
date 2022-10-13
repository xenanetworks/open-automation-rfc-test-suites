from enum import Enum
from xoa_driver.enums import (
    LatencyMode as XLatencyMode,
    LengthType,
    ProtocolOption as XProtocolOption,
    PayloadType as XPayloadType,
)


MIXED_DEFAULT_WEIGHTS = [0, 0, 0, 0, 57, 3, 5, 1, 2, 5, 1, 4, 4, 18, 0, 0]
MIXED_PACKET_SIZE = [
    56,
    60,
    64,
    70,
    78,
    92,
    256,
    496,
    512,
    570,
    576,
    594,
    1438,
    1518,
    9216,
    16360,
]
STANDARD_TPLD_LENGTH = 20
MICRO_TPLD_LENGTH = 6
ETHERNET_FCS_LENGTH = 4
MIN_PAYLOAD_LENGTH = 2

STANDARD_TPLD_TOTAL_LENGTH = (
    STANDARD_TPLD_LENGTH + MIN_PAYLOAD_LENGTH + ETHERNET_FCS_LENGTH
)
MICRO_TPLD_TOTAL_LENGTH = MICRO_TPLD_LENGTH + ETHERNET_FCS_LENGTH
MIN_REFRESH_TIMER_INTERNAL = 100.0

HW_PACKET_MIN_SIZE = 64
HW_PACKET_MAX_SIZE = 1500

IP_V4_MULTICAST_MAC_BASE_ADDRESS = "0x01005e000000"
IP_V6_MULTICAST_MAC_BASE_ADDRESS = "0x333300000000"

IGMP_V2_JOIN = 0x16
IGMP_V2_LEAVE = 0x17
MLD_V1_REPORT = 0x83
MLD_V1_DONE = 0x84
MLD_V2_REPORT = 0x8F

ALL_ROUTERS_MULTICAST_GROUP_V2 = "224.0.0.2"
ALL_ROUTERS_MULTICAST_GROUP_V3 = "224.0.0.22"
IPV6_LINK_SCOPE_ALL_MLD_ROUTERS_ADDRESS = "FF02::16"
ICMP_V6_IP_PROTOCOL = 0x3A
IP_V6_OPTION_ROUTER_ALERT = 0x05
IP_V6_OPTION_HOP_BY_HOP = 0x00


ETHER_TYPE_NULL = [0x00, 0x00]
ETHER_TYPE_NONE = [0xFF, 0xFF]
ETHER_TYPE_VLAN_TAGGED = [0x81, 0x00]
ETHER_TYPE_VLAN_QIN_Q = [0x91, 0x00]
ETHER_TYPE_MPLS_UNICAST = [0x88, 0x47]
ETHER_TYPE_MPLS_MULTICAST = [0x88, 0x48]
ETHER_TYPE_IPV4 = [0x08, 0x00]
ETHER_TYPE_IPV6 = [0x86, 0xDD]
ETHER_TYPE_ARP = [0x08, 0x06]

IP_V4_OPTION_ROUTER_ALERT = 0x94
MIN_PACKET_LENGTH = 60

IEEE_DEFAULT_LIST = [64, 128, 256, 512, 1024, 1280, 1518]

TRIGGER_PACKET_SIZE = 64

FILTER_M0M1_L0L1 = 196611


class MulticastRole(Enum):
    MC_SOURCE = "mc_source"  # AnyMember("McSource", "mc_source")
    MC_DESTINATION = "mc_destination"  # AnyMember("McDestination", "mc_destination")
    UC_BURDEN = "uc_burden"  # AnyMember("UcBurden", "uc_burden")
    UNDEFINED = "undefined"  # AnyMember("Undefined", "undefined")


class TestTopology(Enum):
    PAIRS = "pairs"  # AnyMember("PAIRS", "pairs")
    BLOCKS = "blocks"  # AnyMember("BLOCKS", "blocks")
    MESH = "mesh"  # AnyMember("MESH", "mesh")


class TrafficDirection(Enum):
    EAST_TO_WEST = "east_to_west"  # AnyMember("EAST_TO_WEST", "east_to_west")
    WEST_TO_EAST = "west_to_east"  # AnyMember("WEST_TO_EAST", "west_to_east")
    BIDIRECTION = "bidir"  # AnyMember("BIDIR", "bidir")


class IgmpVersion(Enum):
    IGMP_V1 = "igmp_v1"  # AnyMember("IGMP_V1", "igmp_v1")
    IGMP_V2_OR_MLD_V1 = "igmp_v2_or_mld_v1"  # AnyMember("IGMP_V2", "igmp_v2_or_mld_v1")
    IGMP_V3_OR_MLD_V2 = "igmp_v3_or_mld_v2"  # AnyMember("IGMP_V3", "igmp_v3_or_mld_v2")


class IPVersion(Enum):
    IPV4 = "ipv4"  # AnyMember("IP", "ipv4", ProtocolOption.IP)
    IPV6 = "ipv6"  # AnyMember("IPv6", "ipv6", ProtocolOption.IPV6)


class DisplayUnit(Enum):
    MILLI_SECONDS = "millisecs"  # AnyMember("Millisecs", "millisecs")
    MICRO_SECONDS = "microsecs"  # AnyMember("Microsecs", "microsecs")

    @property
    def scale(self) -> float:
        if self == DisplayUnit.MILLI_SECONDS:
            return 1e3
        else:
            return 1e6


class ProtocolOption(Enum):
    ARP = "arp"  # AnyMember("ARP", "arp", ProtocolOption.ARP)
    ETHERNET = "ethernet"  # AnyMember("ETHERNET", "ethernet", ProtocolOption.ETHERNET)
    FC = "fc"  # AnyMember("FC", "fc", ProtocolOption.FC)
    FCOE = "fcoe"  # AnyMember("FCOEHEAD", "fcoe", ProtocolOption.FCOE)
    FCOETAIL = "fcoetail"  # AnyMember("FCOETAIL", "fcoetail", ProtocolOption.FCOETAIL)
    GRE_CHECK = (
        "gre_check"  # AnyMember("GRE_CHECK", "gre_check", ProtocolOption.GRE_CHECK)
    )
    GRE_NOCHECK = "gre_nocheck"  # AnyMember("GRE_NOCHECK", "gre_nocheck", ProtocolOption.GRE_NOCHECK)
    GTP = "gtp"  # AnyMember("GTP", "gtp", ProtocolOption.GTP)
    ICMP = "icmp"  # AnyMember("ICMP", "icmp", ProtocolOption.ICMP)
    ICMPV6 = "icmpv6"  # AnyMember("ICMPV6", "icmpv6", ProtocolOption.ICMP)
    IGMPV1 = "igmpv1"  # AnyMember("IGMPV1", "igmpv1", ProtocolOption.IGMPV1)
    IGMPV2 = "igmpv2"  # AnyMember("IGMPV2", "igmpv2", ProtocolOption.IGMPV2)
    MLDV2_AR = "mldv2_ar"  # AnyMember("MLDV2_AR", "mldv2_ar")
    IGMPV3_GR = "igmpv3_gr"  # AnyMember("IGMPV3_GR", "igmpv3_gr")
    IGMPV3_MR = "igmpv3_mr"  # AnyMember("IGMPV3_MR", "igmpv3_mr")
    IGMPV3L0 = "igmpv3l0"  # AnyMember("IGMPV3L0", "igmpv3l0", ProtocolOption.IGMPV3L0)
    IGMPV3L1 = "igmpv3l1"  # AnyMember("IGMPV3L1", "igmpv3l1", ProtocolOption.IGMPV3L1)
    IPV4 = "ipv4"  # AnyMember("IP", "ipv4", ProtocolOption.IP)
    IPV6 = "ipv6"  # AnyMember("IPv6", "ipv6", ProtocolOption.IPV6)
    LLC = "llc"  # AnyMember("LLC", "llc", ProtocolOption.LLC)
    MACCTRL = "macctrl"  # AnyMember("MACCTRL", "macctrl", ProtocolOption.MACCTRL)
    MPLS = "mpls"  # AnyMember("MPLS", "mpls", ProtocolOption.MPLS)
    NVGRE = "nvgre"  # AnyMember("NVGRE", "nvgre", ProtocolOption.NVGRE)
    PBBTAG = "pbbtag"  # AnyMember("PBBTAG", "pbbtag", ProtocolOption.PBBTAG)
    RTCP = "rtcp"  # AnyMember("RTCP", "rtcp", ProtocolOption.RTCP)
    RTP = "rtp"  # AnyMember("RTP", "rtp", ProtocolOption.RTP)
    SCTP = "sctp"  # AnyMember("SCTP", "sctp", ProtocolOption.SCTP)
    SNAP = "snap"  # AnyMember("SNAP", "snap", ProtocolOption.SNAP)
    STP = "stp"  # AnyMember("STP", "stp", ProtocolOption.STP)
    TCP = "tcp"  # AnyMember("TCP", "tcp", ProtocolOption.TCP)
    TCPCHECK = (
        "tcp_check"  # AnyMember("TCPCHECK", "tcp_check", ProtocolOption.TCPCHECK)
    )
    UDP = "udp"  # AnyMember("UDP", "udp", ProtocolOption.UDP)
    UDPCHECK = "udp_check"  # AnyMember("UDPCHECK", "udpcheck", ProtocolOption.UDPCHECK)
    VLAN = "vlan"  # AnyMember("VLAN", "vlan", ProtocolOption.VLAN)
    VXLAN = "vxlan"  # AnyMember("VXLAN", "vxlan", ProtocolOption.VXLAN)

    RAW_1 = "raw_1"  # AnyMember(f'RAW_1', f'raw_1', ProtocolOption[f'RAW_1'])
    RAW_2 = "raw_2"  # AnyMember(f'RAW_2', f'raw_2', ProtocolOption[f'RAW_2'])
    RAW_3 = "raw_3"  # AnyMember(f'RAW_3', f'raw_3', ProtocolOption[f'RAW_3'])
    RAW_4 = "raw_4"  # AnyMember(f'RAW_4', f'raw_4', ProtocolOption[f'RAW_4'])
    RAW_5 = "raw_5"  # AnyMember(f'RAW_5', f'raw_5', ProtocolOption[f'RAW_5'])
    RAW_6 = "raw_6"  # AnyMember(f'RAW_6', f'raw_6', ProtocolOption[f'RAW_6'])
    RAW_7 = "raw_7"  # AnyMember(f'RAW_7', f'raw_7', ProtocolOption[f'RAW_7'])
    RAW_8 = "raw_8"  # AnyMember(f'RAW_8', f'raw_8', ProtocolOption[f'RAW_8'])
    RAW_9 = "raw_9"  # AnyMember(f'RAW_9', f'raw_9', ProtocolOption[f'RAW_9'])
    RAW_10 = "raw_10"  # AnyMember(f'RAW_10', f'raw_10', ProtocolOption[f'RAW_10'])
    RAW_11 = "raw_11"  # AnyMember(f'RAW_11', f'raw_11', ProtocolOption[f'RAW_11'])
    RAW_12 = "raw_12"  # AnyMember(f'RAW_12', f'raw_12', ProtocolOption[f'RAW_12'])
    RAW_13 = "raw_13"  # AnyMember(f'RAW_13', f'raw_13', ProtocolOption[f'RAW_13'])
    RAW_14 = "raw_14"  # AnyMember(f'RAW_14', f'raw_14', ProtocolOption[f'RAW_14'])
    RAW_15 = "raw_15"  # AnyMember(f'RAW_15', f'raw_15', ProtocolOption[f'RAW_15'])
    RAW_16 = "raw_16"  # AnyMember(f'RAW_16', f'raw_16', ProtocolOption[f'RAW_16'])
    RAW_17 = "raw_17"  # AnyMember(f'RAW_17', f'raw_17', ProtocolOption[f'RAW_17'])
    RAW_18 = "raw_18"  # AnyMember(f'RAW_18', f'raw_18', ProtocolOption[f'RAW_18'])
    RAW_19 = "raw_19"  # AnyMember(f'RAW_19', f'raw_19', ProtocolOption[f'RAW_19'])
    RAW_20 = "raw_20"  # AnyMember(f'RAW_20', f'raw_20', ProtocolOption[f'RAW_20'])
    RAW_21 = "raw_21"  # AnyMember(f'RAW_21', f'raw_21', ProtocolOption[f'RAW_21'])
    RAW_22 = "raw_22"  # AnyMember(f'RAW_22', f'raw_22', ProtocolOption[f'RAW_22'])
    RAW_23 = "raw_23"  # AnyMember(f'RAW_23', f'raw_23', ProtocolOption[f'RAW_23'])
    RAW_24 = "raw_24"  # AnyMember(f'RAW_24', f'raw_24', ProtocolOption[f'RAW_24'])
    RAW_25 = "raw_25"  # AnyMember(f'RAW_25', f'raw_25', ProtocolOption[f'RAW_25'])
    RAW_26 = "raw_26"  # AnyMember(f'RAW_26', f'raw_26', ProtocolOption[f'RAW_26'])
    RAW_27 = "raw_27"  # AnyMember(f'RAW_27', f'raw_27', ProtocolOption[f'RAW_27'])
    RAW_28 = "raw_28"  # AnyMember(f'RAW_28', f'raw_28', ProtocolOption[f'RAW_28'])
    RAW_29 = "raw_29"  # AnyMember(f'RAW_29', f'raw_29', ProtocolOption[f'RAW_29'])
    RAW_30 = "raw_30"  # AnyMember(f'RAW_30', f'raw_30', ProtocolOption[f'RAW_30'])
    RAW_31 = "raw_31"  # AnyMember(f'RAW_31', f'raw_31', ProtocolOption[f'RAW_31'])
    RAW_32 = "raw_32"  # AnyMember(f'RAW_32', f'raw_32', ProtocolOption[f'RAW_32'])
    RAW_33 = "raw_33"  # AnyMember(f'RAW_33', f'raw_33', ProtocolOption[f'RAW_33'])
    RAW_34 = "raw_34"  # AnyMember(f'RAW_34', f'raw_34', ProtocolOption[f'RAW_34'])
    RAW_35 = "raw_35"  # AnyMember(f'RAW_35', f'raw_35', ProtocolOption[f'RAW_35'])
    RAW_36 = "raw_36"  # AnyMember(f'RAW_36', f'raw_36', ProtocolOption[f'RAW_36'])
    RAW_37 = "raw_37"  # AnyMember(f'RAW_37', f'raw_37', ProtocolOption[f'RAW_37'])
    RAW_38 = "raw_38"  # AnyMember(f'RAW_38', f'raw_38', ProtocolOption[f'RAW_38'])
    RAW_39 = "raw_39"  # AnyMember(f'RAW_39', f'raw_39', ProtocolOption[f'RAW_39'])
    RAW_40 = "raw_40"  # AnyMember(f'RAW_40', f'raw_40', ProtocolOption[f'RAW_40'])
    RAW_41 = "raw_41"  # AnyMember(f'RAW_41', f'raw_41', ProtocolOption[f'RAW_41'])
    RAW_42 = "raw_42"  # AnyMember(f'RAW_42', f'raw_42', ProtocolOption[f'RAW_42'])
    RAW_43 = "raw_43"  # AnyMember(f'RAW_43', f'raw_43', ProtocolOption[f'RAW_43'])
    RAW_44 = "raw_44"  # AnyMember(f"RAW_44", f"raw_44", ProtocolOption[f"RAW_44"])
    RAW_45 = "raw_45"  # AnyMember(f"RAW_45", f"raw_45", ProtocolOption[f"RAW_45"])
    RAW_46 = "raw_46"  # AnyMember(f"RAW_46", f"raw_46", ProtocolOption[f"RAW_46"])
    RAW_47 = "raw_47"  # AnyMember(f"RAW_47", f"raw_47", ProtocolOption[f"RAW_47"])
    RAW_48 = "raw_48"  # AnyMember(f"RAW_48", f"raw_48", ProtocolOption[f"RAW_48"])
    RAW_49 = "raw_49"  # AnyMember(f"RAW_49", f"raw_49", ProtocolOption[f"RAW_49"])
    RAW_50 = "raw_50"  # AnyMember(f"RAW_50", f"raw_50", ProtocolOption[f"RAW_50"])
    RAW_51 = "raw_51"  # AnyMember(f"RAW_51", f"raw_51", ProtocolOption[f"RAW_51"])
    RAW_52 = "raw_52"  # AnyMember(f"RAW_52", f"raw_52", ProtocolOption[f"RAW_52"])
    RAW_53 = "raw_53"  # AnyMember(f"RAW_53", f"raw_53", ProtocolOption[f"RAW_53"])
    RAW_54 = "raw_54"  # AnyMember(f"RAW_54", f"raw_54", ProtocolOption[f"RAW_54"])
    RAW_55 = "raw_55"  # AnyMember(f"RAW_55", f"raw_55", ProtocolOption[f"RAW_55"])
    RAW_56 = "raw_56"  # AnyMember(f"RAW_56", f"raw_56", ProtocolOption[f"RAW_56"])
    RAW_57 = "raw_57"  # AnyMember(f"RAW_57", f"raw_57", ProtocolOption[f"RAW_57"])
    RAW_58 = "raw_58"  # AnyMember(f"RAW_58", f"raw_58", ProtocolOption[f"RAW_58"])
    RAW_59 = "raw_59"  # AnyMember(f"RAW_59", f"raw_59", ProtocolOption[f"RAW_59"])
    RAW_60 = "raw_60"  # AnyMember(f"RAW_60", f"raw_60", ProtocolOption[f"RAW_60"])
    RAW_61 = "raw_61"  # AnyMember(f"RAW_61", f"raw_61", ProtocolOption[f"RAW_61"])
    RAW_62 = "raw_62"  # AnyMember(f"RAW_62", f"raw_62", ProtocolOption[f"RAW_62"])
    RAW_63 = "raw_63"  # AnyMember(f"RAW_63", f"raw_63", ProtocolOption[f"RAW_63"])
    RAW_64 = "raw_64"  # AnyMember(f"RAW_64", f"raw_64", ProtocolOption[f"RAW_64"])

    @property
    def xoa(self) -> XProtocolOption:
        dic = {
            ProtocolOption.ARP: XProtocolOption.ARP,
            ProtocolOption.ETHERNET: XProtocolOption.ETHERNET,
            ProtocolOption.FC: XProtocolOption.FC,
            ProtocolOption.FCOE: XProtocolOption.FCOE,
            ProtocolOption.FCOETAIL: XProtocolOption.FCOETAIL,
            ProtocolOption.GRE_CHECK: XProtocolOption.GRE_CHECK,
            ProtocolOption.GRE_NOCHECK: XProtocolOption.GRE_NOCHECK,
            ProtocolOption.GTP: XProtocolOption.GTP,
            ProtocolOption.ICMP: XProtocolOption.ICMP,
            ProtocolOption.ICMPV6: XProtocolOption.ICMP,
            ProtocolOption.IGMPV1: XProtocolOption.IGMPV1,
            ProtocolOption.IGMPV2: XProtocolOption.IGMPV2,
            ProtocolOption.IGMPV3L0: XProtocolOption.IGMPV3L0,
            ProtocolOption.IGMPV3L1: XProtocolOption.IGMPV3L1,
            ProtocolOption.IPV4: XProtocolOption.IP,
            ProtocolOption.IPV6: XProtocolOption.IPV6,
            ProtocolOption.LLC: XProtocolOption.LLC,
            ProtocolOption.MACCTRL: XProtocolOption.MACCTRL,
            ProtocolOption.MPLS: XProtocolOption.MPLS,
            ProtocolOption.NVGRE: XProtocolOption.NVGRE,
            ProtocolOption.PBBTAG: XProtocolOption.PBBTAG,
            ProtocolOption.RTCP: XProtocolOption.RTCP,
            ProtocolOption.RTP: XProtocolOption.RTP,
            ProtocolOption.SCTP: XProtocolOption.SCTP,
            ProtocolOption.SNAP: XProtocolOption.SNAP,
            ProtocolOption.STP: XProtocolOption.STP,
            ProtocolOption.TCP: XProtocolOption.TCP,
            ProtocolOption.TCPCHECK: XProtocolOption.TCPCHECK,
            ProtocolOption.UDP: XProtocolOption.UDP,
            ProtocolOption.UDPCHECK: XProtocolOption.UDPCHECK,
            ProtocolOption.VLAN: XProtocolOption.VLAN,
            ProtocolOption.VXLAN: XProtocolOption.VXLAN,
        }
        dic.update(
            {
                ProtocolOption[f"RAW_{i}"]: XProtocolOption[f"RAW_{i}"]
                for i in range(1, 65)
            }
        )
        return dic[self]


class PortRateCapProfile(Enum):
    PHYSICAL = (
        "physical_port_rate"  # AnyMember("Physical Port Rate", "physical_port_rate")
    )
    CUSTOM = "custom_rate_cap"  # AnyMember("Custom Rate Cap", "custom_rate_cap")


class RateType(Enum):
    PPS = "pps"  # AnyMember("Pps", "pps")
    FRACTION = "fraction"  # AnyMember("Fraction", "fraction")


class PortRateCapUnit(Enum):
    GBPS = "1e9_bps"  # AnyMember("Gbps", "1e9_bps")
    MBPS = "1e6_bps"  # AnyMember("Mbps", "1e6_bps")
    KBPS = "1e3_bps"  # AnyMember("Kbps", "1e3_bps")
    BPS = "bps"  # AnyMember("bps", "bps")

    @property
    def scale(self) -> float:
        return {
            PortRateCapUnit.GBPS: 1e9,
            PortRateCapUnit.MBPS: 1e6,
            PortRateCapUnit.KBPS: 1e3,
            PortRateCapUnit.BPS: 1,
        }[self]


class FlowCreationType(Enum):
    STREAM = "stream_based"  # AnyMember("StreamBased", "stream_based")
    MODIFIER = "modifier_based"  # AnyMember("ModifierBased", "modifier_based")


class LatencyMode(Enum):
    FIRST2LAST = "first_to_last"  # AnyMember("First_To_Last", "first_to_last", LatencyMode.FIRST2LAST)
    LAST2LAST = "last_to_last"  # AnyMember("Last_To_Last", "last_to_last", LatencyMode.LAST2LAST)
    FIRST2FIRST = "first_to_first"  # AnyMember("First_To_First", "first_to_first", LatencyMode.FIRST2FIRST)
    LAST2FIRST = "last_to_first"  # AnyMember("Last_To_First", "last_to_first", LatencyMode.LAST2FIRST)

    @property
    def xoa(self) -> XLatencyMode:
        return {
            LatencyMode.FIRST2LAST: XLatencyMode.FIRST2LAST,
            LatencyMode.LAST2LAST: XLatencyMode.LAST2LAST,
            LatencyMode.FIRST2FIRST: XLatencyMode.FIRST2FIRST,
            LatencyMode.LAST2FIRST: XLatencyMode.LAST2FIRST,
        }[self]


class TidAllocationScope(Enum):
    CONFIGURATION_SCOPE = "config_scope"  # AnyMember("ConfigScope", "config_scope")
    RX_PORT_SCOPE = "port_scope"  # AnyMember("PortScope", "port_scope")
    SOURCE_PORT_ID = "source_port_id"  # AnyMember("SourcePortId", "source_port_id")


class MdiMdixMode(Enum):
    AUTO = "auto"  # AnyMember("AUTO", "auto", MDIXMode.AUTO)
    MDI = "mdi"  # AnyMember("MDI", "mdi", MDIXMode.MDI)
    MDIX = "mdix"  # AnyMember("MDIX", "mdix", MDIXMode.MDIX)


class PortSpeedMode(Enum):
    AUTO = "AUTO"  # AnyMember("AUTO", "AUTO")
    F100M = "F100M"  # AnyMember("F100M", "F100M")
    F10M = "F10M"  # AnyMember("F10M", "F10M")
    F10MHDX = "F10MHDX"  # AnyMember("F10MHDX", "F10MHDX")
    F100MHDX = "F100MHDX"  # AnyMember("F100MHDX", "F100MHDX")
    F10M100M = "F10M100M"  # AnyMember("F10M100M", "F10M100M")
    F1G = "F1G"  # AnyMember("F1G", "F1G")
    SPEED_100M1G10G = (
        "SPEED_100M1G10G"  # AnyMember("SPEED_100M1G10G", "SPEED_100M1G10G")
    )
    SPEED_2500M = "SPEED_2500M"  # AnyMember("SPEED_2500M", "SPEED_2500M")
    SPEED_5G = "SPEED_5G"  # AnyMember("SPEED_5G", "SPEED_5G")
    F10G = "F10G"  # AnyMember("F10G", "F10G")
    F40G = "F40G"  # AnyMember("F40G", "F40G")
    F100G = "F100G"  # AnyMember("F100G", "F100G")
    F100M1G = "F100M1G"  # AnyMember("F100M1G", "F100M1G")
    SPEED_100M1G2500M = (
        "SPEED_100M1G2500M"  # AnyMember("SPEED_100M1G2500M", "SPEED_100M1G2500M")
    )

    @property
    def scale(self) -> float:
        return {
            PortSpeedMode.AUTO: 0,
            PortSpeedMode.F10M: 10,
            PortSpeedMode.F100M: 100,
            PortSpeedMode.F1G: 1000,
            PortSpeedMode.F10G: 10000,
            PortSpeedMode.F40G: 40000,
            PortSpeedMode.F100G: 100000,
            PortSpeedMode.F10MHDX: 10,
            PortSpeedMode.F100MHDX: 100,
            PortSpeedMode.F10M100M: 100,
            PortSpeedMode.F100M1G: 1000,
            PortSpeedMode.SPEED_100M1G10G: 10000,
            PortSpeedMode.SPEED_2500M: 2500,
            PortSpeedMode.SPEED_5G: 5000,
            PortSpeedMode.SPEED_100M1G2500M: 2500,
        }[self] * 1_000_000


class BRRMode(Enum):
    MASTER = "master"  # AnyMember("MASTER", "master", BRRMode.MASTER)
    SLAVE = "slave"  # AnyMember("SLAVE", "slave", BRRMode.SLAVE)


class PacketSizeType(Enum):
    IEEE_DEFAULT = (
        "ietf_default"  # AnyMember("IEEEDefault", "ietf_default", LengthType.FIXED)
    )
    CUSTOM_SIZES = (
        "custom_sizes"  # AnyMember("CustomSizes", "custom_sizes", LengthType.FIXED)
    )
    RANGE = "specified"  # AnyMember("Specified", "specified", LengthType.FIXED)
    INCREMENTING = "incrementing"  # AnyMember("Incrementing", "incrementing", LengthType.INCREMENTING)
    BUTTERFLY = "butterfly"  # AnyMember("Butterfly", "butterfly", LengthType.BUTTERFLY)
    RANDOM = "random"  # AnyMember("Random", "random", LengthType.RANDOM)
    MIX = "mixed_sizes"  # AnyMember("MixedSizes", "mixed_sizes", LengthType.MIX)

    @property
    def xoa(self) -> LengthType:
        return {
            PacketSizeType.IEEE_DEFAULT: LengthType.FIXED,
            PacketSizeType.CUSTOM_SIZES: LengthType.FIXED,
            PacketSizeType.RANGE: LengthType.FIXED,
            PacketSizeType.INCREMENTING: LengthType.INCREMENTING,
            PacketSizeType.BUTTERFLY: LengthType.BUTTERFLY,
            PacketSizeType.RANDOM: LengthType.RANDOM,
            PacketSizeType.MIX: LengthType.MIX,
        }[self]


class PayloadType(Enum):
    PATTERN = "pattern"  # AnyMember("Pattern", "pattern", PayloadType.PATTERN)
    INCREMENTING = "incrementing"  # AnyMember("Incrementing", "incrementing", PayloadType.INCREMENTING)
    PRBS = "prbs"  # AnyMember("PRBS", "prbs", PayloadType.PRBS)

    @property
    def xoa(self) -> XPayloadType:
        return {
            PayloadType.PATTERN: XPayloadType.PATTERN,
            PayloadType.INCREMENTING: XPayloadType.INCREMENTING,
            PayloadType.PRBS: XPayloadType.PRBS,
        }[self]


class GroupCountSel(Enum):
    LIST = "List"
    RANGE = "Range"


class StreamTypeInfo(Enum):
    MULTICAST = "multicast"
    UNICAST_NOT_BURDEN = "unicast_not_burden"
    UNICAST_BURDEN = "unicast_burden"


class IGMPv1Type(Enum):
    QUERY = 1
    REPORT = 2


class IGMPv3GroupRecordTypes(Enum):
    MODE_IS_INCLUDE = 1
    MODE_IS_EXCLUDE = 2
    CHANGE_TO_INCLUDE_MODE = 3
    CHANGE_TO_EXCLUDE_MODE = 4
    ALLOW_NEW_SOURCES = 5
    BLOCK_OLD_SOURCES = 6


class IgmpRequestType(Enum):
    JOIN = IGMP_V2_JOIN
    LEAVE = IGMP_V2_LEAVE


class ResultState(Enum):
    PENDING = "Pending"
    PASS = "Pass"
    FAIL = "Fail"
