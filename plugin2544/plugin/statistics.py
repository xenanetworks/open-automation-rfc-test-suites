import math
from decimal import Decimal
from typing import Any, Dict, List, Union, TYPE_CHECKING
from pydantic import BaseModel, validator
from operator import attrgetter
from ..utils import constants as const

if TYPE_CHECKING:
    from .structure import PortStruct


class AvgMinMax(BaseModel):
    minimum: int = 0
    maximum: int = 0
    average: int = 0


class DelayData(BaseModel):
    counter_type: const.CounterType = const.CounterType.LATENCY
    minimum: int = 0
    maximum: int = 0
    average: int = 0
    is_valid: bool = True

    @validator("average", "minimum", "maximum", always=True)
    def check_is_valid(cls, v: int, values: Dict[str, Any]) -> int:
        if v == values["counter_type"].value:
            values["is_valid"] = False
            return 0
        return v


class DelayCounter(AvgMinMax):
    _total: int = 0
    _count: int = 0

    class Config:
        underscore_attrs_are_private = True

    def sum(self, other: "DelayCounter") -> None:
        for name, value in self:
            setattr(self, name, value + attrgetter(name)(other))

    def avg(self, count: int) -> None:
        for name, value in self:
            setattr(self, name, math.floor(Decimal(str(value)) / Decimal(str(count))))

    def update(self, data: DelayData) -> None:
        if not data.is_valid:
            return
        self._total += data.average
        if self._count == 0:
            self.minimum = data.minimum
            self.maximum = data.maximum
        else:
            self.minimum = min(data.minimum, self.minimum)
            self.maximum = max(data.maximum, self.maximum)
        self._count += 1
        self.average = math.floor(
            Decimal(self._total) / Decimal(self._count) if self._count else 0
        )


class StreamCounter(BaseModel):
    frames: int = 0  # packet_count_since_cleared
    bps: int = 0  # bit_count_last_sec
    pps: int = 0  # packet_count_last_sec
    bytes_count: int = 0  # byte_count_since_cleared
    frame_rate: Decimal = Decimal("0.0")
    l2_bit_rate: Decimal = Decimal("0.0")
    l1_bit_rate: Decimal = Decimal("0.0")
    tx_l1_bps: Decimal = Decimal("0.0")

    def add_stream_counter(self, counter: "StreamCounter") -> None:
        """update stream counter by pr stream"""
        self.frames += counter.frames  # _cal_port_tx_frames  + _cal_port_rx_frames
        self.bps += counter.bps
        self.pps += counter.pps
        self.bytes_count += counter.bytes_count  # _cal_port_rx_bytes

    def calculate_stream_rate(
        self,
        is_final: bool,
        duration: Decimal,
        frame_size: Decimal,
        interframe_gap: Decimal,
    ) -> None:
        self.frame_rate = Decimal(str(self.frames)) / duration
        self.l2_bit_rate = self.frame_rate * Decimal("8") * frame_size
        self.l1_bit_rate = (
            self.frame_rate * Decimal("8") * (frame_size + interframe_gap)
        )
        if is_final:
            self.tx_l1_bps = self.l1_bit_rate
        else:
            self.tx_l1_bps = self.bps * (frame_size + interframe_gap) / frame_size


class PRStatistic(BaseModel):
    """pr stream statistic"""

    rx_stream_counter: StreamCounter = StreamCounter()
    latency: DelayData = DelayData(counter_type=const.CounterType.LATENCY)
    jitter: DelayData = DelayData(counter_type=const.CounterType.JITTER)
    live_loss_frames: int = 0


