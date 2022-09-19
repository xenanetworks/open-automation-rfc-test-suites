import os
from enum import Enum
from ..conversion.enum_changer import AnyMember, EnumChanger
from xoa_driver.enums import (
    ModifierAction,
    ProtocolOption,
    LatencyMode,
    MDIXMode,
    BRRMode,
    LengthType,
    PayloadType,
)

DEFAULT_SEGMENT_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "reference/segment_refs",
    )
)


class RMulticastRole(EnumChanger):
    MC_SOURCE = AnyMember("McSource", "mc_source")
    MC_DESTINATION = AnyMember("McDestination", "mc_destination")
    UC_BURDEN = AnyMember("UcBurden", "uc_burden")
    UNDEFINED = AnyMember("Undefined", "undefined")


class RTestTopology(EnumChanger):
    PAIRS = AnyMember("PAIRS", "pairs")
    BLOCKS = AnyMember("BLOCKS", "blocks")
    MESH = AnyMember("MESH", "mesh")


class RTrafficDirection(EnumChanger):
    EAST_TO_WEST = AnyMember("EAST_TO_WEST", "east_to_west")
    WEST_TO_EAST = AnyMember("WEST_TO_EAST", "west_to_east")
    BIDIRECTION = AnyMember("BIDIR", "bidir")


class RIgmpVersion(EnumChanger):
    IGMP_V1 = AnyMember("IGMP_V1", "igmp_v1")
    IGMP_V2_OR_MLD_V1 = AnyMember("IGMP_V2", "igmp_v2_or_mld_v1")
    IGMP_V3_OR_MLD_V2 = AnyMember("IGMP_V3", "igmp_v3_or_mld_v2")


# class PortGroup(Enum):
#     EAST = "east"
#     WEST = "west"
#     UNDEFINED = "undefined"


class RIPVersion(EnumChanger):
    IPV4 = AnyMember("IP", "ipv4", ProtocolOption.IP)
    IPV6 = AnyMember("IPv6", "ipv6", ProtocolOption.IPV6)


class RDisplayUnit(EnumChanger):
    MILLI_SECONDS = AnyMember("Millisecs", "millisecs")
    MICRO_SECONDS = AnyMember("Microsecs", "microsecs")

    @property
    def scale(self) -> float:
        if self == RDisplayUnit.MILLI_SECONDS:
            return 1e3
        else:
            return 1e6


# class RModifierAction(EnumChanger):
#     INC = AnyMember("inc", "increment", ModifierAction.INC)
#     DEC = AnyMember("dec", "decrement", ModifierAction.DEC)
#     RANDOM = AnyMember("rnd", "random", ModifierAction.RANDOM)


