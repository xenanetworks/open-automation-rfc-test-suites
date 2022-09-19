from enum import Enum
from typing import Any, Union, SupportsIndex, TypeVar

SelfEnumChanger = TypeVar("SelfEnumChanger", bound="EnumChanger")


class AnyMember:
    def __init__(self, *args) -> None:
        self.data = args

    def __eq__(self, o: Any) -> bool:
        if isinstance(o, (tuple)):
            return self.data.__eq__(o)
        elif isinstance(o, AnyMember):
            return self.data.__eq__(o.data)
        for i in self.data:
            if i == o:
                return True
        return False

    def __len__(self) -> int:
        return self.data.__len__()

    def __str__(self) -> str:
        return self.data.__str__()

    def __getitem__(self, k: Union[SupportsIndex, slice]) -> Any:
        return self.data[k]

    @property
    def legacy(self) -> Any:
        return self.data[0]

    @property
    def core(self) -> Any:
        return self.data[1]

    @property
    def xoa(self) -> Any:
        return self.data[2]


class EnumChanger(Enum):
    def __new__(cls, values):
        obj = object.__new__(cls)
        # first value is canonical value
        if isinstance(values, AnyMember):
            obj._value_ = values
            for other_value in values:
                cls._value2member_map_[other_value] = obj
        return obj
