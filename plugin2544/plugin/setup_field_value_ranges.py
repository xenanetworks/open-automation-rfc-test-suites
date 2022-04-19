from random import randint
from typing import TYPE_CHECKING, List

from ..utils.constants import ModifierActionOption

if TYPE_CHECKING:
    from ..model import FieldValueRange, HeaderSegment


def reset_field_value_range(header_segments: List["HeaderSegment"]) -> None:
    for header_segment in header_segments:
        for field_value_range in header_segment.field_value_ranges:
            if field_value_range.reset_for_each_port:
                field_value_range.reset_current_count()


def get_field_value_range(field_value_range: "FieldValueRange") -> int:
    if field_value_range.action == ModifierActionOption.INC:
        current_value = (
            field_value_range.start_value
            + field_value_range.current_count * field_value_range.step_value
        )
        if current_value > field_value_range.stop_value:
            current_value = field_value_range.start_value
            field_value_range.reset_current_count()
    elif field_value_range.action == ModifierActionOption.DEC:
        current_value = (
            field_value_range.start_value
            - field_value_range.current_count * field_value_range.step_value
        )
        if current_value < field_value_range.stop_value:
            current_value = field_value_range.start_value
            field_value_range.reset_current_count()
    else:
        boundary = [field_value_range.start_value, field_value_range.stop_value]
        current_value = randint(
            min(boundary), max(boundary)
        )
    field_value_range.increase_current_count()
    return current_value


def setup_field_value_ranges(
    patched_value: bytearray, field_value_ranges: List["FieldValueRange"]
) -> bytearray:
    for field_value_range in field_value_ranges:
        current_value = get_field_value_range(field_value_range)
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
