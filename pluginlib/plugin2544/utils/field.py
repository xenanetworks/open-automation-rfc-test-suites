from decimal import Decimal
import re
from typing import Any, List
from .exceptions import ConfigError
from ipaddress import (
    IPv4Address as OldIPv4Address,
    IPv6Address as OldIPv6Address,
    IPv4Network,
    IPv6Network,
)


class HexString(str):
    def to_list(self) -> List[str]:
        return [f"0x{i}" for i in re.findall(r".{2}", self)]


class MacAddress(str):
    def __new__(cls, *args, **kwargs) -> "MacAddress":
        value = str.__new__(cls, *args, **kwargs)
        if not value:
            value = "00:00:00:00:00:00"
        validate_value = (
            value.upper()
            .replace("0x", "")
            .replace("0X", "")
            .replace(":", "")
            .replace("-", "")
        )
        if len(validate_value) != 12:
            raise ConfigError(f"{value} is not a valid mac address!")
        for i in validate_value:
            if i not in "0123456789ABCDEF":
                raise ConfigError(f"{value} is not a valid mac address!")

        return str.__new__(cls, ":".join(re.findall(".{2}", validate_value)))

    def to_hexstring(self):
        return (
            self.replace(":", "")
            .replace("-", "")
            .replace("0x", "")
            .replace("0X", "")
            .upper()
            .zfill(12)
        )

    def first_three_bytes(self):
        return (
            self.replace(":", "")
            .replace("-", "")
            .replace("0x", "")
            .replace("0X", "")
            .upper()[:6]
            .zfill(6)
        )

    def to_bytearray(self) -> bytearray:
        return bytearray(bytes.fromhex(self.to_hexstring()))

    @property
    def is_empty(self) -> bool:
        return not self or self == MacAddress("00:00:00:00:00:00")


class IPv4Address(OldIPv4Address):
    def to_hexstring(self) -> str:
        return self.packed.hex().upper()

    def last_three_bytes(self) -> str:
        return self.to_hexstring()[-6:]

    def to_bytearray(self) -> bytearray:
        return bytearray(self.packed)

    def network(self, prefix: int) -> IPv4Network:
        return IPv4Network(f"{self}/{prefix}", strict=False)

    @property
    def is_empty(self) -> bool:
        return not self or self == IPv4Address("0.0.0.0")


class IPv6Address(OldIPv6Address):
    def to_hexstring(self) -> str:
        return self.packed.hex().upper()

    def last_three_bytes(self) -> str:
        return self.to_hexstring()[-6:]

    def to_bytearray(self) -> bytearray:
        return bytearray(self.packed)

    @property
    def is_empty(self) -> bool:
        return not self or self == IPv6Address("::")

    def network(self, prefix: int) -> IPv6Network:
        return IPv6Network(f"{self}/{prefix}", strict=False)


class Prefix(int):
    def to_ipv4(self) -> IPv4Address:
        return IPv4Address(int(self * "1" + (32 - self) * "0", 2))


class NonNegativeDecimal(Decimal):
    def __init__(self, v: Any) -> None:
        Decimal.__init__(v)
        if self < 0:
            raise ValueError("Please pass in positive Value.")
