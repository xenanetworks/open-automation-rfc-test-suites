from decimal import Decimal
from typing import Any
from loguru import logger
from pydantic import NonNegativeInt
from xoa_driver import ports as xoa_ports, testers as xoa_testers
from . import constants as const


class BXMPWarning(Warning):
    def __init__(self, para: str, value: Any, port: Any, feature: str) -> None:
        self.str = f"<{para}> can only be set to {value} since port {port} does not support '{feature}' feature!"

    def __repr__(self) -> str:
        return self.str

    def __str__(self) -> str:
        return self.str


class BroadReachModeNotSupport(Warning):
    def __init__(self, port_name: str) -> None:
        self.msg = f"<broad_reach_mode> can only be set to False since port {port_name} does not support 'broad_reach_mode' feature!"
        super().__init__(self.msg)


class MdiMdixModeNotSupport(Warning):
    def __init__(self, port_name: str) -> None:
        self.msg = f"<mdi_mdix_mode> can only be set to False since port {port_name} does not support 'mdi_mdix_mode' feature!"
        super().__init__(self.msg)


class ANLTNotSupport(Warning):
    def __init__(self, port_name: str) -> None:
        self.msg = f"<ANLT> can only be set to False since port {port_name} does not support 'ANLT' feature!"
        super().__init__(self.msg)


class AutoNegotiationNotSupport(Warning):
    def __init__(self, port_name: str) -> None:
        self.msg = f"<Auto Negotiation> can only be set to False since port {port_name} does not support 'Auto Negotiation' feature!"
        super().__init__(self.msg)


class FecModeNotSupport(Warning):
    def __init__(self, port_name: str) -> None:
        self.msg = f"<FEC Mode> can only be set to False since port {port_name} does not support 'FEC Mode' feature!"
        super().__init__(self.msg)


class PortSpeedWarning(Warning):
    def __init__(self, port_speed_mode) -> None:
        self.msg = f"port doesn't support speed mode selection ({port_speed_mode})"
        super().__init__(self.msg)


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


class ModifierExceed(Exception):
    def __init__(self, cur: int, max: int) -> None:
        self.msg = f"Port can only have {max} modifiers per stream (has {cur})"
        super().__init__(self.msg)


class StreamExceed(Exception):
    def __init__(self, cur: int, max: int) -> None:
        self.msg = f"Port only support {max} streams (needs {cur})"
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
        self.msg = f"Not enough mixed weights; there should be {len(const.MIXED_DEFAULT_WEIGHTS)} number of mixed weights!"
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


class FECModeTypeNotSupport(Exception):
    def __init__(self, support_mode: const.FECModeStr) -> None:
        self.msg = f"port not support {support_mode} FECMode"
        super().__init__(self.msg)


class FieldValueRangeExceed(Exception):
    def __init__(self, field_name: str, max: int) -> None:
        self.msg = f"Field Value Range {field_name} boundary can not larger than {max}"
        super().__init__(self.msg)


class PortStaggeringNotSupport(Exception):
    def __init__(self) -> None:
        self.msg = "Tester does not support port staggering"
        super().__init__(self.msg)


class MinPacketLengthExceed(Exception):
    def __init__(self, type: str, cur: int, min: int) -> None:
        self.msg = f"{type} {cur} too small for port, must at least be {min} bytes"
        super().__init__(self.msg)


class MaxPacketLengthExceed(Exception):
    def __init__(self, type: str, cur: int, max: int) -> None:
        self.msg = f"{type} {cur} too large for port, can at most be {max} bytes"
        super().__init__(self.msg)


class MicroTPLDNotSupport(Exception):
    def __init__(self) -> None:
        self.msg = "Port doesn't support micro tpld"
        super().__init__(self.msg)


class PacketSizeTooSmall(Exception):
    def __init__(self, cur: int, need: int) -> None:
        self.msg = (
            f"Packet size {cur} too small for protocol segment, need {need} bytes!"
        )
        super().__init__(self.msg)


class PayloadPatternExceed(Exception):
    def __init__(self, cur: int, max: int) -> None:
        self.msg = f"Custom payload pattern length({cur}) should smaller than {max}"
        super().__init__(self.msg)


class WrongModuleTypeError(Exception):
    def __init__(self, module) -> None:
        self.module_type = type(module)
        self.msg = f"Provided module of: {self.module_type} can't be used."
        super().__init__(self.msg)


class WrongTesterTypeError(Exception):
    def __init__(self, tester) -> None:
        self.tester_type = type(tester)
        self.msg = f"Provided tester of: {self.tester_type} can't be used."
        super().__init__(self.msg)


class LossofPortOwnership(Exception):
    def __init__(self, port: xoa_ports.GenericL23Port) -> None:
        self.msg = f"Test is stopped due to the loss of ownership of port <module_id: {port.kind.module_id}-port_id: {port.kind.port_id}>."
        super().__init__(self.msg)


class LossofTester(Exception):
    def __init__(self, tester: xoa_testers.L23Tester, chassis_id: str) -> None:
        self.msg = f"Test is stopped due to the loss of tester <{chassis_id}>."
        super().__init__(self.msg)


class LossofPortSignal(Exception):
    def __init__(self, port: xoa_ports.GenericL23Port) -> None:
        self.msg = f"Test is stopped due to the loss of signal of port <module_id: {port.kind.module_id}-port_id: {port.kind.port_id}>."
        logger.error(self.msg)
        super().__init__(self.msg)


class FrameDurationRequire(Exception):
    def __init__(self, test_type: str) -> None:
        self.msg = f"{test_type} Test requires Frames Duration Type"
        logger.error(self.msg)
        super().__init__(self.msg)
    
class TimeDurationRequire(Exception):
    def __init__(self, test_type: str) -> None:
        self.msg = f"{test_type} Test requires Time Duration Type"
        logger.error(self.msg)
        super().__init__(self.msg)


class PacketLimitOverflow(Exception):
    def __init__(self, packet_count: int) -> None:
        self.msg = f"{packet_count} can not bigger than 2,147,483,647"
        logger.error(self.msg)
        super().__init__(self.msg)