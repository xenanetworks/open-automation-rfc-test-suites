import os
from enum import Enum as CaseSensitiveEnum
from xoa_driver import ports
from xoa_driver.enums import (
    ProtocolOption,
    LengthType,
    ModifierAction,
    LatencyMode,
    PayloadType,
    MDIXMode,
    BRRMode,
    PortSpeedMode,
)


class Enum(CaseSensitiveEnum):
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if member.value == value.lower():
                    return member


# queue message action code
ADD_ACTION = "ADD"
DEL_ACTION = "DEL"
GET_ALL_TESTERS = "ALL"
UPDATE_ACTION = "UPDATE"

OWNER = "xoa-manager"

REQUEST_ID_LIMIT = 0xFFFFFFFF


ACTIVE_MODE = "ACTIVE"
PASSIVE_MODE = "PASSIVE"


SUCCESS = 1
FAIL = 2

MICRO_TPLD_LENGTH = 6
ETHERNET_FCS_LENGTH = 4
STANDARD_TPLD_LENGTH = 20
MIN_PAYLOAD_LENGTH = 2
MICRO_TPLD_TOTAL_LENGTH = MICRO_TPLD_LENGTH + ETHERNET_FCS_LENGTH
STANDARD_TPLD_TOTAL_LENGTH = (
    STANDARD_TPLD_LENGTH + MIN_PAYLOAD_LENGTH + ETHERNET_FCS_LENGTH
)
MIN_REFRESH_TIMER_INTERNAL = 100.0
DEFAULT_PACKET_SIZE_LIST = [64, 128, 256, 512, 1024, 1280, 1518]
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
MIXED_DEFAULT_WEIGHTS = [0, 0, 0, 0, 57, 3, 5, 1, 2, 5, 1, 4, 4, 18, 0, 0]
MIXED_PACKET_CONFIG_LENGTH_INDICES = [0, 1, 14, 15]
IMIX_AVERAGE = 463.501953
# MAX_PACKET_LIMIT_VALUE = 0x7FFFFFFF
MAX_MASK_BIT_LENGTH = 16
UNREACH_BYTE_VALUE = 256
DEFAULT_SEGMENT_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "reference/segment_refs",
    )
)
SERVER_CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "config/server.json")
)
STANDARD_SEGMENT_VALUE = (128, 256, 512, 1024, 2048)

MdixPorts = (
    ports.POdin1G3S6P,
    ports.POdin1G3S6P_b,
    ports.POdin1G3S6PE,
    ports.POdin1G3S2PT,
)

BrrPorts = (ports.POdin1G3S6PT1RJ45,)
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

PCSPMAPorts = (ports.PThor400G7S1P_c, ports.PThor400G7S1P_b)



class TestTopology(Enum):
    PAIRS = "pairs"
    BLOCKS = "blocks"
    MESH = "mesh"

    @property
    def is_mesh_topology(self) -> bool:
        return self == type(self).MESH

    @property
    def is_pair_topology(self) -> bool:
        return self == type(self).PAIRS


class TrafficDirection(Enum):
    EAST_TO_WEST = "east_to_west"
    WEST_TO_EAST = "west_to_east"
    BIDIRECTION = "bidirectional"


class PacketSizeType(Enum):
    IETF_DEFAULT = "ietf_default"
    CUSTOM = "custom_sizes"
    RANGE = "specified"
    INCREMENTING = "incrementing"
    BUTTERFLY = "butterfly"
    RANDOM = "random"
    MIX = "mixe_sizes"

    @property
    def is_custom(self) -> bool:
        return self == type(self).CUSTOM

    @property
    def is_mix(self) -> bool:
        return self == type(self).MIX

    @property
    def is_fix(self) -> bool:
        return self in [type(self).IETF_DEFAULT, type(self).CUSTOM, type(self).RANGE]

    def to_xmp(self):
        if self.is_fix:
            return LengthType.FIXED
        else:
            return LengthType[self.name]


class PayloadTypeStr(Enum):
    INCREMENTING = "incrementing"
    PATTERN = "pattern"
    PRBS = "prbs"

    def to_xmp(self):
        return PayloadType[self.name]


class TidAllocationScope(Enum):
    CONFIGURATION_SCOPE = "config_scope"
    RX_PORT_SCOPE = "port_scope"
    SOURCE_PORT_ID = "source_port_id"

    @property
    def is_config_scope(self) -> bool:
        return self == TidAllocationScope.CONFIGURATION_SCOPE


class OuterLoopMode(Enum):
    ITERATION = "iterations"
    PACKET_SIZE = "packet_size"

    @property
    def is_iteration(self) -> bool:
        return self == type(self).ITERATION