class RProtocolOption(EnumChanger):
    ARP = AnyMember("ARP", "arp", ProtocolOption.ARP)
    ETHERNET = AnyMember("ETHERNET", "ethernet", ProtocolOption.ETHERNET)
    FC = AnyMember("FC", "fc", ProtocolOption.FC)
    FCOE = AnyMember("FCOEHEAD", "fcoe", ProtocolOption.FCOE)
    FCOETAIL = AnyMember("FCOETAIL", "fcoetail", ProtocolOption.FCOETAIL)
    GRE_CHECK = AnyMember("GRE_CHECK", "gre_check", ProtocolOption.GRE_CHECK)
    GRE_NOCHECK = AnyMember("GRE_NOCHECK", "gre_nocheck", ProtocolOption.GRE_NOCHECK)
    GTP = AnyMember("GTP", "gtp", ProtocolOption.GTP)
    ICMP = AnyMember("ICMP", "icmp", ProtocolOption.ICMP)
    ICMPV6 = AnyMember("ICMPV6", "icmpv6", ProtocolOption.ICMP)
    IGMPV1 = AnyMember("IGMPV1", "igmpv1", ProtocolOption.IGMPV1)
    IGMPV2 = AnyMember("IGMPV2", "igmpv2", ProtocolOption.IGMPV2)
    MLDV2_AR = AnyMember("MLDV2_AR", "mldv2_ar")
    IGMPV3_GR = AnyMember("IGMPV3_GR", "igmpv3_gr")
    IGMPV3_MR = AnyMember("IGMPV3_MR", "igmpv3_mr")
    IGMPV3L0 = AnyMember("IGMPV3L0", "igmpv3l0", ProtocolOption.IGMPV3L0)
    IGMPV3L1 = AnyMember("IGMPV3L1", "igmpv3l1", ProtocolOption.IGMPV3L1)
    IPV4 = AnyMember("IP", "ipv4", ProtocolOption.IP)
    IPV6 = AnyMember("IPv6", "ipv6", ProtocolOption.IPV6)
    LLC = AnyMember("LLC", "llc", ProtocolOption.LLC)
    MACCTRL = AnyMember("MACCTRL", "macctrl", ProtocolOption.MACCTRL)
    MPLS = AnyMember("MPLS", "mpls", ProtocolOption.MPLS)
    NVGRE = AnyMember("NVGRE", "nvgre", ProtocolOption.NVGRE)
    PBBTAG = AnyMember("PBBTAG", "pbbtag", ProtocolOption.PBBTAG)
    RTCP = AnyMember("RTCP", "rtcp", ProtocolOption.RTCP)
    RTP = AnyMember("RTP", "rtp", ProtocolOption.RTP)
    SCTP = AnyMember("SCTP", "sctp", ProtocolOption.SCTP)
    SNAP = AnyMember("SNAP", "snap", ProtocolOption.SNAP)
    STP = AnyMember("STP", "stp", ProtocolOption.STP)
    TCP = AnyMember("TCP", "tcp", ProtocolOption.TCP)
    TCPCHECK = AnyMember("TCPCHECK", "tcp_check", ProtocolOption.TCPCHECK)
    UDP = AnyMember("UDP", "udp", ProtocolOption.UDP)
    UDPCHECK = AnyMember("UDPCHECK", "udpcheck", ProtocolOption.UDPCHECK)
    VLAN = AnyMember("VLAN", "vlan", ProtocolOption.VLAN)
    VXLAN = AnyMember("VXLAN", "vxlan", ProtocolOption.VXLAN)

    _ignore_ = "ProtocolOption i"
    RProtocolOption = vars()
    for i in range(1, 65):
        RProtocolOption[f"RAW_{i}"] = AnyMember(
            f"RAW_{i}", f"raw_{i}", ProtocolOption[f"RAW_{i}"]
        )


class RPortRateCapProfile(EnumChanger):
    PHYSICAL = AnyMember("Physical Port Rate", "physical_port_rate")
    CUSTOM = AnyMember("Custom Rate Cap", "custom_rate_cap")


class RRateType(EnumChanger):
    PPS = AnyMember("Pps", "pps")
    FRACTION = AnyMember("Fraction", "fraction")


class RPortRateCapUnit(EnumChanger):
    GBPS = AnyMember("Gbps", "1e9_bps")
    MBPS = AnyMember("Mbps", "1e6_bps")
    KBPS = AnyMember("Kbps", "1e3_bps")
    BPS = AnyMember("bps", "bps")


class RFlowCreationType(EnumChanger):
    STREAM = AnyMember("StreamBased", "stream_based")
    MODIFIER = AnyMember("ModifierBased", "modifier_based")


class RLatencyMode(EnumChanger):
    FIRST2LAST = AnyMember("First_To_Last", "first_to_last", LatencyMode.FIRST2LAST)
    LAST2LAST = AnyMember("Last_To_Last", "last_to_last", LatencyMode.LAST2LAST)
    FIRST2FIRST = AnyMember("First_To_First", "first_to_first", LatencyMode.FIRST2FIRST)
    LAST2FIRST = AnyMember("Last_To_First", "last_to_first", LatencyMode.LAST2FIRST)


class RTidAllocationScope(EnumChanger):
    CONFIGURATION_SCOPE = AnyMember("ConfigScope", "config_scope")
    RX_PORT_SCOPE = AnyMember("PortScope", "port_scope")
    SOURCE_PORT_ID = AnyMember("SourcePortId", "source_port_id")


class RMdiMdixMode(EnumChanger):
    AUTO = AnyMember("AUTO", "auto", MDIXMode.AUTO)
    MDI = AnyMember("MDI", "mdi", MDIXMode.MDI)
    MDIX = AnyMember("MDIX", "mdix", MDIXMode.MDIX)


