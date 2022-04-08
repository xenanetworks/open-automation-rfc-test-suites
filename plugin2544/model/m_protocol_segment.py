from typing import List
from pydantic import (
    BaseModel,
    validator,
    NonNegativeInt,
)
from xoa_driver.enums import ProtocolOption

from ..utils.constants import (
    ModifierActionOption,
    SegmentType,
    PortProtocolVersion,
)
from ..utils.protocol_segments import (
    get_field_definition,
    get_segment_definition,
)


class HwModifier(BaseModel):
    field_name: str
    mask: str
    action: ModifierActionOption = ModifierActionOption.INC
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
    action: ModifierActionOption
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
    segment_type: SegmentType
    segment_value: str
    hw_modifiers: List[HwModifier]
    field_value_ranges: List[FieldValueRange]
    segment_byte_offset: int = 0  # byte offset since

    @validator("hw_modifiers", pre=True, always=True)
    def set_modifiers(cls, hw_modifiers, values):
        if hw_modifiers:
            segment_type = values["segment_type"]
            if not segment_type.is_raw:
    
                segment_def = get_segment_definition(segment_type)
                for modifier in hw_modifiers:
                    field_def = get_field_definition(segment_def, modifier.field_name)
                    modifier.byte_offset = field_def.byte_offset

        return hw_modifiers

    @validator("field_value_ranges", pre=True, always=True)
    def set_field_value_ranges(cls, field_value_ranges, values):
        if field_value_ranges:
            segment_type = values["segment_type"]
            if not segment_type.is_raw:
                segment_def = get_segment_definition(segment_type)
                for fvr in field_value_ranges:
                    field_def = get_field_definition(segment_def, fvr.field_name)
                    fvr.bit_offset = field_def.bit_offset

        return field_value_ranges


class ProtocolSegmentProfileConfig(BaseModel):
    description: str = ""
    header_segments: List[HeaderSegment] = []

    # Computed Properties
    protocol_version: PortProtocolVersion = PortProtocolVersion.ETHERNET
    modifier_count: NonNegativeInt = 0
    packet_header_length: NonNegativeInt = 0
    header_segment_id_list: List[ProtocolOption] = []

    @validator("header_segments", always=True)
    def set_byte_offset(cls, v):
        if v:
            current_byte_offset = 0
            for header_segment in v:
                header_segment.segment_byte_offset = current_byte_offset
                if header_segment.field_value_ranges:
                    for fvr in header_segment.field_value_ranges:
                        fvr.position = current_byte_offset * 8 + fvr.bit_offset
                if header_segment.hw_modifiers:
                    for modifier in header_segment.hw_modifiers:
                        modifier.position = current_byte_offset + modifier.byte_offset
                        if modifier.field_name in ("Src IP Addr", "Dest IP Addr"):
                            modifier.position += modifier.offset
                current_byte_offset += int(len(header_segment.segment_value) / 2)
        return v

    @validator("modifier_count", pre=True, always=True)
    def set_modifier_count(cls, v, values):
        count = 0
        if "header_segments" in values:
            for header_segment in values["header_segments"]:
                if header_segment.hw_modifiers:
                    count += len(header_segment.hw_modifiers)
        return count

    @validator("protocol_version", pre=True, always=True)
    def set_protocol_version(cls, v, values):
        if "header_segments" in values:
            v = PortProtocolVersion.ETHERNET
            for i in values["header_segments"]:
                if i.segment_type == SegmentType.IPV6:
                    v = PortProtocolVersion.IPV6
                    break
                elif i.segment_type == SegmentType.IP:
                    v = PortProtocolVersion.IPV4
                    break
        return v

    @validator("packet_header_length", pre=True, always=True)
    def set_segment_length(cls, v, values):
        if "header_segments" in values:
            return (
                sum(
                    [
                        len(header_segment.segment_value)
                        for header_segment in values["header_segments"]
                    ]
                )
                // 2
            )
        return v

    @validator("header_segment_id_list", pre=True, always=True)
    def set_segment_id_list(cls, v, values):
        id_list = []
        if "header_segments" in values:
            for h in values["header_segments"]:
                id_list.append(h.segment_type.to_xmp().value)

        return id_list
