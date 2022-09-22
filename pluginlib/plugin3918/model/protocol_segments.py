import json
import os
from typing import Dict, List, Optional
from pydantic import validator, BaseModel, NonNegativeInt
from pydantic import BaseModel, Field, validator
from xoa_driver.enums import ProtocolOption as XProtocolOption
from ..utils.errors import NoIpSegment
from ..utils.constants import (
    DEFAULT_SEGMENT_PATH,
    IPVersion,
    PayloadType,
    ProtocolOption,
    RateType,
    from_legacy_protocol_option,
)


class FieldDefinition(BaseModel):
    name: str = Field(alias="Name")
    bit_length: int = Field(alias="BitLength")
    display_type: Optional[str] = Field(alias="DisplayType")
    default_value: Optional[str] = Field(alias="DefaultValue")
    value_map_name: Optional[str] = Field(alias="ValueMapName")
    is_reserved: Optional[bool] = Field(alias="IsReserved")
    bit_offset: int = 0
    byte_offset: int = 0
    bit_padding: int = 0

    @property
    def byte_length(self) -> int:
        offset = 1 if self.bit_length % 8 > 0 else 0
        byte_length = self.bit_length // 8 + offset
        return byte_length

    # @validator("byte_length")
    # def set_byte_length(cls, v):
    #     offset = 1 if v % 8 > 0 else 0
    #     byte_length = v // 8 + offset
    #     return byte_length


class SegmentDefinition(BaseModel):
    name: str = Field(alias="Name")
    description: str = Field(alias="Description")
    segment_type: ProtocolOption = Field(alias="SegmentType")
    enclosed_type_index: Optional[int] = Field(alias="EnclosedTypeIndex")
    checksum_offset: Optional[int] = Field(alias="ChecksumOffset")
    field_definitions: List[FieldDefinition] = Field(alias="ProtocolFields")

    class Config:
        arbitrary_types_allowed = True

    @validator("field_definitions")
    def set_field_properties(cls, v):  # FixupDependencies
        curr_bit_offset = 0
        # curr_byte_offset = 0
        for field_def in v:
            field_def.bit_offset = curr_bit_offset
            field_def.byte_offset = curr_bit_offset // 8
            field_def.bit_padding = (
                8 - (curr_bit_offset % 8) if curr_bit_offset % 8 else 0
            )

            curr_bit_offset += field_def.bit_length
        return v

    @property
    def default_value(self) -> bytearray:
        step = 8
        result = []
        modulus = len(self.default_value_bin) % step
        if modulus:
            default_value_bin = (step - modulus) * [0] + self.default_value_bin
        else:
            default_value_bin = self.default_value_bin
        for i in range(0, len(default_value_bin), step):
            bit_list = default_value_bin[i : i + step]
            result.append(int("".join(str(i) for i in bit_list), 2))
        return bytearray(result)

    @property
    def default_value_bin(self) -> List[int]:
        all_bits = []
        all_bits_length = 0
        for f in self.field_definitions:
            default_value = f.default_value
            all_bits_length += f.bit_length
            if default_value:
                if default_value.startswith("0x"):
                    base = 16
                elif default_value.startswith("0b"):
                    base = 2
                else:
                    base = 10
                default_list = [i for i in default_value.split(",") if i]
                each_length = f.bit_length // len(default_list)
                for i in default_list:
                    bits = bin(int(i, base)).replace("0b", "").zfill(each_length)
                    all_bits += list(int(i) for i in bits)

            else:
                bits = [0] * f.bit_length
                all_bits += bits
            if all_bits_length - len(all_bits) >= 1:
                all_bits += [0] * (all_bits_length - len(all_bits))

        return all_bits


def load_segment_map(
    path: str = DEFAULT_SEGMENT_PATH,
) -> Dict[str, "SegmentDefinition"]:
    dic = {}
    for i in os.listdir(path):
        filepath = os.path.join(DEFAULT_SEGMENT_PATH, i)
        if os.path.isfile(filepath) and filepath.endswith(".json"):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                    data["SegmentType"] = from_legacy_protocol_option(
                        data["SegmentType"]
                    )
                value = SegmentDefinition.parse_obj(data)
                key = value.segment_type.value
            except:
                continue
            dic[key] = value
    return dic


DEFAULT_SEGMENT_DIC = load_segment_map()


class HwModifier(BaseModel):
    field_name: str
    mask: str
    action: str
    start_value: int
    stop_value: int
    step_value: int = 1
    repeat_count: NonNegativeInt = 1
    offset: int

    # Computed properties
    byte_offset: int = 0  # byte offset from current segment start
    position: NonNegativeInt = 0  # byte position from all segment start

    @validator("mask", pre=True, always=True)
    def set_mask(cls, v):
        v = v[2:6] if v.startswith("0x") else v
        return f"0x{v}0000"


class FieldValueRange(BaseModel):
    field_name: str
    start_value: NonNegativeInt
    stop_value: NonNegativeInt
    step_value: NonNegativeInt
    action: str
    bit_length: NonNegativeInt
    reset_for_each_port: bool

    # Computed Properties
    bit_offset: int = 0  # bit offset from current_segment start
    position: NonNegativeInt = 0  # bit position from all segment start
    current_count: NonNegativeInt = 0

    def increase_current_count(self):
        self.current_count += 1

    def reset_current_count(self):
        self.current_count = 0


class HeaderSegment(BaseModel):
    segment_type: ProtocolOption
    segment_value: str

    @property
    def byte_length(self) -> int:
        return len(self.segment_value) // 2


class ProtocolSegmentProfileConfig(BaseModel):
    description: str = ""
    header_segments: List[HeaderSegment] = []
    payload_type: PayloadType
    payload_pattern: str
    rate_type: RateType
    rate_fraction: float
    rate_pps: float

    @property
    def packet_header_length(self) -> int:
        return (
            sum(
                [
                    len(header_segment.segment_value)
                    for header_segment in self.header_segments
                ]
            )
            // 2
        )

    @property
    def header_segment_id_list(self) -> List[XProtocolOption]:
        return [h.segment_type.xoa for h in self.header_segments]

    @property
    def ip_version(self) -> IPVersion:
        for header_segment in self.header_segments:
            if ProtocolOption.IPV4 == header_segment.segment_type:
                return IPVersion.IPV4
            elif ProtocolOption.IPV6 == header_segment.segment_type:
                return IPVersion.IPV6
        raise NoIpSegment("No IP segment found")

    @property
    def segment_offset_for_ip(self) -> int:
        offset = 0
        for header_segment in self.header_segments:
            if ProtocolOption.IPV4 == header_segment.segment_type:
                return offset
            elif ProtocolOption.IPV6 == header_segment.segment_type:
                return offset
            offset += len(header_segment.segment_value) // 2
        return -1
