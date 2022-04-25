from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    TypeVar,
    Protocol as Interface,
)
from xoa_driver.ports import GenericL23Port
from pydantic import NonNegativeInt
from ..utils.field import NonNegativeDecimal
from .structure import Structure
from ..utils.constants import TestResultState, TestType

if TYPE_CHECKING:
    from xoa_driver.internals.core.commands.p_commands import P_TRAFFIC


class ITraffic(Interface):
    bit_count_last_sec: int
    packet_count_last_sec: int
    byte_count_since_cleared: int
    packet_count_since_cleared: int


class IDelay(Interface):
    min_val: int
    avg_val: int
    max_val: int
    avg_last_sec: int
    min_last_sec: int
    max_last_sec: int


class IExtra(Interface):
    fcs_error_count: int
    # pause_frame_count: int
    # rx_arp_request_count: int
    # rx_arp_reply_count: int
    # rx_ping_request_count: int
    # rx_ping_reply_count: int
    # gap_count: int
    # gap_duration: int


class IError(Interface):
    # dummy: int
    packet_count_since_cleared: int
    non_incre_seq_event_count: int
    swapped_seq_misorder_event_count: int
    non_incre_payload_packet_count: int


@dataclass
class BoutEntry:
    port_index: str = "all"
    rate: Decimal = Decimal("0")
    current: Decimal = Decimal("0")
    next: Decimal = Decimal("0")


IterationEntry = TypeVar("IterationEntry", bound=BoutEntry)


@dataclass
class Kind:
    port_index: str = "all"
    peer_index: str = "all"
    stream_id: int = -1
    tpld_id: int = -1


@dataclass
class Par:
    is_live: bool = True
    is_common = False
    current_packet_size: NonNegativeDecimal = NonNegativeDecimal("0")
    iteration: int = -1
    rate: Decimal = Decimal("0")
    actual_rate: Decimal = Decimal("0")
    test_result_state: TestResultState = TestResultState.PENDING

    def set_result_state(self, passed: bool) -> None:
        self.test_result_state = (
            TestResultState.PASS if passed else TestResultState.FAIL
        )


@dataclass
class AvgMinMax:
    average: Decimal = Decimal("0")
    minimum: Decimal = Decimal("0")
    maximum: Decimal = Decimal("0")
    current: Decimal = Decimal("0")


@dataclass
class DelayCounter(AvgMinMax):
    is_valid: bool = False
    is_current_valid: bool = False
    is_aggregate: bool = False
    average_last_sec: Decimal = Decimal("0")

    def check(self, mode: str, is_live: bool):
        latency_invalid = -2147483648
        jitter_invalid = -1
        if mode == "latency":
            self.current = (
                self.average_last_sec
                if self.average_last_sec > latency_invalid
                else self.average
            )
            self.is_current_valid = self.average_last_sec != latency_invalid and is_live
            self.is_valid = (
                self.minimum != latency_invalid
                and self.maximum != latency_invalid
                and self.average != latency_invalid
            )

        else:
            self.current = self.average
            self.is_current_valid = self.average_last_sec != jitter_invalid and is_live
            self.is_valid = (
                self.minimum != jitter_invalid
                and self.maximum != jitter_invalid
                and self.average != jitter_invalid
            )

    def avg_min_max(self) -> AvgMinMax:
        return AvgMinMax(
            average=self.average,
            minimum=self.minimum,
            maximum=self.maximum,
            current=self.current,
        )

    def divided_by_factor(self, factor: Decimal):
        self.average /= factor
        self.minimum /= factor
        self.maximum /= factor
        self.current /= factor


class CounterHandle:
    def __post_init__(self):
        self._tx_counters = []
        self._rx_counters = []
        self._ji_counters = []
        self._la_counters = []
        self._ex_counters = []
        self._rr_counters = []

    def add_tx(self, index: int) -> None:
        self._tx_counters.append(index)

    def add_rx(self, index: int) -> None:
        self._rx_counters.append(index)

    def add_ji(self, index: int) -> None:
        self._ji_counters.append(index)

    def add_la(self, index: int) -> None:
        self._la_counters.append(index)

    def add_ex(self, index: int) -> None:
        self._ex_counters.append(index)

    def add_rr(self, index: int) -> None:
        self._rr_counters.append(index)

    def read(self, replies: List, common_params: "TestCommonParam") -> None:
        self._read_from_tx_counters(replies, common_params)
        self._read_from_rx_counters(replies, common_params)
        self._read_from_la_counters(replies, common_params)
        self._read_from_ji_counters(replies, common_params)
        self._read_from_ex_counters(replies, common_params)
        self._read_from_rr_counters(replies, common_params)

    def _read_from_tx_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        pass

    def _read_from_rx_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        pass

    def _read_from_la_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        pass

    def _read_from_ji_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        pass

    def _read_from_ex_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        pass

    def _read_from_rr_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        pass

    def get_tx_counters(self) -> List[int]:
        return self._tx_counters

    def get_rx_counters(self) -> List[int]:
        return self._rx_counters

    def get_la_counters(self) -> List[int]:
        return self._la_counters

    def get_ji_counters(self) -> List[int]:
        return self._ji_counters

    def get_ex_counters(self) -> List[int]:
        return self._ex_counters

    def get_rr_counters(self) -> List[int]:
        return self._rr_counters