class StreamStatisticData(BaseModel):
    """stream statistic"""

    src_port_id: str = ""
    dest_port_id: str = ""
    src_port_addr: str = ""
    dest_port_addr: str = ""
    tx_counter: StreamCounter = StreamCounter()
    rx_counter: StreamCounter = StreamCounter()
    latency: DelayCounter = DelayCounter()
    jitter: DelayCounter = DelayCounter()
    live_loss_frames: int = 0
    burst_frames: int = 0

    def add_pr_stream_statistic(self, pr_stream_statistic: "PRStatistic") -> None:
        """aggregate pr stream statistic"""
        self.rx_counter.add_stream_counter(pr_stream_statistic.rx_stream_counter)
        self.latency.update(pr_stream_statistic.latency)
        self.jitter.update(pr_stream_statistic.jitter)
        self.live_loss_frames += pr_stream_statistic.live_loss_frames

    def calculate(
        self, tx_port_struct: "PortStruct", rx_port_struct: "PortStruct"
    ) -> None:
        """for stream based mode to recalculate port statistic based on best result storage"""
        tx_port_struct.statistic.aggregate_tx_statistic(self)
        rx_port_struct.statistic.add_rx(self.rx_counter)
        rx_port_struct.statistic.add_latency(DelayData.parse_obj(self.latency))
        rx_port_struct.statistic.add_jitter(DelayData.parse_obj(self.jitter))


class PortCounter(StreamCounter):
    counter_type: const.PortCounterType = const.PortCounterType.TX
    _tx_l1_bps: Decimal = Decimal("0")
    l2_bps: int = 0
    l1_bps: int = 0
    fps: int = 0

    class Config:
        underscore_attrs_are_private = True

    def sum(self, other: "PortCounter") -> None:
        for name, value in self:
            if name == "counter_type":
                continue
            setattr(self, name, value + attrgetter(name)(other))

    def avg(self, count: int) -> None:
        for name, value in self:
            if name == "counter_type":
                continue
            setattr(self, name, math.floor(Decimal(str(value)) / Decimal(str(count))))

    def add_stream_counter(self, counter: "StreamCounter") -> None:
        """aggregate stream statistic"""
        self.frames += counter.frames  # _cal_port_tx_frames  + _cal_port_rx_frames
        self.bps += counter.bps
        self.pps += counter.pps
        self.bytes_count += counter.bytes_count  # _cal_port_rx_bytes
        self._tx_l1_bps += counter.tx_l1_bps

    def calculate_port_rate(
        self,
        is_final: bool,
        duration: Decimal,
        frame_size: Decimal,
        interframe_gap: Decimal,
    ) -> None:
        super().calculate_stream_rate(is_final, duration, frame_size, interframe_gap)
        self.l2_bps = math.floor(self.l2_bit_rate) if is_final else self.bps
        self.fps = math.floor(self.frame_rate) if is_final else self.pps
        self.l1_bps = math.floor(
            self.l2_bps * (frame_size + interframe_gap) / frame_size
            if self.counter_type == const.PortCounterType.RX
            else self._tx_l1_bps
        )


