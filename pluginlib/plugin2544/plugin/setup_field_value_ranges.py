from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..model import FieldValueRange, HeaderSegment


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
