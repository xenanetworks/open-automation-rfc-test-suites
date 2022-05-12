from decimal import Decimal
from typing import Any, List

from pydantic import NonNegativeInt

from pluginlib.plugin2544.utils.constants import MIXED_DEFAULT_WEIGHTS


class BXMPWarning:
    def __init__(self, para: str, value: Any, port: Any, feature: str) -> None:
        self.str = f"<{para}> can only be set to {value} since port {port} does not support '{feature}' feature!"

    def __repr__(self) -> str:
        return self.str

    def __str__(self) -> str:
        return self.str


class NotSupportL47Tester(Exception):
    def __init__(self) -> None:
        self.msg = "Not Support L47Tester"
        super().__init__(self.msg)


class IPAddressMissing(Exception):
    def __init__(self) -> None:
        self.msg = "You must assign an IP address to the port!"
        super().__init__(self.msg)


class PortConfigNotEnough(Exception):
    def __init__(self, require_ports: int) -> None:
        self.msg = f"The configuration must have at least {require_ports} testport{'s'  if require_ports > 1 else ''}!"
        super().__init__(self.msg)


class PortGroupError(Exception):
    def __init__(self, group: str) -> None:
        self.msg = f"At least one port must be assigned to the {group} port group!"
        super().__init__(self.msg)


class TestTypesError(Exception):
    def __init__(self) -> None:
        self.msg = "You have not enabled any test types."
        super().__init__(self.msg)


class ModifierBasedNotSupportPerPortResult(Exception):
    def __init__(self) -> None:
        self.msg = "Cannot use per-port result for modifier-based flows."
        super().__init__(self.msg)


class ModifierBasedNotSupportL3(Exception):
    def __init__(self) -> None:
        self.msg = "Cannot use modifier-based flow creation for layer-3 tests!"
        super().__init__(self.msg)


class ModifierBasedNotSupportMultiStream(Exception):
    def __init__(self) -> None:
        self.msg = "Modifier-based mode doesn't support multi-stream!"
        super().__init__(self.msg)

class ModifierBasedNotSupportDefineModifier(Exception):
    def __init__(self) -> None:
        self.msg = "Not possible to define modifiers when using modifier-based flows"
        super().__init__(self.msg)
class PortPeerNeeded(Exception):
    def __init__(self) -> None:
        self.msg = "You must assign a peer to the port!"
        super().__init__(self.msg)


class PortPeerInconsistent(Exception):
    def __init__(self) -> None:
        self.msg = "Inconsistent port peer definition!"
        super().__init__(self.msg)


class PortGroupNeeded(Exception):
    def __init__(self) -> None:
        self.msg = "You must assign the port to a port group!"
        super().__init__(self.msg)


class MacAddressNotValid(Exception):
    def __init__(self, mac_addr: str) -> None:
        self.msg = f"{mac_addr} is not a valid mac address!"
        super().__init__(self.msg)


class MixWeightsNotEnough(Exception):
    def __init__(self) -> None:
        self.msg = f"Not enough mixed weights; there should be {len(MIXED_DEFAULT_WEIGHTS)} number of mixed weights!"
        super().__init__(self.msg)


class MixWeightsSumError(Exception):
    def __init__(self, current_sum: int) -> None:
        self.msg = (
            f"The sum of packet weights must be 100% (is currently {current_sum}%.)"
        )
        super().__init__(self.msg)


class FrameSizeTypeError(Exception):
    def __init__(self, packet_size_type: str) -> None:
        self.msg = f"Frame size type {packet_size_type} not implemented!"
        super().__init__(self.msg)


class RangeRestriction(Exception):
    def __init__(self) -> None:
        self.msg = "Start rate cannot be larger than the End rate."
        super().__init__(self.msg)


class StepValueRestriction(Exception):
    def __init__(self) -> None:
        self.msg = "Step value percent must be larger than 0!"
        super().__init__(self.msg)


class RateRestriction(Exception):
    def __init__(self, cur_rate: float, max_rate: float) -> None:
        self.msg = f"{cur_rate} cannot be larger than the maximum rate({max_rate})"
        super().__init__(self.msg)


class PacketLengthExceed(Exception):
    def __init__(self, cur: int, max: int) -> None:
        self.msg = f"packet length ({cur}) is larger than port capability ({max})"
        super().__init__(self.msg)


class TPLDIDExceed(Exception):
    def __init__(self, cur: int, max: int) -> None:
        self.msg = f"current tpldid ({cur}) is larger than port capability ({max})"
        super().__init__(self.msg)


class OffsetNotExsits(Exception):
    def __init__(self) -> None:
        self.msg = "Offsets table calculate error"
        super().__init__(self.msg)


class ProtocolNotSupport(Exception):
    def __init__(self, proto: str) -> None:
        self.msg = f"Port don't support {proto}"
        super().__init__(self.msg)


class InterFrameGapError(Exception):
    def __init__(self, curr: int, min: int, max: int) -> None:
        self.msg = f"Custom interframe gap({curr}) should between {min} and {max}"
        super().__init__(self.msg)


class PortRateError(Exception):
    def __init__(self, curr: Decimal, max: int) -> None:
        self.msg = f"Custom port rate({curr}) larger than physical port rate({max})!"
        super().__init__(self.msg)


class SpeedReductionError(Exception):
    def __init__(self, curr: NonNegativeInt, max: int) -> None:
        self.msg = f"Custom speed reduction larger({curr}) than port max speed reduction({max})"
        super().__init__(self.msg)


class ProtocolSegmentExceed(Exception):
    def __init__(self, curr: int, max: int) -> None:
        self.msg = f"Custom header segments length({curr}) should less than {max}"
        super().__init__(self.msg)


class PacketHeaderExceed(Exception):
    def __init__(self, curr: int, max: int) -> None:
        self.msg = f"Segment packet header length ({curr}) is larger than port capability ({max})"
        super().__init__(self.msg)


class ModifierRepeatCountExceed(Exception):
    def __init__(self, curr: int, max: int) -> None:
        self.msg = f"Custom modifier repeat count ({curr}) is larger than port capability ({max})"
        super().__init__(self.msg)


class FECModeRequired(Exception):
    def __init__(self) -> None:
        self.msg = f"port is mandatory to set FECMODE"
        super().__init__(self.msg)


class FECModeNotSupport(Exception):
    def __init__(self, support_mode: List) -> None:
        self.msg = f"port support {support_mode} FECMode"
        super().__init__(self.msg)


class FieldValueRangeExceed(Exception):
    def __init__(self, field_name: str, max: int) -> None:
        self.msg = f"Field Value Range {field_name} boundary can not larger than {max}"
        super().__init__(self.msg)

class PortStaggeringNotSupport(Exception):
    def __init__(self) -> None:
        self.msg = "Tester does not support port staggering"
        super().__init__(self.msg)