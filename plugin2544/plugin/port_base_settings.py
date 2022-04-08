from typing import List,  TYPE_CHECKING

from ..utils.logger import logger
from .control_ports import Structure
from xoa_driver.utils import apply
from xoa_driver.misc import Token
from xoa_driver import ports
from xoa_driver.enums import (
    OnOff,
    YesNo,
    FECMode,
    AutoNegMode,
    AutoNegTecAbility,
    AutoNegFecOption,
    PauseMode,
    LinkTrainMode,
    PAM4FrameSize,
    LinkTrainingInitCondition,
    NRZPreset,
    TimeoutMode,
    TPLDMode,
)
from ..utils.errors import BXMPWarning
from ..utils.constants import (
    STANDARD_SEGMENT_VALUE,
    AutoNegPorts,
    BrrPorts,
    FECModeStr,
    MdiMdixMode,
    BRRModeStr,
    LatencyModeStr,
    MdixPorts,
    PCSPMAPorts,
)

from ..model import TestConfiguration

if TYPE_CHECKING:
    from ..model import (
        PortConfiguration,
        HeaderSegment,
        FrameSizeConfiguration,
    )


def set_latency_offset(
    port: "ports.GenericL23Port", latency_offset_ms: int
) -> List["Token"]:
    # set latency offset
    return [port.latency_config.offset.set(offset=latency_offset_ms)]


def set_ip_address(
    port: "ports.GenericL23Port",
    port_conf: "PortConfiguration",
) -> List["Token"]:
    if port_conf.profile.protocol_version.is_ipv4:
        # ip address, net mask, gateway
        ipv4_properties = port_conf.ipv4_properties
        subnet_mask = ipv4_properties.routing_prefix.to_ipv4()
        return [
            port.net_config.ipv4.address.set(
                ipv4_address=ipv4_properties.address,
                subnet_mask=subnet_mask,
                gateway=ipv4_properties.gateway,
                wild="0.0.0.0",
            )
        ]

    elif port_conf.profile.protocol_version.is_ipv6:
        ipv6_properties = port_conf.ipv6_properties
        return [
            port.net_config.ipv6.address.set(
                ipv6_address=ipv6_properties.address,
                gateway=ipv6_properties.gateway,
                subnet_prefix=ipv6_properties.routing_prefix,
                wildcard_prefix=128,
            )
        ]
    else:  # port_conf.protocol_version == PortProtocolVersion.ETHERNET:
        return []


def set_arpping(port: "ports.GenericL23Port") -> List["Token"]:
    return [
        port.net_config.ipv4.arp_reply.set(OnOff.ON),  # P_ARPREPLY
        port.net_config.ipv6.arp_reply.set(OnOff.ON),  # P_ARPV6REPLY
        port.net_config.ipv4.ping_reply.set(OnOff.ON),  # P_PINGREPLY
        port.net_config.ipv6.ping_reply.set(OnOff.ON),  # P_PINGV6REPLY
    ]


def set_interframe_gap(
    port: "ports.GenericL23Port", inter_frame_gap: int
) -> List["Token"]:
    return [port.interframe_gap.set(min_byte_count=inter_frame_gap)]


def set_speed_reduction(
    port: "ports.GenericL23Port", speed_reduction_ppm: int
) -> List["Token"]:
    # speed reduction
    return [port.speed.reduction.set(ppm=speed_reduction_ppm)]


def set_pause_mode(
    port: "ports.GenericL23Port", pause_mode_enabled: bool
) -> List["Token"]:
    # pause mode
    return [port.pause.set(on_off=OnOff(int(pause_mode_enabled)))]


def set_fec_mode(
    port: "ports.GenericL23Port",
    fec_enabled: "FECModeStr",
) -> List["Token"]:
    # fec mode
    # TODO: need to distinguish which mode to set
    tokens = []
    if fec_enabled:
        if port.info.capabilities.can_fec == FECMode.OFF:
            para = f"fec_enabled"
            logger.warning(str(BXMPWarning(para, False, port, "FEC")))
        else:
            tokens.append(port.fec_mode.set(FECMode.ON))
    return tokens


