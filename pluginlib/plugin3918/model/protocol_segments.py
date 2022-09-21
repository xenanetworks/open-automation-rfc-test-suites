from copy import deepcopy
from enum import Enum
import json
import os, re
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type, Union
from typing_extensions import Self
from pydantic import validator, BaseModel, NonNegativeInt
from pydantic import BaseModel, ConfigError, Field, validator
from xoa_driver.enums import ProtocolOption as XProtocolOption
from ..utils.errors import NoIpSegment
from ..utils.constants import (
    DEFAULT_SEGMENT_PATH,
    IPVersion,
    PayloadType,
    ProtocolOption,
    RateType,
    MIN_PACKET_LENGTH,
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


class ParseMode(Enum):
    BIT = 0
    BYTE = 1


class ProtocolChange:
    def __init__(self, protocol: Union[ProtocolOption, str]) -> None:
        self.segment_def = type(self).get_segment_definition_by_protocol(
            ProtocolOption(protocol)
        )
        self.value_bin = self.segment_def.default_value_bin

    @property
    def header(self) -> "HeaderSegment":
        return HeaderSegment(
            segment_type=self.segment_def.segment_type, segment_value=self.hexstring
        )

    @classmethod
    def read_segment(cls, segment: "HeaderSegment") -> "ProtocolChange":
        instance = ProtocolChange(segment.segment_type)
        instance.value_bin = [
            int(p)
            for i in bytes.fromhex(segment.segment_value)
            for p in bin(i).replace("0b", "").zfill(8)
        ]
        return instance

    @classmethod
    def calculate_checksum(
        cls,
        header_segments: List["HeaderSegment"],
        index: int,
        value: str,
    ) -> bytearray:
        segment = header_segments[index]
        if segment.segment_type != ProtocolOption.ICMPV6:
            patched_value = bytearray.fromhex(value)
            offset_num = (
                ProtocolChange.get_segment_definition_by_protocol(
                    segment.segment_type
                ).checksum_offset
                or -1
                if segment.segment_type.value in DEFAULT_SEGMENT_DIC
                else -1
            )
            if offset_num != -1:
                result = cls.wrap_add_16(patched_value, offset_num)
                segment.segment_value = result.hex()
                return result
            return patched_value
        else:
            ip_segment = ProtocolChange.read_segment(header_segments[index - 1])
            source_ip_address = ip_segment.find_value_as_bytearray("Src IPv6 Addr")
            dest_ip_address = ip_segment.find_value_as_bytearray("Dest IPv6 Addr")
            icmpv6_checksum = cls.icmp_v6_checksum(
                source_ip_address,
                dest_ip_address,
                list(bytes.fromhex(segment.segment_value)),
            )
            now_value = (
                segment.segment_value[:4] + icmpv6_checksum + segment.segment_value[8:]
            )
            segment.segment_value = now_value
            return bytearray.fromhex(now_value)

    @classmethod
    def icmp_v6_checksum(
        cls,
        source_ip_bytearray: bytearray,
        dest_ip_bytearray: bytearray,
        byte_list: List[int],
    ) -> str:
        checksum = 0
        for i in range(0, len(source_ip_bytearray), 2):
            num = (source_ip_bytearray[i] << 8) + source_ip_bytearray[i + 1]
            checksum += num
        for i in range(0, len(dest_ip_bytearray), 2):
            num = (dest_ip_bytearray[i] << 8) + dest_ip_bytearray[i + 1]
            checksum += num
        checksum += len(byte_list) >> 16
        checksum += len(byte_list)
        checksum += 0
        checksum += 0x003A
        for i in range(0, len(byte_list), 2):
            num = (byte_list[i] << 8) + byte_list[i + 1]
            checksum += num
        checksum += checksum >> 16
        c = ~checksum
        high = (c & 0xFF00) >> 8
        low = c & 0xFF
        return bytearray([high, low]).hex()

    @classmethod
    def wrap_add_16(cls, data: bytearray, offset_num: int) -> bytearray:
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

    @classmethod
    def cal_packet_header(cls, header_segments: List["HeaderSegment"]) -> bytearray:
        packet_header_list = bytearray()
        for index, segment in enumerate(header_segments):
            patched_value = segment.segment_value
            real_value = cls.calculate_checksum(header_segments, index, patched_value)
            packet_header_list += real_value

        # minimum packet length
        if MIN_PACKET_LENGTH > len(packet_header_list):
            for i in range(MIN_PACKET_LENGTH - len(packet_header_list)):
                packet_header_list.append(0)

        # add spece for Ethernet FCS
        return packet_header_list + bytearray([0, 0, 0, 0])

    @property
    def bin_int_list(self) -> List[int]:
        return self.value_bin

    @property
    def bin_str(self) -> str:
        return "".join(str(i) for i in self.value_bin)

    @property
    def bytes_int_list(self) -> List[int]:
        return type(self).bin_to_bytes_int_list(self.value_bin)

    @classmethod
    def bin_to_bytes_int_list(cls, bin_list: List[int]) -> List[int]:
        length = len(bin_list)
        step = 8
        modulus = length % step
        short_len = length // step
        long_len = short_len * step if not modulus else (short_len + 1) * step
        new_bin = cls.patch_bin_list(bin_list, long_len)
        result = []
        for i in range(0, length, step):
            part = new_bin[i : i + step]
            part_str = "".join(str(m) for m in part)
            result.append(int(part_str, 2))
        return result

    @property
    def bytearrays(self) -> bytearray:
        return bytearray(self.bytes_int_list)

    @property
    def byte(self) -> bytes:
        return bytes(self.bytearrays)

    @property
    def hexstring(self) -> str:
        return self.byte.hex()

    def keys(self) -> List[str]:
        return [i.name for i in self.segment_def.field_definitions]

    def find_field(self, key: str) -> Optional[FieldDefinition]:
        for field_def in self.segment_def.field_definitions:
            if field_def.name == key or field_def.value_map_name == field_def.name:
                return field_def
        return None

    def find_value_as_bytearray(self, key: str) -> bytearray:
        field = self.find_field(key)
        if field:
            bins = self.value_bin[
                field.bit_offset : field.bit_offset + field.bit_length
            ]
            return bytearray(type(self).bin_to_bytes_int_list(bins))
        return bytearray()

    def change_segments(self, **dic) -> "ProtocolChange":
        for key, v in dic.items():
            value, mode = v
            self.change_segment(key, value, mode)
        return self

    def change_segment(
        self,
        key: str,
        value: Union[str, list, bytearray, bytes, int],
        mode: Union[ParseMode, int] = ParseMode.BIT.value,
    ) -> "ProtocolChange":
        value_bin = self.value_bin
        mode_enum = ParseMode(mode)
        field_def = self.find_field(key)
        assert field_def, f'Cannot find the field named "{key}". '
        bit_offset = field_def.bit_offset
        bit_length = field_def.bit_length
        new_value = [0] * bit_length
        if isinstance(value, (str, list, bytearray, bytes)):
            if mode_enum == ParseMode.BIT:
                new_value = [int(i) for i in value]
                assert all(
                    i in range(2) for i in new_value
                ), "Not all elements are '0' or '1'!"
            elif mode_enum == ParseMode.BYTE:
                if isinstance(value, str):
                    temp = [int(i) for i in bytes.fromhex(value)]
                else:
                    temp = list(value)
                new_value = [
                    int(i) for b in temp for i in bin(b).replace("0b", "").zfill(8)
                ]

        elif isinstance(value, int):
            new_value = [int(i) for i in bin(value).replace("0b", "")]

        result = type(self).patch_bin_list(new_value, bit_length)
        assert bit_offset + len(result) <= len(value_bin), "Modified value too long. "
        value_bin[bit_offset : bit_offset + len(result)] = result
        self.value_bin = value_bin
        return self

    @classmethod
    def get_segment_definition_by_string(cls, protocol_str: str) -> SegmentDefinition:
        if not protocol_str in DEFAULT_SEGMENT_DIC:
            raise ConfigError(f"Not Support {protocol_str}")
        else:
            return deepcopy(DEFAULT_SEGMENT_DIC[protocol_str])

    @classmethod
    def get_segment_definition_by_protocol(
        cls, protocol: ProtocolOption
    ) -> SegmentDefinition:
        protocol_str = protocol.value
        return cls.get_segment_definition_by_string(protocol_str)

    @classmethod
    def get_segment_definition_by_ip_version(
        cls, protocol: IPVersion
    ) -> SegmentDefinition:
        return cls.get_segment_definition_by_string(protocol.value)

    @classmethod
    def patch_bin_list(cls, int_01_list: List[int], patch_to_length: int) -> List[int]:
        modulus = len(int_01_list) % patch_to_length
        if len(int_01_list) > patch_to_length:
            result = int_01_list[-patch_to_length:]
        elif modulus:
            result = (patch_to_length - modulus) * [0] + int_01_list
        else:
            result = int_01_list
        return result

    @classmethod
    def get_ip_field_byte_offset(cls, ip_version: IPVersion) -> int:
        for field_def in cls.get_segment_definition_by_ip_version(
            ip_version
        ).field_definitions:
            if (ip_version == IPVersion.IPV4 and field_def.name == "Dest IP Addr") or (
                ip_version == IPVersion.IPV6 and field_def.name == "Dest IPv6 Addr"
            ):
                return field_def.byte_offset
        raise Exception(f"Cannot find byte offset of '{ip_version}'")


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
                    data["SegmentType"] = from_legacy_protocol_option(data["SegmentType"])
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