class MACLearningMode(Enum):
    NEVER = "never"
    ONCE = "once"
    EVERYTRIAL = "every_trial"


class DurationType(Enum):
    TIME = "time"
    FRAME = "frames"

    @property
    def is_time_duration(self) -> bool:
        return self == type(self).TIME


class DurationTimeUnit(Enum):
    SECOND = "seconds"
    MINUTE = "minutes"
    HOUR = "hours"

    @property
    def scale(self) -> int:
        if self == type(self).SECOND:
            return 1
        elif self == type(self).MINUTE:
            return 60
        elif self == type(self).HOUR:
            return 3600
        raise ValueError("No scale!")


class DurationFrameUnit(Enum):
    FRAME = "frames"
    K_FRAME = "10e3_frames"
    M_FRAME = "10e6_frames"
    G_FRAME = "10e9_frames"

    @property
    def scale(self):
        if self == type(self).FRAME:
            return 1
        elif self == type(self).K_FRAME:
            return 1e3
        elif self == type(self).M_FRAME:
            return 1e6
        elif self == type(self).G_FRAME:
            return 1e9
        raise ValueError("No scale!")


class TestType(Enum):
    THROUGHPUT = "throughput"
    LATENCY_JITTER = "latency"
    FRAME_LOSS_RATE = "loss"
    BACK_TO_BACK = "back_to_back"

    @property
    def is_latency(self):
        return self == type(self).LATENCY_JITTER


class SearchType(Enum):
    BINARY_SEARCH = "binary_search"
    FAST_BINARY_SEARCH = "fast_binary_search"

    @property
    def is_fast(self) -> bool:
        return self == SearchType.FAST_BINARY_SEARCH


class RateResultScopeType(Enum):
    COMMON = "common_result"
    PER_SOURCE_PORT = "per_sourc_port_result"

    @property
    def is_per_source_port(self) -> bool:
        return self == RateResultScopeType.PER_SOURCE_PORT


class AdditionalStatisticsOption(Enum):
    LATENCY_AND_JITTER = "latency_and_jitter"


class LatencyModeStr(Enum):
    FIRST2LAST = "first_to_last"
    LAST2LAST = "last_to_last"
    FIRST2FIRST = "first_to_first"
    LAST2FIRST = "last_to_first"

    def to_xmp(self) -> "LatencyMode":
        return LatencyMode[self.name]


class TestResultState(Enum):
    PENDING = "pending"
    PASS = "pass"
    FAIL = "fail"


class AcceptableLossType(Enum):
    PERCENT = "percent"
    FRAME = "frames"


class PortRateCapProfile(Enum):
    PHYSICAL = "physical_port_rate"
    CUSTOM = "custom_rate_cap"

    @property
    def is_custom(self) -> bool:
        return self == PortRateCapProfile.CUSTOM


class PortRateCapUnit(Enum):
    GBPS = "1e9_bps"
    MBPS = "1e6_bps"
    KBPS = "1e3_bps"
    BPS = "bps"

    def scale(self) -> int:
        return {
            PortRateCapUnit.GBPS: 1e9,
            PortRateCapUnit.MBPS: 1e6,
            PortRateCapUnit.KBPS: 1e3,
            PortRateCapUnit.BPS: 1,
        }[self]


class MdiMdixMode(Enum):
    AUTO = "auto"
    MDI = "mdi"
    MDIX = "mdix"

    def to_xmp(self) -> "MDIXMode":
        return MDIXMode[self.name]


class BRRModeStr(Enum):
    MASTER = "master"
    SLAVE = "slave"

    def to_xmp(self) -> "BRRMode":
        return BRRMode[self.name]


class FECModeStr(Enum):
    ON = "on"
    OFF = "off"
    FC_FEC = "fc_fec"


class PortSpeedStr(Enum):
    AUTO = "auto"
    F100M = "f100m"
    F1G = "f1g"
    F2500M = "f2500m"
    F5G = "f5g"
    F10G = "f10g"
    F100M1G = "f100m1g"
    F100M1G2500M = "f100m1g2500m"
    F10M = "f10m"
    F40G = "f40g"
    F100G = "f100g"
    F10MHDX = "f10mhdx"
    F100MHDX = "f100mhdx"
    F10M100M = "f10m100m"
    F100M1G10G = "f100m1g10g"
    F25G = "f25g"
    F50G = "f50g"
    F200G = "f200g"
    F400G = "f400g"
    F800G = "f800g"
    F1600G = "f1600g"
    UNKNOWN = "unknown"

    @property
    def is_auto(self):
        return self == PortSpeedStr.AUTO

    def to_xmp(self) -> "PortSpeedMode":
        return PortSpeedMode[self.name]