def set_auto_negotiation(
    port: "ports.GenericL23Port", auto_neg_enabled: bool
) -> List["Token"]:
    # auto negotiation
    tokens = []
    if not auto_neg_enabled:
        pass
    elif not bool(port.info.capabilities.can_set_autoneg):
        logger.warning(
            str(BXMPWarning(f"auto_neg_enabled", False, port, "auto negotiation"))
        )

    elif not isinstance(port, AutoNegPorts):  # port not support
        logger.warning(
            str(BXMPWarning(f"auto_neg_enabled", False, port, "auto negotiation"))
        )
    else:
        tokens.append(port.autonneg_selection.set(OnOff.ON))

    return tokens


def set_anlt(port: "ports.GenericL23Port", anlt_enabled: bool) -> List["Token"]:
    tokens = []
    if not anlt_enabled:
        pass

    if isinstance(port, PCSPMAPorts):  # port not support
        if bool(port.info.capabilities.can_auto_neg_base_r):
            tokens.append(
                port.pcs_pma.auto_neg.settings.set(
                    AutoNegMode.ANEG_ON,
                    AutoNegTecAbility.DEFAULT_TECH_MODE,
                    AutoNegFecOption.NO_FEC,
                    AutoNegFecOption.NO_FEC,
                    PauseMode.NO_PAUSE,
                )
            )
        else:
            logger.warning(
                str(BXMPWarning(f"can_auto_neg_base_r", False, port, "anlt"))
            )
        if bool(port.info.capabilities.can_set_link_train):
            tokens.append(
                port.pcs_pma.link_training.settings.set(
                    LinkTrainMode.FORCE_ENABLE,
                    PAM4FrameSize.N16K_FRAME,
                    LinkTrainingInitCondition.NO_INIT,
                    NRZPreset.NRZ_NO_PRESET,
                    TimeoutMode.DEFAULT_TIMEOUT,
                )
            )
        else:
            logger.warning(str(BXMPWarning(f"can_set_link_train", False, port, "anlt")))
    return tokens


def set_mdi_mdix_mode(
    port: "ports.GenericL23Port", mdi_mdix_mode: "MdiMdixMode"
) -> List["Token"]:
    # mdi mdix mode
    tokens = []
    logger.debug(
        f"[Set mdi mdix mode]: can {port.info.capabilities.can_mdi_mdix}, mode: {mdi_mdix_mode} {YesNo.NO}"
    )
    if port.info.capabilities.can_mdi_mdix == YesNo.NO:
        para = "mdi_mdix_mode"
        logger.warning(str(BXMPWarning(para, False, port, "mdi mdix")))
    elif isinstance(port, MdixPorts):
        logger.debug("ready to set mdix mode")
        tokens.append(port.mdix_mode.set(mdi_mdix_mode.to_xmp()))
    return tokens


def set_broadr_reach_mode(
    port: ports.GenericL23Port, broadr_reach_mode: "BRRModeStr"
) -> List["Token"]:
    tokens = []
    if port.is_brr_mode_supported == YesNo.NO:
        para = "broadr_reach_mode"
        logger.warning(str(BXMPWarning(para, False, port, "broadr_reach_mode")))
    elif isinstance(port, BrrPorts):
        tokens.append(port.brr_mode.set(broadr_reach_mode.to_xmp()))
    return tokens


def set_max_header(
    port: "ports.GenericL23Port", header_segments: List["HeaderSegment"]
) -> List["Token"]:
    # calculate max header length
    header_segments_val = sum(len(i.segment_value) for i in header_segments)

    for p in STANDARD_SEGMENT_VALUE:
        if header_segments_val <= p:
            header_segments_val = p
            break
    return [port.max_header_length.set(header_segments_val)]


