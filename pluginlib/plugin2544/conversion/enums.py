from enum import Enum as CaseSensitiveEnum

from pluginlib.plugin2544.utils import constants as const


class Enum(CaseSensitiveEnum):
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if member.value == value.lower():
                    return member


class ODurationType(Enum):
    TIME = "seconds"
    FRAME = "frames"

    @property
    def core(self):
        return const.DurationType[self.name]


class OSearchType(Enum):
    BINARY_SEARCH = "binarysearch"
    FAST_BINARY_SEARCH = "fastbinarysearc"

    @property
    def core(self):
        return const.SearchType[self.name]


class ODurationFrameUnit(Enum):
    FRAME = "frames"
    K_FRAME = "kframes"
    M_FRAME = "mframes"
    G_FRAME = "gframes"

    @property
    def core(self):
        return const.DurationFrameUnit[self.name]


class OTrafficDirection(Enum):
    EAST_TO_WEST = "east_west"
    WEST_TO_EAST = "west_east"
    BIDIRECTION = "bidir"

    @property
    def core(self):
        return const.TrafficDirection[self.name]


class OPacketSizeType(Enum):
    IETF_DEFAULT = "ieeedefault"
    CUSTOM = "customsizes"
    RANGE = "specified"
    INCREMENTING = "incrementing"
    BUTTERFLY = "butterfly"
    RANDOM = "random"
    MIX = "mixedsizes"

    @property
    def core(self):
        return const.PacketSizeType[self.name]


class OModifierActionOption(Enum):
    INC = "inc"
    DEC = "dec"
    RANDOM = "rnd"

    @property
    def core(self):
        return const.ModifierActionOption[self.name]


class OPortRateCapUnit(Enum):
    GBPS = "gbps"
    MBPS = "mbps"
    KBPS = "kbps"
    BPS = "bps"

    @property
    def core(self):
        return const.PortRateCapUnit[self.name]


class OPortRateCapProfile(Enum):
    PHYSICAL = "Physical Port Rate"
    CUSTOM = "Custom Rate Cap"

    @property
    def core(self):
        return const.PortRateCapProfile[self.name]


class OOuterLoopMode(Enum):
    ITERATION = "iterations"
    PACKET_SIZE = "packetsize"

    @property
    def core(self):
        return const.OuterLoopMode[self.name]


class OMACLearningMode(Enum):
    NEVER = "never"
    ONCE = "once"
    EVERYTRIAL = "everytrial"

    @property
    def core(self):
        return const.MACLearningMode[self.name]


class OFlowCreationType(Enum):
    STREAM = "streambased"
    MODIFIER = "modifierbased"

    @property
    def core(self):
        return const.FlowCreationType[self.name]


class OTidAllocationScope(Enum):
    CONFIGURATION_SCOPE = "configscope"
    RX_PORT_SCOPE = "portscope"
    SOURCE_PORT_ID = "srcportid"

    @property
    def core(self):
        return const.TidAllocationScope[self.name]


class ORateResultScopeType(Enum):
    COMMON = "commonresult"
    PER_SOURCE_PORT = "persrcportresult"

    @property
    def core(self):
        return const.RateResultScopeType[self.name]


# special_type_map = {
#     "ip": "ipv4",
#     "mldv2_ar": "mldv2ar",
#     "igmpv3_mr": "igmpv3mr",
#     "igmpv3_gr": "igmpv3gr",
# }


class OTestType(Enum):
    THROUGHPUT = "throughput"
    LATENCY_JITTER = "latency"
    FRAME_LOSS_RATE = "loss"
    BACK_TO_BACK = "back2back"

    @property
    def core(self):
        return const.TestType[self.name]


class OSegmentType(Enum):
    ETHERNET = "ethernet"
    VLAN = "vlan"
    ARP = "arp"
    IP = "ip"
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

    _ignore_ = "OSegmentType i"
    OSegmentType = vars()
    for i in range(1, 65):
        OSegmentType[f"RAW_{i}"] = f"raw_{i}"  # type: ignore

    @property
    def core(self):
        return const.SegmentType[self.name]

    @property
    def is_raw(self) -> bool:
        return self.value.lower().startswith("raw")

    @property
    def raw_length(self) -> int:
        if not self.is_raw:
            return 0
        return int(self.value.split("_")[-1])