class PortGroup(Enum):
    EAST = "east"
    WEST = "west"
    UNDEFINED = "undefined"

    @property
    def is_east(self):
        return self == PortGroup.EAST

    @property
    def is_west(self):
        return self == PortGroup.WEST


class ModifierActionOption(Enum):
    INC = "increment"
    DEC = "decrement"
    RANDOM = "random"

    def to_xmp(self) -> "ModifierAction":
        return ModifierAction[self.name]


class FlowCreationType(Enum):
    STREAM = "stream_based"
    MODIFIER = "modifier_based"

    @property
    def is_stream_based(self):
        return self == FlowCreationType.STREAM


class ThroughputUnit(Enum):
    BIT_PER_SEC = "bps"
    FRAME_PER_SEC = "fps"


class MulticastRole(Enum):
    UNDEFINED = "undefined"


class SegmentType(Enum):
    # RAW = "raw"
    ETHERNET = "ethernet"
    VLAN = "vlan"
    ARP = "arp"
    IP = "ipv4"
    IPV6 = "ipv6"
    UDP = "udp"
    TCP = "tcp"
    LLC = "llc"
    SNAP = "snap"
    GTP = "gtp"
    ICMP = "icmp"
    # ICMPV6 = "icmpv6"
    RTP = "rtp"
    RTCP = "rtcp"
    STP = "stp"
    SCTP = "sctp"  # added
    MACCTRL = "macctrl"
    MPLS = "mpls"
    PBBTAG = "pbbtag"
    FCOE = "fcoe"  # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1
    FC = "fc"
    # FCOEHEAD = "fcoehead"  # added
    FCOETAIL = "fcoetail"
    IGMPV3L0 = "igmpv3l0"
    IGMPV3L1 = "igmpv3l1"
    # IGMPV3GR = "igmpv3gr"
    # IGMPV3MR = "igmpv3mr"
    # MLDV2AR = "mldv2ar"
    UDPCHECK = "udpcheck"
    IGMPV2 = "igmpv2"
    # "MPLS_TP_OAM"
    GRE_NOCHECK = "gre_nocheck"
    GRE_CHECK = "gre_check"
    TCPCHECK = "tcp_check"
    # "GTPV1L0"
    # "GTPV1L1"
    # "GTPV2L0"
    # "GTPV2L1"
    IGMPV1 = "igmpv1"
    # "PWETHCTRL"
    VXLAN = "vxlan"
    # "ETHERNET_8023"
    NVGRE = "nvgre"
    # "DHCPV4"
    # "GENEVE"
    # "XENA_TPLD"
    # "XENA_TPLD_PI"
    # "XENA_MICROTPLD"
    # "ETHERNET_FCS"
    # "MACCTRLPFC"
    # "ECPRI"
    # "ROE"
    # "ETHERTYPE"
    # Generat RAW form 1...64 bytes
    _ignore_ = "SegmentType i"
    SegmentType = vars()
    for i in range(1, 65):
        SegmentType[f"RAW_{i}"] = f"raw_{i}"  # type: ignore

    def to_xmp(self) -> "ProtocolOption":
        return ProtocolOption[self.name]

    @property
    def is_raw(self) -> bool:
        return self.value.lower().startswith("raw")

    @property
    def raw_length(self) -> int:
        if not self.is_raw:
            return 0
        return int(self.value.split("_")[-1])


class StreamState(Enum):
    OFF = "off"
    ON = "on"
    SUPPRESS = "suppress"


class StreamRateType(Enum):
    FRACTION = "fraction"
    PPS = "pps"
    L2MBPS = "l2mbps"


class StreamPacketLengthType(Enum):
    FIXED = "fixed"
    INCREMENTING = "incrementing"
    BUTTERFLY = "butterfly"
    RANDOM = "random"
    MIX = "mix"


class FramePacketTerminology(Enum):
    FRAME = "fps"
    PACKET = "pps"


class PassDisplayType(Enum):
    PASS = "pass"
    DONE = "done"


class PortProtocolVersion(Enum):
    ETHERNET = 0
    IPV4 = 4
    IPV6 = 6

    @property
    def is_ipv4(self) -> bool:
        return self == type(self).IPV4

    @property
    def is_ipv6(self) -> bool:
        return self == type(self).IPV6

    @property
    def is_l3(self) -> bool:
        return self != type(self).ETHERNET


class IPVersion(Enum):
    IPV4 = 4
    IPV6 = 6


class ARPSenarioType(Enum):
    DEFAULT = 0
    GATEWAY = 1
    REMOTE = 2
    PUBLIC = 3


class IPPrefixLength(Enum):
    IPv4 = 32
    IPv6 = 128


class TestState(Enum):
    L3_LEARNING = 3
    RUNNING_TEST = 5