class Statistic(BaseModel):
    port_id: str = ""
    is_final: bool = False  # for calculation use
    frame_size: Decimal = Decimal("1")  # for calculation use
    duration: Decimal = Decimal("0")  # for calculation use
    rate: Decimal = Decimal("0")  # # for calculation use
    interframe_gap: Decimal = Decimal("0")  # for calculation use
    port_speed: Decimal = Decimal("0")  # for calculation use
    tx_counter: PortCounter = PortCounter(counter_type=const.PortCounterType.TX)
    rx_counter: PortCounter = PortCounter(counter_type=const.PortCounterType.RX)
    latency: DelayCounter = DelayCounter()
    jitter: DelayCounter = DelayCounter()
    stream_statistic: List[StreamStatisticData] = []
    fcs_error_frames: int = 0
    burst_frames: int = 0
    burst_bytes_count: int = 0
    loss_frames: int = 0
    loss_ratio: Decimal = Decimal("0.0")
    actual_rate_percent: Decimal = Decimal("0.0")
    tx_rate_l1_bps_theor: int = 0
    tx_rate_fps_theor: int = 0

    @validator("tx_rate_l1_bps_theor", always=True)
    def set_theor_l1_bps_rate(cls, _v: int, values: Dict[str, Any]) -> int:
        return math.floor(values["port_speed"])

    @validator("tx_rate_fps_theor", always=True)
    def set_theor_fps_rate(cls, _v: int, values: Dict[str, Any]) -> int:
        return math.floor(
            values["port_speed"]
            / Decimal("8")
            / (values["interframe_gap"] + values["frame_size"])
        )

    def sum(self, other: "Statistic") -> None:
        self.tx_counter.sum(other.tx_counter)
        self.rx_counter.sum(other.rx_counter)

        self.latency.sum(other.latency)
        self.jitter.sum(other.jitter)
        for f in [
            "fcs_error_frames",
            "burst_frames",
            "burst_bytes_count",
            "loss_frames",
            "loss_ratio",
        ]:
            value = getattr(self, f)
            setattr(self, f, value + attrgetter(f)(other))

    def avg(self, count: int) -> None:
        self.tx_counter.avg(count)
        self.rx_counter.avg(count)

        self.latency.avg(count)
        self.jitter.avg(count)
        for f in [
            "fcs_error_frames",
            "burst_frames",
            "burst_bytes_count",
            "loss_frames",
            "loss_ratio",
        ]:
            value = getattr(self, f)
            setattr(self, f, math.floor(Decimal(str(value)) / Decimal(str(count))))

    def aggregate_tx_statistic(self, stream_statistic: "StreamStatisticData") -> None:
        """aggregate tx port statistic based on stream statistic"""
        self.add_tx(stream_statistic.tx_counter)
        self.add_burst_frames(stream_statistic.burst_frames)
        self.add_burst_bytes_count(stream_statistic.rx_counter.bytes_count)
        self.add_loss(
            stream_statistic.tx_counter.frames,
            stream_statistic.rx_counter.frames,
            stream_statistic.live_loss_frames,
        )
        self.stream_statistic.append(stream_statistic)

    def aggregate_rx_statistic(self, pr_statistic: "PRStatistic") -> None:
        """aggregate rx port statistic based on pr statistic"""
        self.add_rx(pr_statistic.rx_stream_counter)
        self.add_latency(pr_statistic.latency)
        self.add_jitter(pr_statistic.jitter)
        # self.add_extra(pr_statistic.fcs)

    def add_tx(self, tx_stream_counter: "StreamCounter") -> None:
        tx_stream_counter.calculate_stream_rate(
            self.is_final, self.duration, self.frame_size, self.interframe_gap
        )
        self.tx_counter.add_stream_counter(tx_stream_counter)

    def add_rx(self, rx_stream_counter: "StreamCounter") -> None:
        rx_stream_counter.calculate_stream_rate(
            self.is_final, self.duration, self.frame_size, self.interframe_gap
        )
        self.rx_counter.add_stream_counter(rx_stream_counter)

    def add_latency(self, delay_data: "DelayData") -> None:
        self.latency.update(delay_data)

    def add_jitter(self, delay_data: "DelayData") -> None:
        self.jitter.update(delay_data)

    def add_burst_frames(self, frame_count: int) -> None:
        self.burst_frames += frame_count

    def add_burst_bytes_count(self, bytes_count: int) -> None:
        self.burst_bytes_count += bytes_count

    def add_loss(self, tx_frames: int, rx_frames: int, live_loss_frames: int) -> None:
        if self.is_final:
            self.loss_frames += tx_frames - rx_frames
        else:
            self.loss_frames += live_loss_frames

    def calculate_rate(self) -> None:
        self.loss_ratio = (
            Decimal(str(self.loss_frames)) / Decimal(str(self.tx_counter.frames))
            if self.tx_counter.frames
            else Decimal("0")
        )
        self.tx_counter.calculate_port_rate(
            self.is_final, self.duration, self.frame_size, self.interframe_gap
        )
        self.rx_counter.calculate_port_rate(
            self.is_final, self.duration, self.frame_size, self.interframe_gap
        )
        self.actual_rate_percent = (
            Decimal("100") * self.tx_counter.l1_bit_rate / self.port_speed
        )


class TotalCounter(BaseModel):
    frames: int = 0
    l1_bps: int = 0
    l2_bps: int = 0
    fps: int = 0
    bytes_count: int = 0

    def add(self, counter: "PortCounter") -> None:
        self.frames += counter.frames
        self.l1_bps += counter.l1_bps
        self.l2_bps += counter.l2_bps
        self.fps += counter.fps
        self.bytes_count += counter.bytes_count

    def sum(self, other: "TotalCounter") -> None:
        for name, value in self:
            setattr(self, name, value + attrgetter(name)(other))

    def avg(self, count: int) -> None:
        for name, value in self:
            setattr(self, name, math.floor(Decimal(str(value)) / Decimal(str(count))))