@dataclass
class BaseResult(Kind, Par, CounterHandle):
    tx_frames: Decimal = Decimal("0")
    rx_frames: Decimal = Decimal("0")
    latency: AvgMinMax = AvgMinMax()
    jitter: AvgMinMax = AvgMinMax()
    burst_frames: Decimal = Decimal("0")

    @property
    def burst_bytes(self) -> Decimal:
        return Decimal(str(self.burst_frames)) * Decimal(str(self.current_packet_size))


Result = TypeVar("Result", bound="BaseResult")


@dataclass
class StreamResult(BaseResult):
    loss_frames: Decimal = Decimal("0")

    @property
    def loss_ratio_pct(self) -> Decimal:
        return 100 * self.loss_ratio

    @property
    def loss_ratio(self) -> Decimal:
        if self.tx_frames == Decimal("0"):
            return Decimal("0")
        return self.loss_frames / self.tx_frames

    def average_from(self, obj_list: List) -> None:
        count = 0
        for other in obj_list:
            self.is_live = other.is_live
            self.is_common = other.is_common
            self.current_packet_size = other.current_packet_size
            self.rate = other.rate
            self.actual_rate = other.actual_rate
            self.test_result_state = other.test_result_state

            self.tx_frames += other.tx_frames
            self.rx_frames += other.rx_frames
            self.jitter.maximum += other.jitter.maximum
            self.jitter.minimum += other.jitter.minimum
            self.jitter.average += other.jitter.average
            self.latency.maximum += other.latency.maximum
            self.latency.minimum += other.latency.minimum
            self.latency.average += other.latency.average

            count += 1
        if count > 0:
            self.tx_frames /= count
            self.rx_frames /= count
            self.jitter.maximum /= count
            self.jitter.minimum /= count
            self.jitter.average /= count
            self.latency.maximum /= count
            self.latency.minimum /= count
            self.latency.average /= count

    @classmethod
    def average(
        cls, obj_list: List[Result]
    ) -> Dict[Tuple[str,], Result]:
        dic = {}
        for k, v in groupby(obj_list).items():
            r = StreamResult()
            r.average_from(v)
            dic[k] = r
        return dic

    def _read_from_tx_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        if not self._tx_counters:
            return
        t = self._tx_counters[0]
        self.tx_frames = Decimal(str(replies[t].packet_count_since_cleared))

    def _read_from_rx_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        if not self._rx_counters:
            return
        t = self._rx_counters[0]
        self.rx_frames += Decimal(str(replies[t].packet_count_since_cleared))

    def _read_from_la_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        if not self._la_counters:
            return
        t = self._la_counters[0]
        result = DelayCounter(
            average=replies[t].avg_val,
            minimum=replies[t].min_val,
            maximum=replies[t].max_val,
        )
        result.check("latency", self.is_live)
        result.divided_by_factor(Decimal("1000"))
        self.latency = result.avg_min_max()

    def _read_from_ji_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        if not self._ji_counters:
            return
        t = self._ji_counters[0]
        result = DelayCounter(
            average=replies[t].avg_val,
            minimum=replies[t].min_val,
            maximum=replies[t].max_val,
        )
        result.check("jitter", self.is_live)
        result.divided_by_factor(Decimal("1000"))
        self.jitter = result.avg_min_max()

    def _read_from_rr_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        if not self._rr_counters:
            return
        t = self._rr_counters[0]
        if self.is_live:
            self.loss_frames = Decimal(str(replies[t].non_incre_seq_event_count))
        else:
            self.loss_frames = self.tx_frames - self.rx_frames