def set_stagger_step(
    port: "ports.GenericL23Port", port_stagger_steps: int
) -> List["Token"]:
    # Port stagger step
    if not port_stagger_steps:
        return []
    return [port.tx_config.delay.set(port_stagger_steps)]  # P_TXDELAY


def set_tpld_mode(port: "ports.GenericL23Port", use_micro_tpld: bool) -> List["Token"]:
    return [port.tpld_mode.set(TPLDMode(int(use_micro_tpld)))]


async def setup_latency_mode(
    control_ports: List["Structure"], latency_mode: "LatencyModeStr"
) -> None:
    tokens = []
    for port_struct in control_ports:
        tokens.append(port_struct.port.latency_config.mode.set(latency_mode.to_xmp()))
    await apply(*tokens)


def set_packet_size_if_mix(
    port: "ports.GenericL23Port", frame_sizes: "FrameSizeConfiguration"
) -> List["Token"]:
    tokens = []
    if not frame_sizes.packet_size_type.is_mix:
        return []
    tokens.append(port.mix.weights.set(*frame_sizes.mixed_sizes_weights))
    if frame_sizes.mixed_length_config:
        dic = frame_sizes.mixed_length_config.dict()
        for k, v in dic.items():
            position = int(k.split('_')[-1])
            tokens.append(port.mix.lengths[position].set(v))
    return tokens


async def set_reduction_sweep(
    control_ports: List["Structure"], test_conf: TestConfiguration
) -> None:
    # Speed Reduct. Sweep  overrules Speed Reduction
    tokens = []
    sweep = 0
    if (
        not test_conf.enable_speed_reduction_sweep
        or test_conf.topology.is_pair_topology
    ):
        return
    for port_struct in control_ports:
        tokens.append(port_struct.port.speed.reduction.set(ppm=sweep))
        sweep += 10

    await apply(*tokens)


def apply_macaddress_for_modifier_mode(
    port_struct: "Structure", is_stream_based: bool
) -> List["Token"]:
    if is_stream_based:
        return []

    return [
        port_struct.port.net_config.mac_address.set(
            f"0x{port_struct.properties.mac_address.to_hexstring()}"
        )
    ]


def set_speed_mode(
    port: "ports.GenericL23Port", port_speed_mode
) -> List["Token"]:  # SetPortSpeedSelection

    mode = port_speed_mode.to_xmp()
    if mode not in port.local_states.port_possible_speed_modes:
        logger.warning(f"port doesn't support speed mode selection ({port_speed_mode})")
        return []
    return [port.speed.mode.selection.set(mode)]


async def base_setting(
    test_conf: "TestConfiguration", port_struct: "Structure"
) -> None:
    tokens = []
    port = port_struct.port
    port_conf = port_struct.port_conf
    tokens += apply_macaddress_for_modifier_mode(
        port_struct, test_conf.flow_creation_type.is_stream_based
    )
    tokens += set_speed_mode(port, port_conf.port_speed_mode)
    tokens += set_latency_offset(port, port_conf.latency_offset_ms)
    tokens += set_ip_address(port, port_conf)
    tokens += set_arpping(port)
    tokens += set_interframe_gap(port, port_conf.inter_frame_gap)
    tokens += set_speed_reduction(port, port_conf.speed_reduction_ppm)
    tokens += set_pause_mode(port, port_conf.pause_mode_enabled)
    tokens += set_fec_mode(port, port_conf.fec_mode)
    tokens += set_auto_negotiation(port, port_conf.auto_neg_enabled)
    tokens += set_anlt(port, port_conf.anlt_enabled)
    tokens += set_mdi_mdix_mode(port, port_conf.mdi_mdix_mode)
    tokens += set_broadr_reach_mode(port, port_conf.broadr_reach_mode)
    tokens += set_max_header(port, port_conf.profile.header_segments)
    tokens += set_stagger_step(port, test_conf.port_stagger_steps)
    tokens += set_tpld_mode(port, test_conf.use_micro_tpld_on_demand)
    tokens += set_packet_size_if_mix(port_struct.port, test_conf.frame_sizes)
    await apply(*tokens)