class TotalStatistic(BaseModel):
    tx_counter: TotalCounter = TotalCounter()
    rx_counter: TotalCounter = TotalCounter()
    fcs_error_frames: int = 0
    rx_loss_percent: Decimal = Decimal("0.0")
    rx_loss_frames: int = 0
    tx_rate_l1_bps_theor: int = 0
    tx_rate_fps_theor: int = 0
    tx_burst_frames: int = 0
    tx_burst_bytes: int = 0
    ber_percent: Decimal = Decimal("0.0")

    def sum(self, other: "TotalStatistic") -> None:
        for name, value in self:
            if name in ["tx_counter", "rx_counter"]:
                getattr(self, name).sum(attrgetter(name)(other))
            else:
                setattr(self, name, value + attrgetter(name)(other))

    def avg(self, count: int) -> None:
        for name, value in self:
            if name in ["tx_counter", "rx_counter"]:
                getattr(self, name).avg(count)
            else:
                setattr(
                    self, name, math.floor(Decimal(str(value)) / Decimal(str(count)))
                )

    def add(self, port_data: "Statistic") -> None:
        self.tx_counter.add(port_data.tx_counter)
        self.rx_counter.add(port_data.rx_counter)
        self.fcs_error_frames += port_data.fcs_error_frames
        self.tx_rate_l1_bps_theor += port_data.tx_rate_l1_bps_theor
        self.tx_rate_fps_theor += port_data.tx_rate_fps_theor
        self.rx_loss_frames += port_data.loss_frames
        self.tx_burst_bytes += port_data.burst_bytes_count
        self.tx_burst_frames += port_data.burst_frames
        self.rx_loss_percent = (
            Decimal(str(self.rx_loss_frames)) / Decimal(str(self.tx_counter.frames))
            if self.tx_counter.frames
            else Decimal("0.0")
        )

        if (
            self.rx_counter.bytes_count == 0
            or self.rx_counter.frames == 0
            or self.rx_loss_frames <= 0
        ):
            self.ber_percent = Decimal("0.0")
        else:
            divisor = (
                Decimal("8.0")
                * Decimal(str(self.rx_counter.bytes_count))
                * (
                    Decimal(str(self.rx_counter.frames))
                    + Decimal(str(self.rx_loss_frames))
                )
            )
            self.ber_percent = (
                Decimal(str(self.rx_loss_frames))
                * Decimal(str(self.rx_counter.frames))
                / Decimal(str(divisor))
            )


class FinalStatistic(BaseModel):
    test_case_type: const.TestType
    test_suite_type: str = "xoa2544"
    result_state: const.ResultState = const.ResultState.PENDING
    tx_rate_percent: Decimal
    is_final: bool = True
    frame_size: Decimal
    repetition: Union[int, str] = "avg"
    rate_result_scope: const.RateResultScopeType = const.RateResultScopeType.COMMON
    port_data: List[Statistic] = []
    tx_rate_nominal_percent: Decimal = Decimal("0.0")
    total: TotalStatistic = TotalStatistic()

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {Decimal: lambda x: float("{:.3f}".format(x).rstrip("0"))}

    @validator("total", always=True)
    def calculate_total(
        cls, _v: "TotalStatistic", values: Dict[str, Any]
    ) -> TotalStatistic:
        total = TotalStatistic()
        for port_data in values["port_data"]:
            total.add(port_data)
        return total

    def set_result_state(self, state: "const.ResultState") -> None:
        self.result_state = state

    def sum(self, final: "FinalStatistic") -> None:
        for k, port_statistic in enumerate(self.port_data):
            port_statistic.sum(final.port_data[k])
        self.total.sum(final.total)

    def avg(self, count: int) -> None:
        for port_statistic in self.port_data:
            port_statistic.avg(count)
        self.total.avg(count)


class StatisticParams(BaseModel):
    test_case_type: const.TestType
    result_state: const.ResultState = const.ResultState.PENDING
    frame_size: Decimal
    duration: Decimal
    repetition: Union[int, str]
    rate_percent: Decimal = Decimal("0")