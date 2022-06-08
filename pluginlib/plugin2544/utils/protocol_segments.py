import os, re
from pydantic import BaseModel, Field, validator
from pluginlib.plugin2544.plugin.common import copy_to, is_byte_values_zero

from pluginlib.plugin2544.utils import exceptions, constants as const, field
from typing import List, Dict, Optional

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..model import FieldValueRange, HeaderSegment
    from pluginlib.plugin2544.plugin.stream_struct import AddressCollection


class FieldDefinition(BaseModel):
    name: str = Field(alias="Name")
    bit_length: int = Field(0, alias="BitLength")
    display_type: Optional[str] = Field(alias="DisplayType")
    default_value: Optional[str] = Field(alias="DefaultValue")
    value_map_name: Optional[str] = Field(alias="ValueMapName")
    is_reserved: Optional[bool] = Field(alias="IsReserved")
    # computed properties
    bit_offset: int = 0
    byte_offset: int = 0
    byte_length: int = 0
    bit_padding: int = 0

    @validator("byte_length")
    def set_byte_length(cls, v):
        offset = 1 if v % 8 > 0 else 0
        byte_length = v // 8 + offset
        return byte_length


class SegmentDefinition(BaseModel):
    name: str = Field(alias="Name")
    description: str = Field(alias="Description")
    segment_type: str = Field(alias="SegmentType")
    enclosed_type_index: Optional[int] = Field(alias="EnclosedTypeIndex")
    checksum_offset: Optional[int] = Field(alias="ChecksumOffset")
    field_definitions: List[FieldDefinition] = Field(alias="ProtocolFields")

    default_bytearray: bytearray = bytearray()

    class Config:
        arbitrary_types_allowed = True

    @validator("field_definitions")
    def set_field_properties(cls, v):  # FixupDependencies
        curr_bit_offset = 0
        # curr_byte_offset = 0
        for field_def in v:
            field_def.bit_offset = curr_bit_offset
            field_def.byte_offset = curr_bit_offset // 8
            field_def.bit_padding = curr_bit_offset % 8

            curr_bit_offset += field_def.bit_length
        return v

    @validator("default_bytearray", pre=True, always=True)
    def validate_default_bytearray(cls, v, values):
        all_bits = ""
        all_bits_length = 0
        for f in values["field_definitions"]:
            default_value = f.default_value
            all_bits_length += f.bit_length
            if default_value:
                base = 0 if default_value.startswith("0x") else 10
                default_list = [i for i in default_value.split(",") if i]
                each_length = f.bit_length // len(default_list)
                for i in default_list:
                    bits = bin(int(i, base)).replace("0b", "").zfill(each_length)
                    all_bits += bits

            else:
                bits = "0" * f.bit_length
                all_bits += bits

        return bytearray([int(i, 2) for i in re.findall(".{4}", all_bits)])


def load_segment_map(
    path: str = const.DEFAULT_SEGMENT_PATH,
) -> Dict["const.SegmentType", "SegmentDefinition"]:
    dic = {}
    for i in os.listdir(path):
        filepath = os.path.join(const.DEFAULT_SEGMENT_PATH, i)
        if os.path.isfile(filepath) and filepath.endswith(".json"):
            value = SegmentDefinition.parse_file(filepath, encoding="utf-8")
            try:
                key = const.SegmentType(value.name.lower())
            except ValueError:
                continue

            dic[key] = value
    return dic


DEFAULT_SEGMENT_DIC = load_segment_map()


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
    segment_dic: Dict["const.SegmentType", "SegmentDefinition"],
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


def get_field_bit_length(
    segment_type: "const.SegmentType", field_def: "FieldDefinition"
) -> int:
    return 8 * segment_type.raw_length if segment_type.is_raw else field_def.bit_length


def get_field_byte_length(
    segment_type: "const.SegmentType", field_def: "FieldDefinition"
) -> int:
    return segment_type.raw_length if segment_type.is_raw else field_def.byte_length


def get_segment_definition(protocol: "const.SegmentType") -> SegmentDefinition:
    if not protocol in DEFAULT_SEGMENT_DIC:
        raise exceptions.ProtocolNotSupport(protocol.value)
    else:
        return DEFAULT_SEGMENT_DIC[protocol]


