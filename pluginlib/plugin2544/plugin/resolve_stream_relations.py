from typing import TYPE_CHECKING, List
from .setup_standard_streams import setup_standard_streams
from .setup_multi_streams import setup_multi_source_streams, setup_offset_table
from .stream_base_settings import (
    setup_modifier,
    stream_base_setting,
    get_packet_header_inner,
)
from .setup_field_value_ranges import reset_field_value_range

if TYPE_CHECKING:
    from .structure import Structure, StreamInfo
    from .common import TPLDControl
    from ..model import TestConfiguration


def setup_packet_header(
    stream_lists: List["StreamInfo"],
) -> None:
    current_struct = None
    for stream_info in stream_lists:
        port_struct = stream_info.port_struct
        if current_struct != port_struct:
            reset_field_value_range(port_struct.port_conf.profile.header_segments)
            current_struct = port_struct
        packet_header = get_packet_header_inner(
            stream_info.addr_coll,
            port_struct.port_conf.profile.header_segments,
            bool(port_struct.port.info.capabilities.can_tcp_checksum),
            stream_info.arp_mac,
        )
        stream_info.change_packet_header(packet_header)


def configure_source_streams(
    control_ports: List["Structure"],
    tpld_controller: "TPLDControl",
    test_conf: "TestConfiguration",
) -> List["StreamInfo"]:
    if test_conf.multi_stream_config.enable_multi_stream:
        offset_table = setup_offset_table(control_ports, test_conf.multi_stream_config)
        stream_lists = setup_multi_source_streams(
            control_ports, tpld_controller, test_conf, offset_table
        )
    else:
        stream_lists = setup_standard_streams(control_ports, tpld_controller, test_conf)
    return stream_lists


async def create_source_stream(
    stream_lists: List["StreamInfo"],
    test_conf: "TestConfiguration",
) -> None:
    for stream_info in stream_lists:
        port_struct = stream_info.port_struct
        port = port_struct.port
        segment_id_list = port_struct.port_conf.profile.header_segment_id_list
        stream = await port.streams.create()
        await stream_base_setting(stream, stream_info, test_conf, segment_id_list)
        await setup_modifier(stream, stream_info.modifiers)