class TxRxFullResult(BaseResult):
    tx_fps: Decimal = Decimal("0")
    tx_rate_l1: Decimal = Decimal("0")
    tx_rate_l2: Decimal = Decimal("0")

    rx_fps: Decimal = Decimal("0")
    rx_rate_l1: Decimal = Decimal("0")
    rx_rate_l2: Decimal = Decimal("0")
    rx_bytes: Decimal = Decimal("0")

    fcs_error: Decimal = Decimal("0")

    def average_from(self, obj_list: List) -> None:
        count = 0
        for other in obj_list:
            self.is_live = other.is_live
            self.is_common = other.is_common
            self.current_packet_size = other.current_packet_size
            self.rate = other.rate
            self.test_result_state = other.test_result_state

            self.actual_rate += other.actual_rate
            self.tx_frames += other.tx_frames
            self.tx_fps += other.tx_fps
            self.tx_rate_l1 += other.tx_rate_l1
            self.tx_rate_l2 += other.tx_rate_l2
            self.rx_frames += other.rx_frames
            self.rx_fps += other.rx_fps
            self.rx_rate_l1 += other.rx_rate_l1
            self.rx_rate_l2 += other.rx_rate_l2
            self.rx_bytes += other.rx_bytes
            self.fcs_error += other.fcs_error
            self.jitter.maximum += other.jitter.maximum
            self.jitter.minimum += other.jitter.minimum
            self.jitter.average += other.jitter.average
            self.latency.maximum += other.latency.maximum
            self.latency.minimum += other.latency.minimum
            self.latency.average += other.latency.average
            self.burst_frames += other.burst_frames

            count += 1
        if count > 0:
            self.tx_frames /= count
            self.tx_rate_l1 /= count
            self.tx_rate_l2 /= count
            self.tx_fps /= count
            self.rx_frames /= count
            self.rx_bytes /= count
            self.rx_rate_l1 /= count
            self.rx_rate_l2 /= count
            self.rx_fps /= count
            self.fcs_error /= count
            self.jitter.maximum /= count
            self.jitter.minimum /= count
            self.jitter.average /= count
            self.latency.maximum /= count
            self.latency.minimum /= count
            self.latency.average /= count
            self.burst_frames /= count
            self.actual_rate /= count


class PortResult(TxRxFullResult):
    loss_frames: Decimal = Decimal("0")
    loss_ratio: Decimal = Decimal("0")
    def add_burst_frames(self, burst_frames: Decimal) -> None:
        self.burst_frames += burst_frames

    @property
    def loss_ratio_pct(self) -> Decimal:
        return 100 * self.loss_ratio

    @classmethod
    def average(cls, obj_list: List["Result"]) -> Dict[str, List["Result"]]:
        dic = {}
        for k, v in groupby(obj_list, "port_index", "rate").items():
            r = PortResult()
            r.average_from(v)
            dic[k] = r
        return dic

    def add_ex(self, index: int) -> None:
        if not self._ex_counters:
            self._ex_counters.append(index)

    def _read_from_tx_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        portize_tx(self, replies, common_params)

    def _read_from_rx_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        portize_rx(self, replies, common_params)

    def _read_from_la_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        portize_la_or_ji(self, replies, common_params, mode="latency")

    def _read_from_ji_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        portize_la_or_ji(self, replies, common_params, mode="jitter")

    def _read_from_ex_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        portize_ex(self, replies)

    def _read_from_rr_counters(
        self, replies: List, common_params: "TestCommonParam"
    ) -> None:
        portize_rr(self, replies)


def groupby(
    obj_list: List[Result], *groupby_keys: str
) -> Dict[Tuple[str,], Any]:
    dic = {}
    for i in obj_list:
        key = []
        for k in groupby_keys:
            v = getattr(i, k, None)
            key.append(v)
        key = tuple(key)
        if key not in dic:
            dic[key] = []

        dic[key].append(i)
    return dic