def get_field_definition(
    segment_def: "SegmentDefinition", field_name: str
) -> "FieldDefinition":
    for field_def in segment_def.field_definitions:
        if field_def.name == field_name:
            return field_def
    raise Exception(
        f"GET FIELD DEFINITION ERROR: No {field_name} in {segment_def.name}.json"
    )


def reset_field_value_range(header_segments: List["HeaderSegment"]) -> None:
    for header_segment in header_segments:
        for field_value_range in header_segment.field_value_ranges:
            if field_value_range.reset_for_each_port:
                field_value_range.reset()


def setup_field_value_ranges(
    patched_value: bytearray, field_value_ranges: List["FieldValueRange"]
) -> bytearray:
    for field_value_range in field_value_ranges:
        current_value = field_value_range.get_current_value()
        bin_value = bin(current_value)[2:].zfill(field_value_range.bit_length)

        original_value = "".join([bin(byte)[2:].zfill(8) for byte in patched_value])
        final = (
            original_value[: field_value_range.bit_offset]
            + bin_value
            + original_value[
                field_value_range.bit_offset + field_value_range.bit_length :
            ]
        )
        patched_value = bytearray(
            int(final, 2).to_bytes(len(final) // 8, byteorder="big")
        )

    return patched_value


def get_segment_value(
    segment: "HeaderSegment",
    segment_index: int,
    address_collection: "AddressCollection",
) -> bytearray:
    segment_value_bytearray = bytearray(bytes.fromhex(segment.segment_value))
    patched_value = bytearray()
    if (segment.segment_type) == const.SegmentType.ETHERNET:
        # patch first Ethernet segment with the port S/D MAC addresses
        if segment_index == 0:
            patched_value = setup_ethernet_segment(
                segment_value_bytearray, address_collection
            )

    elif (segment.segment_type) == const.SegmentType.IP:
        patched_value = setup_ipv4_segment(segment_value_bytearray, address_collection)

    elif (segment.segment_type) == const.SegmentType.IPV6:
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

    if not address_collection.dmac.is_empty and is_byte_values_zero(template, 0, 6):
        copy_to(address_collection.dmac.to_bytearray(), template, 0)
    if not address_collection.smac.is_empty and is_byte_values_zero(template, 6, 6):
        copy_to(address_collection.smac.to_bytearray(), template, 6)
    return template


def setup_ipv4_segment(
    template_segment: bytearray, address_collection: "AddressCollection"
) -> bytearray:
    template = template_segment.copy()

    # Patch S/D IP adresses if the address is valid and not already set
    if is_byte_values_zero(template, 12, 4):
        copy_to(address_collection.src_ipv4_addr.to_bytearray(), template, 12)

    if is_byte_values_zero(template, 16, 4):
        copy_to(address_collection.dst_ipv4_addr.to_bytearray(), template, 16)

    return template


def setup_ipv6_segment(
    template_segment: bytearray, address_collection: "AddressCollection"
) -> bytearray:
    template = template_segment.copy()

    # Patch S/D IP adresses if the address is valid and not already set
    if is_byte_values_zero(template, 8, 16):
        copy_to(address_collection.src_ipv6_addr.to_bytearray(), template, 8)

    if is_byte_values_zero(template, 24, 16):
        copy_to(address_collection.dst_ipv6_addr.to_bytearray(), template, 24)

    return template


# def format_modifier_mask(
#     segment_type: "SegmentType",
#     field_def: "FieldDefinition",
#     mask: str,
# ) -> str:
#     mask_bytes = bytearray(bytes.fromhex(mask))
#     real_mask = bytearray([0, 0])
#     field_total_bit_length = (
#         get_field_bit_length(segment_type, field_def)
#         + field_def.bit_padding
#     )
#     for bit_index in range(0, min(MAX_MASK_BIT_LENGTH, field_total_bit_length)):
#         if bit_index < field_def.bit_padding:
#             continue
#         byte_index = 0 if bit_index < 8 else 1
#         bit = 7 - bit_index % 8
#         real_mask[byte_index] |= mask_bytes[byte_index] & (1 << bit)

#     return bytes(real_mask).hex()
