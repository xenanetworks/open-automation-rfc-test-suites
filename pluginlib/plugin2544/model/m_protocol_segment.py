from random import randint
from typing import List
from pydantic import (
    BaseModel,
    Field,
    validator,
    NonNegativeInt,
)
from xoa_driver import enums
from ..utils import constants as const, exceptions
from ..utils.protocol_segments import (
    get_field_definition,
    get_segment_definition,
)


class HwModifier(BaseModel):
    field_name: str
    mask: str
    action: const.ModifierActionOption = const.ModifierActionOption.INC
    start_value: int = Field(ge=0, le=65535)
    stop_value: int = Field(ge=0, le=65535)
    step_value: int = Field(1, ge=0, le=15)
    repeat_count: NonNegativeInt = 1
    offset: int

    # Computed properties
    _byte_offset: int = 0  # byte offset from current segment start
    _position: NonNegativeInt = 0  # byte position from all segment start

    class Config:
        underscore_attrs_are_private = True

    @validator("step_value", pre=True, always=True)
    def validate_step(cls, step_value:int, values) -> int:
        if values['start_value'] > values['stop_value'] or (values['stop_value'] - values['start_value']) % step_value != 0:
            raise exceptions.ModifierRangeError(values['start_value'], values['stop_value'], step_value)
        return step_value


    @validator("mask", pre=True, always=True)
    def set_mask(cls, v) -> str:
        v = v[2:6] if v.startswith("0x") else v
        return f"0x{v}0000"

    @property
    def position(self) -> NonNegativeInt:
        return self._position

    def set_position(self, value: NonNegativeInt) -> None:
        self._position = value

    @property
    def byte_offset(self) -> NonNegativeInt:
        return self._byte_offset

    def set_byte_offset(self, value: NonNegativeInt) -> None:
        self._byte_offset = value


class FieldValueRange(BaseModel):
    field_name: str
    start_value: NonNegativeInt
    stop_value: NonNegativeInt
    step_value: NonNegativeInt
    action: const.ModifierActionOption
    reset_for_each_port: bool

    # Computed Properties
    _bit_length: NonNegativeInt = 0
    _bit_offset: int = 0  # bit offset from current_segment start
    _position: NonNegativeInt = 0  # bit position from all segment start
    _current_count: NonNegativeInt = 0

    class Config:
        underscore_attrs_are_private = True

    @property
    def current_count(self):
        return self._current_count

    def reset(self) -> None:
        self._current_count = 0

    @property
    def position(self) -> NonNegativeInt:
        return self._position

    def set_position(self, value: NonNegativeInt) -> None:
        self._position = value

    @property
    def bit_length(self) -> NonNegativeInt:
        return self._bit_length

    def set_bit_length(self, value: NonNegativeInt) -> None:
        self._bit_length = value

    @property
    def bit_offset(self) -> NonNegativeInt:
        return self._bit_offset

    def set_bit_offset(self, value: NonNegativeInt) -> None:
        self._bit_offset = value

    def get_current_value(self) -> int:
        if self.action == const.ModifierActionOption.INC:
            current_value = self.start_value + self.current_count * self.step_value
            if current_value > self.stop_value:
                current_value = self.start_value
                self._current_count = 0
        elif self.action == const.ModifierActionOption.DEC:
            current_value = self.start_value - self.current_count * self.step_value
            if current_value < self.stop_value:
                current_value = self.start_value
                self._current_count = 0
        else:
            boundary = [self.start_value, self.stop_value]
            current_value = randint(min(boundary), max(boundary))
        self._current_count += 1
        return current_value


class HeaderSegment(BaseModel):
    segment_type: const.SegmentType
    segment_value: str
    hw_modifiers: List[HwModifier]
    field_value_ranges: List[FieldValueRange]
    segment_byte_offset: int = 0  # byte offset since

    @validator("hw_modifiers")
    def set_modifiers(cls, hw_modifiers: List[HwModifier], values) -> List[HwModifier]:
        if hw_modifiers:
            segment_type = values["segment_type"]
            if not segment_type.is_raw:
                segment_def = get_segment_definition(segment_type)
                for modifier in hw_modifiers:
                    field_def = get_field_definition(segment_def, modifier.field_name)
                    modifier.set_byte_offset(field_def.byte_offset)

        return hw_modifiers

    @validator("field_value_ranges")
    def set_field_value_ranges(
        cls, field_value_ranges: List[FieldValueRange], values
    ) -> List[FieldValueRange]:
        if field_value_ranges:
            segment_type = values["segment_type"]
            if not segment_type.is_raw:
                segment_def = get_segment_definition(segment_type)
                for fvr in field_value_ranges:
                    field_def = get_field_definition(segment_def, fvr.field_name)
                    fvr.set_bit_length(field_def.bit_length)
                    fvr.set_bit_offset(field_def.bit_offset)
                    max_v = max(fvr.start_value, fvr.stop_value)
                    can_max = pow(2, fvr.bit_length)
                    if max_v >= can_max:
                        raise exceptions.FieldValueRangeExceed(fvr.field_name, can_max)

        return field_value_ranges


class ProtocolSegmentProfileConfig(BaseModel):
    description: str = ""
    header_segments: List[HeaderSegment] = []

    @validator("header_segments", always=True)
    def set_byte_offset(cls, v: List[HeaderSegment]) -> List[HeaderSegment]:
        if not v:
            return []

        current_byte_offset = 0
        for header_segment in v:
            header_segment.segment_byte_offset = current_byte_offset
            if header_segment.field_value_ranges:
                for fvr in header_segment.field_value_ranges:
                    fvr.set_position(current_byte_offset * 8 + fvr.bit_offset)
            if header_segment.hw_modifiers:
                for modifier in header_segment.hw_modifiers:
                    modifier.set_position(current_byte_offset + modifier.byte_offset)
                    if modifier.field_name in ("Src IP Addr", "Dest IP Addr"):
                        modifier.set_position(modifier.offset)
            current_byte_offset += len(header_segment.segment_value) // 2
        return v

    @property
    def modifier_count(self) -> int:
        return sum(
            [
                len(header_segment.hw_modifiers)
                for header_segment in self.header_segments
            ]
        )

    @property
    def packet_header_length(self) -> NonNegativeInt:
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
    def protocol_version(self) -> const.PortProtocolVersion:
        v = const.PortProtocolVersion.ETHERNET
        for i in self.header_segments:
            if i.segment_type == const.SegmentType.IPV6:
                v = const.PortProtocolVersion.IPV6
                break
            elif i.segment_type == const.SegmentType.IP:
                v = const.PortProtocolVersion.IPV4
                break
        return v

    @property
    def segment_id_list(self) -> List[enums.ProtocolOption]:
        return [h.segment_type.to_xmp() for h in self.header_segments]
