import os, re
from pydantic import BaseModel, ConfigError, Field, validator
from ..utils.constants import (
    DEFAULT_SEGMENT_PATH,
    MAX_MASK_BIT_LENGTH,
    SegmentType,
)
from typing import List, Dict, Optional


class FieldDefinition(BaseModel):
    name: str = Field(alias="Name")
    bit_length: int = Field(alias="BitLength")
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
        byte_length = v / 8 + offset
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
            field_def.byte_offset = int(curr_bit_offset / 8)
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
    path: str = DEFAULT_SEGMENT_PATH,
) -> Dict["SegmentType", "SegmentDefinition"]:
    dic = {}
    for i in os.listdir(path):
        filepath = os.path.join(DEFAULT_SEGMENT_PATH, i)
        if os.path.isfile(filepath) and filepath.endswith(".json"):
            value = SegmentDefinition.parse_file(filepath, encoding="utf-8")
            try:
                key = SegmentType(value.name.lower())
            except ValueError:
                continue

            dic[key] = value
    return dic


DEFAULT_SEGMENT_DIC = load_segment_map()


def get_field_bit_length(
    segment_type: "SegmentType", field_def: "FieldDefinition"
) -> int:
    return 8 * segment_type.raw_length if segment_type.is_raw else field_def.bit_length


def get_field_byte_length(
    segment_type: "SegmentType", field_def: "FieldDefinition"
) -> int:
    return segment_type.raw_length if segment_type.is_raw else field_def.byte_length


def get_segment_definition(protocol: "SegmentType") -> SegmentDefinition:
    if not protocol in DEFAULT_SEGMENT_DIC:
        raise ConfigError(f"Not Support {protocol}")
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