class AllResult(TxRxFullResult):
    @classmethod
    def average(cls, obj_list: List["Result"]) -> Dict[str, List["Result"]]:
        dic = {}
        for k, v in groupby(obj_list, "rate").items():
            r = AllResult()
            r.average_from(v)
            dic[k] = r
        return dic

    def read_from_ports(self, *port_result: "PortResult") -> None:
        count = 0
        for other in port_result:
            self.is_live = other.is_live
            self.current_packet_size = other.current_packet_size
            self.iteration = other.iteration
            self.test_result_state = other.test_result_state
            self.rate = other.rate

            count += 1
            self.tx_frames += other.tx_frames
            self.tx_fps += other.tx_fps
            self.tx_rate_l1 += other.tx_rate_l1
            self.tx_rate_l2 += other.tx_rate_l2
            self.rx_frames += other.rx_frames
            self.rx_fps += other.rx_fps
            self.rx_rate_l1 += other.rx_rate_l1
            self.rx_rate_l2 += other.rx_rate_l2
            self.rx_bytes += other.rx_bytes
            self.fcs_error += other.fcs_error
            self.actual_rate += other.actual_rate
            self.burst_frames += other.burst_frames

            if count == 0:
                self.jitter.maximum = other.jitter.maximum
                self.jitter.minimum = other.jitter.minimum
                self.jitter.average = other.jitter.average
                self.jitter.current = other.jitter.current

                self.latency.maximum = other.latency.maximum
                self.latency.minimum = other.latency.minimum
                self.latency.average = other.latency.average
                self.latency.current = other.latency.current
            else:
                self.jitter.maximum = max(self.jitter.maximum, other.jitter.maximum)
                self.jitter.minimum = min(self.jitter.minimum, other.jitter.minimum)
                self.jitter.average += self.jitter.average
                self.jitter.current += other.jitter.current

                self.latency.maximum = max(self.latency.maximum, other.latency.maximum)
                self.latency.minimum = min(self.latency.minimum, other.latency.minimum)
                self.latency.average += other.latency.average
                self.latency.current += other.latency.current
        if count > 1:
            self.actual_rate /= count
            self.jitter.average /= count
            self.jitter.current /= count
            self.latency.average /= count
            self.latency.current /= count

    @property
    def ber(self) -> Decimal:
        if self.rx_bytes or self.rx_frames == 0 or self.loss_frames <= 0:
            return Decimal("0")
        divisor = Decimal("8.0") * Decimal(str(self.rx_bytes)) * Decimal(
            str(self.rx_frames)
        ) + Decimal(str(self.loss_frames))
        return (
            Decimal(str(self.loss_frames))
            * Decimal(str(self.rx_frames))
            / Decimal(str(divisor))
        )

    @property
    def loss_ratio_pct(self) -> Decimal:
        return 100 * self.loss_ratio

    @property
    def loss_ratio(self) -> Decimal:
        if self.tx_frames == Decimal("0"):
            return Decimal("0")
        return self.loss_frames / self.tx_frames

    @property
    def loss_frames(self) -> Decimal:
        return max(Decimal("0"), self.tx_frames - self.rx_frames)


@dataclass
class TestPortParam:
    inter_frame_gap: int
    rate: Decimal
    src_port_speed: NonNegativeDecimal


@dataclass
class TestStreamParam:
    burst_frames: Decimal


@dataclass
class TestCommonParam:
    test_result_state: TestResultState
    average_packet_size: Decimal
    current_packet_size: NonNegativeDecimal
    iteration: int
    actual_duration: Decimal
    is_live: bool
    port_params: Dict[
        Tuple[
            str,
        ],
        "TestPortParam",
    ]
    stream_params: Dict[Tuple[str, str, int, int], "TestStreamParam"]


def convert_l1_bit_rate_from_l2(
    bit_rate_l2: Decimal,
    current_packet_size: NonNegativeDecimal,
    inter_frame_gap: NonNegativeInt,
):
    return (
        Decimal(str(bit_rate_l2))
        * (current_packet_size + Decimal(str(inter_frame_gap)))
        / current_packet_size
    )


def convert_l1_bit_rate(
    frame_rate: Decimal,
    current_packet_size: NonNegativeDecimal,
    inter_frame_gap: NonNegativeInt,
):
    return (
        frame_rate
        * Decimal("8")
        * (current_packet_size + Decimal(str(inter_frame_gap)))
    )


def convert_l2_bit_rate(
    frame_rate: Decimal, current_packet_size: NonNegativeDecimal
) -> Decimal:
    return frame_rate * Decimal("8") * current_packet_size


def _cal_port_tx_bps_l1(
    counter_list: List[ITraffic],
    duration: Decimal,
    current_packet_size: NonNegativeDecimal,
    is_live: bool,
    inter_frame_gap: NonNegativeInt,
) -> Decimal:
    value = Decimal("0")
    if is_live:
        for counter in counter_list:
            value += convert_l1_bit_rate_from_l2(
                Decimal(str(counter.bit_count_last_sec)),
                current_packet_size,
                inter_frame_gap,
            )
    else:
        for counter in counter_list:
            frame_rate = counter.packet_count_since_cleared / duration
            l1_bit_rate = convert_l1_bit_rate(
                frame_rate, current_packet_size, inter_frame_gap
            )
            value += l1_bit_rate
    return value