class RPortSpeedMode(EnumChanger):
    AUTO = AnyMember("AUTO", "AUTO")
    F100M = AnyMember("F100M", "F100M")
    F10M = AnyMember("F10M", "F10M")
    F10MHDX = AnyMember("F10MHDX", "F10MHDX")
    F100MHDX = AnyMember("F100MHDX", "F100MHDX")
    F10M100M = AnyMember("F10M100M", "F10M100M")
    F1G = AnyMember("F1G", "F1G")
    SPEED_100M1G10G = AnyMember("SPEED_100M1G10G", "SPEED_100M1G10G")
    SPEED_2500M = AnyMember("SPEED_2500M", "SPEED_2500M")
    SPEED_5G = AnyMember("SPEED_5G", "SPEED_5G")
    F10G = AnyMember("F10G", "F10G")
    F40G = AnyMember("F40G", "F40G")
    F100G = AnyMember("F100G", "F100G")
    F100M1G = AnyMember("F100M1G", "F100M1G")
    SPEED_100M1G2500M = AnyMember("SPEED_100M1G2500M", "SPEED_100M1G2500M")

    @property
    def scale(self) -> float:
        return {
            RPortSpeedMode.AUTO: 0,
            RPortSpeedMode.F10M: 10,
            RPortSpeedMode.F100M: 100,
            RPortSpeedMode.F1G: 1000,
            RPortSpeedMode.F10G: 10000,
            RPortSpeedMode.F40G: 40000,
            RPortSpeedMode.F100G: 100000,
            RPortSpeedMode.F10MHDX: 10,
            RPortSpeedMode.F100MHDX: 100,
            RPortSpeedMode.F10M100M: 100,
            RPortSpeedMode.F100M1G: 1000,
            RPortSpeedMode.SPEED_100M1G10G: 10000,
            RPortSpeedMode.SPEED_2500M: 2500,
            RPortSpeedMode.SPEED_5G: 5000,
            RPortSpeedMode.SPEED_100M1G2500M: 2500,
        }[self] * 1_000_000


class RBRRMode(EnumChanger):
    MASTER = AnyMember("MASTER", "master", BRRMode.MASTER)
    SLAVE = AnyMember("SLAVE", "slave", BRRMode.SLAVE)


class RPacketSizeType(EnumChanger):
    IEEE_DEFAULT = AnyMember("IEEEDefault", "ietf_default", LengthType.FIXED)
    CUSTOM_SIZES = AnyMember("CustomSizes", "custom_sizes", LengthType.FIXED)
    RANGE = AnyMember("Specified", "specified", LengthType.FIXED)
    INCREMENTING = AnyMember("Incrementing", "incrementing", LengthType.INCREMENTING)
    BUTTERFLY = AnyMember("Butterfly", "butterfly", LengthType.BUTTERFLY)
    RANDOM = AnyMember("Random", "random", LengthType.RANDOM)
    MIX = AnyMember("MixedSizes", "mixed_sizes", LengthType.MIX)


class RPayloadType(EnumChanger):
    PATTERN = AnyMember("Pattern", "pattern", PayloadType.PATTERN)
    INCREMENTING = AnyMember("Incrementing", "incrementing", PayloadType.INCREMENTING)
    PRBS = AnyMember("PRBS", "prbs", PayloadType.PRBS)


class GroupCountSel(Enum):
    LIST = "List"
    RANGE = "Range"


class StreamTypeInfo(Enum):
    MULTICAST = "multicast"
    UNICAST_NOT_BURDEN = "unicast_not_burden"
    UNICAST_BURDEN = "unicast_burden"


# class SourcePortType(Enum):
#     MC_AND_UC_NOT_BURDENS = "multicast_and_unicast_not_burden"
#     MC_AND_UC_BURDENS = "multicast_and_unicast_burden"
#     MC = "multicast"

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


class TestState(Enum):
    L3_LEARNING = 3
    RUNNING_TEST = 5


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


class StartTrafficMode(Enum):
    MC_PORTS = "MC_PORTS"
    MC_AND_BURDEN_PORTS = "MC_AND_BURDEN_PORTS"
    ALL_PORTS = "ALL_PORTS"


class ResultState(Enum):
    PENDING = "Pending"
    PASS = "Pass"
    FAIL = "Fail"


FILTER_M0M1_L0L1 = 196611
