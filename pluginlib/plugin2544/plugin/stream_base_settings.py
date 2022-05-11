from typing import List, Dict, Tuple
from ..utils.field import NonNegativeDecimal

from ..utils.protocol_segments import DEFAULT_SEGMENT_DIC, SegmentDefinition
from .structure import Structure, AddressCollection
from ..model import (
    HeaderSegment,
    TestConfiguration,
    HwModifier,
    FrameSizeConfiguration,
)
from ..utils.field import MacAddress
from ..utils.constants import (
    PacketSizeType,
    SegmentType,
)
from .setup_field_value_ranges import setup_field_value_ranges

from xoa_driver.utils import apply
from xoa_driver.misc import GenuineStream
from xoa_driver.misc import Token

from xoa_driver.enums import (
    ProtocolOption,
    LengthType,
)
from ..utils.logger import logger
from .common import copy_to, is_byte_values_zero
from .structure import StreamInfo


async def stream_base_setting(
    stream: "GenuineStream",
    stream_info: "StreamInfo",
    test_conf: "TestConfiguration",
    segment_id_list: List[ProtocolOption],
) -> None:

    tokens = [
        stream.enable.set_on(),
        stream.packet.header.protocol.set(segment_id_list),
        stream.packet.header.data.set(f"0x{bytes(stream_info.packet_header).hex()}"),
        stream.payload.content.set(
            test_conf.payload_type.to_xmp(), f"0x{test_conf.payload_pattern}"
        ),
        stream.tpld_id.set(test_payload_identifier=stream_info.tpldid),
        stream.insert_packets_checksum.set_on(),
    ]
    await apply(*tokens)


async def setup_modifier(
    stream: "GenuineStream", hw_modifiers: List[HwModifier]
) -> None:
    tokens = []
    modifiers = stream.packet.header.modifiers
    await modifiers.configure(len(hw_modifiers))
    for mid, hw_modifier in enumerate(hw_modifiers):
        logger.debug(f"[Configure Modifier]: {hw_modifiers}")
        modifier = modifiers.obtain(mid)
        tokens.append(
            modifier.specification.set(
                position=hw_modifier.position,
                mask=hw_modifier.mask,
                action=hw_modifier.action.to_xmp(),
                repetition=hw_modifier.repeat_count,
            )
        )
        tokens.append(
            modifier.range.set(
                min_val=hw_modifier.start_value,
                step=hw_modifier.step_value,
                max_val=hw_modifier.stop_value,
            )
        )
    await apply(*tokens)


def get_modifier_range_by_test_port_index(
    port_struct: "Structure", stream_index: int
) -> Tuple[int, int]:
    if stream_index == 0:
        if port_struct.properties.num_modifiersL2 == 2:
            modifier_range = (
                port_struct.properties.lowest_dest_port_index,
                port_struct.properties.test_port_index - 1,
            )
        elif port_struct.properties.dest_port_count > 0:
            modifier_range = (
                port_struct.properties.lowest_dest_port_index,
                port_struct.properties.highest_dest_port_index,
            )
        else:
            modifier_range = (
                port_struct.properties.test_port_index,
                port_struct.properties.test_port_index,
            )
    else:
        modifier_range = (
            port_struct.properties.test_port_index + 1,
            port_struct.properties.highest_dest_port_index,
        )

    return modifier_range


def get_rx_ports_by_range(
    control_ports: List["Structure"], modifier_range: Tuple[int, int]
) -> List["Structure"]:
    port_struct_map = {
        port_struct.properties.test_port_index: port_struct
        for port_struct in control_ports
    }
    rx_ports = []
    for test_port_index in range(modifier_range[0], modifier_range[1] + 1):
        rx_ports.append(port_struct_map[test_port_index])
    return rx_ports


def wrap_add_16(data: bytearray, offset_num: int) -> bytearray:
    # Needs validation
    checksum = 0
    data[offset_num + 0] = 0
    data[offset_num + 1] = 0
    for i in range(0, len(data), 2):
        w = (data[i + 0] << 8) + data[i + 1]
        checksum += w
        if checksum > 0xFFFF:
            checksum = (1 + checksum) & 0xFFFF  # add carry back in as lsb
    data[offset_num + 0] = 0xFF + 1 + (~(checksum >> 8))
    data[offset_num + 1] = 0xFF + 1 + (~(checksum & 0xFF))
    return data


def calculate_checksum(
    segment: "HeaderSegment",
    segment_dic: Dict["SegmentType", "SegmentDefinition"],
    patched_value: bytearray,
) -> bytearray:

    offset_num = (
        segment_dic[segment.segment_type].checksum_offset
        if segment.segment_type in segment_dic
        else 0
    )
    if offset_num:
        return wrap_add_16(patched_value, offset_num)
    return patched_value