def _cal_port_rx_bps_l1(
    counter_list: List[ITraffic],
    duration: Decimal,
    current_packet_size: NonNegativeDecimal,
    is_live: bool,
    inter_frame_gap: NonNegativeInt,
):
    bit_rate_l2 = _cal_port_rx_bps_l2(
        counter_list, duration, current_packet_size, is_live
    )
    return convert_l1_bit_rate_from_l2(
        bit_rate_l2, current_packet_size, inter_frame_gap
    )


def _cal_port_tx_frames(counter_list: List[ITraffic]) -> Decimal:
    return Decimal(sum(counter.packet_count_since_cleared for counter in counter_list))


def _cal_port_rx_frames(counter_list: List[ITraffic]) -> Decimal:
    return _cal_port_tx_frames(counter_list)


def _cal_port_tx_bps_l2(
    counter_list: List[ITraffic],
    duration: Decimal,
    current_packet_size: NonNegativeDecimal,
    is_live: bool,
) -> Decimal:

    value = Decimal("0")
    if is_live:
        value = Decimal(
            str(sum(counter.bit_count_last_sec for counter in counter_list))
        )
    else:
        frame_rate = _cal_port_tx_frames(counter_list) / duration
        value = convert_l2_bit_rate(frame_rate, current_packet_size)
    return value


def _cal_port_rx_bps_l2(
    counter_list: List[ITraffic],
    duration: Decimal,
    current_packet_size: NonNegativeDecimal,
    is_live: bool,
) -> Decimal:
    return _cal_port_tx_bps_l2(counter_list, duration, current_packet_size, is_live)


def _cal_port_tx_pps(
    counter_list: List[ITraffic], duration: Decimal, is_live: bool
) -> Decimal:

    if is_live:
        value = Decimal(
            str(sum(counter.packet_count_last_sec for counter in counter_list))
        )
    else:
        value = _cal_port_tx_frames(counter_list) / duration
    return value


def _cal_port_rx_pps(
    counter_list: List[ITraffic], duration: Decimal, is_live: bool
) -> Decimal:
    return _cal_port_tx_pps(counter_list, duration, is_live)


def _cal_port_rx_bytes(counter_list: List[ITraffic]) -> Decimal:
    return Decimal(sum(counter.byte_count_since_cleared for counter in counter_list))


def _cal_port_tx_actual_rate(tx_rate_l1: Decimal, src_port_speed: NonNegativeDecimal):
    return 100 * tx_rate_l1 / src_port_speed


def portize_tx(
    result: PortResult, replies: List, common_params: TestCommonParam
) -> PortResult:
    port_index_tup = (result.port_index,)
    port_params = common_params.port_params[port_index_tup]
    counter_list = [replies[t] for t in result.get_tx_counters()]
    result.tx_frames = _cal_port_tx_frames(counter_list)
    result.tx_fps = _cal_port_tx_pps(
        counter_list,
        common_params.actual_duration,
        common_params.is_live,
    )
    result.tx_rate_l1 = _cal_port_tx_bps_l1(
        counter_list,
        common_params.actual_duration,
        common_params.current_packet_size,
        common_params.is_live,
        port_params.inter_frame_gap,
    )
    result.tx_rate_l2 = _cal_port_tx_bps_l2(
        counter_list,
        common_params.actual_duration,
        common_params.current_packet_size,
        common_params.is_live,
    )
    result.actual_rate = _cal_port_tx_actual_rate(
        result.tx_rate_l1, common_params.port_params[port_index_tup].src_port_speed
    )
    return result


def portize_rx(
    result: PortResult, replies: List[ITraffic], common_params: TestCommonParam
) -> PortResult:
    port_index_tup = (result.port_index,)
    port_params = common_params.port_params[port_index_tup]
    counter_list = [replies[t] for t in result.get_rx_counters()]

    result.rx_frames = _cal_port_rx_frames(counter_list)
    result.rx_fps = _cal_port_rx_pps(
        counter_list,
        common_params.actual_duration,
        common_params.is_live,
    )
    result.rx_rate_l1 = _cal_port_rx_bps_l1(
        counter_list,
        common_params.actual_duration,
        common_params.current_packet_size,
        common_params.is_live,
        port_params.inter_frame_gap,
    )
    result.rx_rate_l2 = _cal_port_rx_bps_l2(
        counter_list,
        common_params.actual_duration,
        common_params.current_packet_size,
        common_params.is_live,
    )
    result.rx_bytes = _cal_port_rx_bytes(counter_list)
    return result


