import asyncio
from typing import TYPE_CHECKING, List
from pluginlib.plugin2544.utils.constants import FECModeStr
from pluginlib.plugin2544.utils import exceptions
from xoa_driver.enums import ProtocolOption

if TYPE_CHECKING:
    from xoa_driver.ports import GenericL23Port
    from pluginlib.plugin2544.plugin.structure import (
        Structure,
    )
    from pluginlib.plugin2544.model import (
        ProtocolSegmentProfileConfig,
        PortConfiguration,
    )


def check_port_config_profile(
    port: "GenericL23Port", profile: "ProtocolSegmentProfileConfig"
) -> None:
    cap = port.info.capabilities
    if cap.max_protocol_segments < len(profile.header_segment_id_list):
        raise exceptions.ProtocolSegmentExceed(
            len(profile.header_segment_id_list), cap.max_protocol_segments
        )
    if (
        ProtocolOption.TCPCHECK in profile.header_segment_id_list
        and cap.can_tcp_checksum
    ):
        raise exceptions.ProtocolNotSupport("TCPCHECK")
    if (
        ProtocolOption.UDPCHECK in profile.header_segment_id_list
        and cap.can_udp_checksum
    ):
        raise exceptions.ProtocolNotSupport("UDPCHECK")

    if profile.packet_header_length > cap.max_header_length:
        raise exceptions.PacketHeaderExceed(
            profile.packet_header_length, cap.max_header_length
        )

    for header_segment in profile.header_segments:
        for modifier in header_segment.hw_modifiers:
            if modifier.repeat_count > cap.max_repeat:
                raise exceptions.ModifierRepeatCountExceed(
                    modifier.repeat_count, cap.max_repeat
                )


def check_can_fec(can_fec: int, fec_mode: FECModeStr) -> None:
    bin_str = bin(can_fec)[2:].zfill(32)
    is_mandatory = int(bin_str[-32])
    cap_mode = bin_str[-3:]
    supported_mode = [] if is_mandatory else [FECModeStr.OFF]
    if fec_mode == FECModeStr.OFF:
        if is_mandatory:
            raise exceptions.FECModeRequired()
    elif cap_mode == "100" and fec_mode != FECModeStr.FC_FEC:
        supported_mode.append(FECModeStr.FC_FEC)
        raise exceptions.FECModeNotSupport(supported_mode)
    elif cap_mode in ["010", "001"] and fec_mode != FECModeStr.ON:
        supported_mode.append(FECModeStr.ON)
        raise exceptions.FECModeNotSupport(supported_mode)


async def check_custom_port_config(
    port: "GenericL23Port", port_conf: "PortConfiguration"
) -> None:
    cap = port.info.capabilities

    if port_conf.port_rate > cap.max_speed * 1_000_000:
        raise exceptions.PortRateError(port_conf.port_rate, cap.max_speed * 1_000_000)
    if port_conf.speed_reduction_ppm > cap.max_speed_reduction:
        raise exceptions.SpeedReductionError(
            port_conf.speed_reduction_ppm, cap.max_speed_reduction
        )
    if (
        cap.min_interframe_gap > port_conf.inter_frame_gap
        or port_conf.inter_frame_gap > cap.max_interframe_gap
    ):
        raise exceptions.InterFrameGapError(
            port_conf.inter_frame_gap, cap.min_interframe_gap, cap.max_interframe_gap
        )
    check_can_fec(port.info.capabilities.can_fec, port_conf.fec_mode)
    check_port_config_profile(port, port_conf.profile)


async def check_ports(control_ports: List["Structure"]) -> None:
    await asyncio.gather(
        *[
            check_custom_port_config(port_struct.port, port_struct.port_conf)
            for port_struct in control_ports
        ]
    )