def get_packet_header_inner(
    address_collection: "AddressCollection",
    header_segments: List["HeaderSegment"],
    can_tcp_checksum: bool,
    arp_mac: "MacAddress",
) -> bytearray:
    packet_header_list = bytearray()

    # Insert all configured header segments in order
    segment_index = 0
    for segment in header_segments:
        segment_type = segment.segment_type
        if segment_type == SegmentType.TCP and can_tcp_checksum:
            segment_type = SegmentType.TCPCHECK
        addr_coll = address_collection.copy()
        if not arp_mac.is_empty:
            addr_coll.change_dmac_address(arp_mac)
        patched_value = get_segment_value(segment, segment_index, addr_coll)
        real_value = calculate_checksum(segment, DEFAULT_SEGMENT_DIC, patched_value)

        packet_header_list += real_value
        segment_index += 1

    return packet_header_list


def get_segment_value(
    segment: "HeaderSegment",
    segment_index: int,
    address_collection: "AddressCollection",
) -> bytearray:
    segment_value_bytearray = bytearray(bytes.fromhex(segment.segment_value))
    patched_value = bytearray()
    if (segment.segment_type) == SegmentType.ETHERNET:
        # patch first Ethernet segment with the port S/D MAC addresses
        if segment_index == 0:
            patched_value = setup_ethernet_segment(
                segment_value_bytearray, address_collection
            )

    elif (segment.segment_type) == SegmentType.IP:
        patched_value = setup_ipv4_segment(segment_value_bytearray, address_collection)

    elif (segment.segment_type) == SegmentType.IPV6:
        patched_value = setup_ipv6_segment(segment_value_bytearray, address_collection)

    # set field value range
    patched_value = setup_field_value_ranges(patched_value, segment.field_value_ranges)

    # set to default value if not assigned
    if patched_value == bytearray():
        patched_value = segment_value_bytearray

    return patched_value


def setup_ethernet_segment(
    template_segment: bytearray, address_collection: "AddressCollection"
) -> bytearray:
    template = template_segment.copy()

    if address_collection.dmac_address != MacAddress(
        "00-00-00-00-00-00"
    ) and is_byte_values_zero(template, 0, 6):
        copy_to(address_collection.dmac_address.to_bytearray(), template, 0)
    if address_collection.smac_address != MacAddress(
        "00-00-00-00-00-00"
    ) and is_byte_values_zero(template, 6, 6):
        copy_to(address_collection.smac_address.to_bytearray(), template, 6)
    return template


def setup_ipv4_segment(
    template_segment: bytearray, address_collection: "AddressCollection"
) -> bytearray:
    template = template_segment.copy()

    # Patch S/D IP adresses if the address is valid and not already set
    if is_byte_values_zero(template, 12, 4):
        copy_to(address_collection.src_ipv4_address.to_bytearray(), template, 12)

    if is_byte_values_zero(template, 16, 4):
        copy_to(address_collection.dest_ipv4_address.to_bytearray(), template, 16)

    return template


def setup_ipv6_segment(
    template_segment: bytearray, address_collection: "AddressCollection"
) -> bytearray:
    template = template_segment.copy()

    # Patch S/D IP adresses if the address is valid and not already set
    if is_byte_values_zero(template, 8, 16):
        copy_to(address_collection.src_ipv6_address.to_bytearray(), template, 8)

    if is_byte_values_zero(template, 24, 16):
        copy_to(address_collection.dest_ipv6_address.to_bytearray(), template, 24)

    return template


async def setup_packet_size(
    control_ports: List["Structure"],
    frame_size_config: "FrameSizeConfiguration",
    current_packet_size: NonNegativeDecimal,
) -> None:
    tokens = []
    for port_struct in control_ports:
        port = port_struct.port
        for stream in port.streams:
            tokens.extend(
                update_packet_size(stream, frame_size_config, current_packet_size)
            )
    await apply(*tokens)


def update_packet_size(
    stream: "GenuineStream",
    frame_size_config: "FrameSizeConfiguration",
    current_packet_size: NonNegativeDecimal,
) -> List["Token"]:
    if frame_size_config.packet_size_type.is_fix:
        return [
            stream.packet.length.set(
                LengthType.FIXED, int(current_packet_size), int(current_packet_size)
            )  # PS_PACKETLENGTH
        ]
    else:
        if (
            frame_size_config.packet_size_type == PacketSizeType.INCREMENTING
            or frame_size_config.packet_size_type == PacketSizeType.RANDOM
            or frame_size_config.packet_size_type == PacketSizeType.BUTTERFLY
        ):
            min_size = frame_size_config.varying_packet_min_size
            max_size = frame_size_config.varying_packet_max_size
        else:
            # Packet length is useless when mixed
            min_size = max_size = int(frame_size_config.mixed_average_packet_size)

        return [
            stream.packet.length.set(
                frame_size_config.packet_size_type.to_xmp(), min_size, max_size
            )
        ]  # PS_PACKETLENGTH