def portize_la_or_ji(
    result: PortResult,
    replies: List[IDelay],
    common_params: "TestCommonParam",
    mode: str,
) -> PortResult:
    c_list = result.get_ji_counters() if mode == "jitter" else result.get_la_counters()
    counter_list = [replies[t] for t in c_list]
    val = DelayCounter()
    count = 0

    for pseudo_counter in counter_list:
        counter = DelayCounter(
            average=Decimal(str(pseudo_counter.avg_val)),
            minimum=Decimal(str(pseudo_counter.min_val)),
            maximum=Decimal(str(pseudo_counter.max_val)),
        )
        counter.check(mode, common_params.is_live)
        counter.divided_by_factor(Decimal("1000"))
        if not counter.is_valid:
            continue
        val.is_valid = True
        val.average += counter.average
        val.current += counter.current
        if count == 0:
            val.minimum = counter.minimum
            val.maximum = counter.maximum
        else:
            val.minimum = min(counter.minimum, val.minimum)
            val.maximum = max(counter.maximum, val.maximum)
        if counter.is_current_valid:
            val.is_current_valid = True
        count += 1
    if count > 0:
        val.current /= count
        val.average /= count
    if mode == "jitter":
        result.jitter = val.avg_min_max()
    else:
        result.latency = val.avg_min_max()
    return result


def portize_ex(
    result: PortResult,
    replies: List[IExtra],
) -> PortResult:
    c_list = result.get_ex_counters()
    counter_list = [replies[t] for t in c_list]
    for c in counter_list:
        result.fcs_error += c.fcs_error_count
    return result


def portize_rr(
    result: PortResult,
    replies: List[IError],
) -> PortResult:
    c_list = result.get_rr_counters()
    counter_list = [replies[t] for t in c_list]
    tx_all = 0
    for i in range(len(counter_list) // 3):
        tx= counter_list[3 * i]            
        rx =  counter_list[3 * i + 1]
        rr = counter_list[3 * i + 2]        
        if result.is_live:
            result.loss_frames += Decimal(str(rr.non_incre_seq_event_count))
        else:
            lf = max(0, tx.packet_count_since_cleared - rx.packet_count_since_cleared)
            result.loss_frames += Decimal(str(lf))
        tx_all += tx.packet_count_since_cleared
    result.loss_ratio = result.loss_frames / tx_all if tx_all else Decimal("0")
    return result


@dataclass
class ResultGroup:
    stream: Dict
    port: Dict
    all: Dict

    def copy(self) -> "ResultGroup":
        return deepcopy(self)


@dataclass
class ResultHandler:
    stream_result: List[StreamResult] = field(default_factory=list)
    port_result: List[PortResult] = field(default_factory=list)
    all_result: List[AllResult] = field(default_factory=list)


@dataclass
class TestCaseResult:
    throughput: ResultHandler = field(default_factory=ResultHandler)
    latency: ResultHandler = field(default_factory=ResultHandler)
    frame_loss: ResultHandler = field(default_factory=ResultHandler)
    back_to_back: ResultHandler = field(default_factory=ResultHandler)

    def get_result_handler(self, test_type: TestType):
        if test_type == TestType.THROUGHPUT:
            return self.throughput
        elif test_type == TestType.LATENCY_JITTER:
            return self.latency
        elif test_type == TestType.FRAME_LOSS_RATE:
            return self.frame_loss
        else:
            return self.back_to_back

    def get_throughput_result(self) -> Optional[Decimal]:
        result = None
        if self.throughput and self.throughput.all_result:
            throughput_result = self.throughput.all_result[0]
            if throughput_result:
                return throughput_result.rate
        return result


class TrafficStateListener:
    def __init__(self, source_port_structs: List["Structure"]) -> None:
        self.dic = {}
        for port_struct in source_port_structs:
            self.dic[port_struct.port] = False
            port_struct.port.on_traffic_change(self.onchange_traffic_status)

    async def onchange_traffic_status(
        self, port: "GenericL23Port", traffic_value: "P_TRAFFIC.GetDataAttr"
    ) -> None:
        self.dic[port] = bool(traffic_value.on_off)

    def test_running(self):
        return any(v for v in self.dic.values())
