from decimal import Decimal
from typing import Dict, List, Union
from pydantic import BaseModel, Field, validator

import pluginlib.plugin2544.utils.constants as const


class AvgMinMax(BaseModel):
    minimum: Decimal = Decimal(0)
    maximum: Decimal = Decimal(0)
    average: Decimal = Decimal(0)


class DelayData(BaseModel):
    counter_type: const.CounterType = const.CounterType.LATENCY
    minimum: Decimal = Decimal(0)
    maximum: Decimal = Decimal(0)
    average: Decimal = Decimal(0)
    is_valid: bool = True

    @validator("average", "minimum", "maximum", always=True)
    def check_is_valid(cls, v, values):
        if v == values["counter_type"].value:
            values["is_valid"] = False
            return Decimal(0)
        return v


class DelayCounter(AvgMinMax):
    _total: Decimal = Decimal(0)
    _count: int = 0

    class Config:
        underscore_attrs_are_private = True

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
        self.average = (
            Decimal(self._total) / Decimal(self._count) if self._count else Decimal(0)
        )


class StreamCounter(BaseModel):
    frames: Decimal = Decimal(0)  # packet_count_since_cleared
    bps: Decimal = Decimal(0)  # bit_count_last_sec
    pps: Decimal = Decimal(0)  # packet_count_last_sec
    bytes_count: Decimal = Decimal(0)  # byte_count_since_cleared
    loss_frames: Decimal = Decimal(0)
    frame_rate: Decimal = Decimal(0)
    l2_bit_rate: Decimal = Decimal(0)
    l1_bit_rate: Decimal = Decimal(0)
    tx_l1_bps: Decimal = Decimal(0)

    def update(self, counter: "StreamCounter"):
        self.frames += counter.frames  # _cal_port_tx_frames  + _cal_port_rx_frames
        self.bps += counter.bps
        self.pps += counter.pps
        self.bytes_count += counter.bytes_count

    @validator("frames", "bps", "pps", "bytes_count", always=True)
    def set_type(cls, v) -> Decimal:
        return Decimal(str(v))

    def calculate_rate(
        self,
        is_final: bool,
        duration: Decimal,
        frame_size: Decimal,
        interframe_gap: Decimal,
    ):
        self.frame_rate = self.frames / duration
        self.l2_bit_rate = self.frame_rate * Decimal("8") * frame_size
        self.l1_bit_rate = (
            self.frame_rate * Decimal("8") * (frame_size + interframe_gap)
        )
        if is_final:
            self.tx_l1_bps = self.l1_bit_rate
        else:
            self.tx_l1_bps = self.bps * (frame_size + interframe_gap) / frame_size


class PortCounter(StreamCounter):
    counter_type: const.PortCounterType = const.PortCounterType.TX
    _tx_l1_bps: Decimal = Decimal("0")
    l2_bps: Decimal = Decimal(0)
    l1_bps: Decimal = Decimal(0)
    fps: Decimal = Decimal(0)

    class Config:
        underscore_attrs_are_private = True

    def update(self, counter: "StreamCounter"):
        self.frames += counter.frames  # _cal_port_tx_frames  + _cal_port_rx_frames
        self.bps += counter.bps
        self.pps += counter.pps
        self.bytes_count += counter.bytes_count  # _cal_port_rx_bytes
        self._tx_l1_bps += counter.tx_l1_bps

    def calculate_rate(
        self,
        is_final: bool,
        duration: Decimal,
        frame_size: Decimal,
        interframe_gap: Decimal,
    ):
        super().calculate_rate(is_final, duration, frame_size, interframe_gap)
        self.l2_bps = self.l2_bit_rate if is_final else self.bps
        self.fps = self.frame_rate if is_final else self.pps
        self.l1_bps = (
            self.l2_bps * (frame_size + interframe_gap) / frame_size
            if self.counter_type == const.PortCounterType.RX
            else self._tx_l1_bps
        )


class Statistic(BaseModel):
    is_final: bool
    frame_size: Decimal
    duration: Decimal
    interframe_gap: Decimal
    tx_counter: PortCounter = PortCounter()
    rx_counter: PortCounter = PortCounter(counter_type=const.PortCounterType.RX)
    latency: DelayCounter = DelayCounter(counter_type=const.CounterType.LATENCY)
    jitter: DelayCounter = DelayCounter(counter_type=const.CounterType.JITTER)
    fcs_error_frames: int = 0
    loss_frames: Decimal = Decimal(0)
    loss_ratio: Decimal = Decimal(0)

    def add_tx(self, tx_stream_counter: StreamCounter) -> None:
        tx_stream_counter.calculate_rate(
            self.is_final, self.duration, self.frame_size, self.interframe_gap
        )
        self.tx_counter.update(tx_stream_counter)

    def add_rx(self, rx_stream_counter: StreamCounter) -> None:
        rx_stream_counter.calculate_rate(
            self.is_final, self.duration, self.frame_size, self.interframe_gap
        )
        self.rx_counter.update(rx_stream_counter)

    def add_latency(self, delay_data: DelayData) -> None:
        self.latency.update(delay_data)

    def add_jitter(self, delay_data: DelayData) -> None:
        self.jitter.update(delay_data)

    def add_extra(self, fcs: int) -> None:
        self.fcs_error_frames += fcs

    def add_loss(self, loss_frames: Decimal) -> None:
        self.loss_frames += loss_frames

    def calculate_rate(self):
        if self.is_final:
            self.loss_frames = self.tx_counter.frames - self.rx_counter.frames
        self.loss_ratio = (
            self.loss_frames / self.tx_counter.frames
            if self.tx_counter.frames
            else Decimal(0)
        )
        self.tx_counter.calculate_rate(
            self.is_final, self.duration, self.frame_size, self.interframe_gap
        )
        self.rx_counter.calculate_rate(
            self.is_final, self.duration, self.frame_size, self.interframe_gap
        )


class TotalCounter(BaseModel):
    frames: Decimal = Decimal(0)
    l1_bps: Decimal = Decimal(0)
    fps: Decimal = Decimal(0)

    def add(self, counter: PortCounter) -> None:
        self.frames += counter.frames
        self.l1_bps += counter.l1_bps
        self.fps += counter.fps


class TotalStatistic(BaseModel):
    tx_counter: TotalCounter = TotalCounter()
    rx_counter: TotalCounter = TotalCounter()
    rx_loss_percent: Decimal = Decimal(0)
    rx_loss_frames: Decimal = Decimal(0)

    def add(self, port_data: Statistic):
        self.tx_counter.add(port_data.tx_counter)
        self.rx_counter.add(port_data.rx_counter)
        self.rx_loss_frames = port_data.loss_frames
        self.rx_loss_percent = (
            self.rx_loss_frames / self.tx_counter.frames
            if self.tx_counter.frames
            else Decimal(0)
        )


class BaseStatistic(BaseModel):
    tx_frames: int
    rx_frames: int
    latency_ns_avg: float = 0
    latency_ns_min: float = 0
    latency_ns_max: float = 0
    jitter_ns_avg: float = 0
    jitter_ns_min: float = 0
    jitter_ns_max: float = 0


class PortStatistic(BaseStatistic):
    port_id: str
    tx_rate_l1_bps: Decimal = Field()
    tx_rate_fps: Decimal = Field()


class StreamStatistic(BaseStatistic):
    src_port_id: str
    dest_port_id: str
    src_port_addr: str
    dest_port_addr: str


class FinalStatistic(BaseModel):
    test_case_type: const.TestType
    test_suit_type: str = "2544"
    result_state: const.ResultState = const.ResultState.PENDING
    tx_rate_percent: float
    is_final: bool
    frame_size: int
    repetition: Union[int, str]
    port_data: List[Statistic]
    # stream_data: List[LatencyStreamStatistic]
    total: TotalStatistic = TotalStatistic()

    class Config:
        arbitrary_types_allowed = True

    @validator("total", always=True)
    def calculate_total(cls, v, values) -> TotalStatistic:
        total = TotalStatistic()
        for port_data in values["port_data"]:
            total.add(port_data)
        return total
        # total_tx_frames = 0
        # total_tx_rate_l1_bps = 0
        # total_tx_rate_fps = 0
        # total_rx_frames = 0
        # total_rx_rate_l1_bps = 0
        # total_rx_rate_fps = 0
        # total_loss_frames = 0
        # for port_data in values["port_data"]:
        #     total_tx_frames += port_data.tx_counter.frames
        #     total_tx_rate_l1_bps += port_data.tx_counter.l1_bps
        #     total_tx_rate_fps += port_data.tx_counter.fps
        #     total_rx_frames += port_data.rx_counter.frames
        #     total_rx_rate_l1_bps += port_data.rx_counter.l1_bps
        #     total_rx_rate_fps += port_data.rx_counter.fps
        #     total_loss_frames += port_data.loss_frames
        # return TotalStatistic(
        #     tx_frames=total_tx_frames,
        #     rx_frames=total_rx_frames,
        #     tx_rate_l1_bps=total_tx_rate_l1_bps,
        #     tx_rate_fps=total_tx_rate_fps,
        #     rx_loss_percent=
        # )

    def set_result_state(self, state: const.ResultState) -> None:
        self.result_state = state


class StatisticParams(BaseModel):
    test_case_type: const.TestType
    result_state: const.ResultState = const.ResultState.PENDING
    rate_percent: float
    frame_size: int
    duration: int
    repetition: Union[int, str]

LATENCY_OUTPUT = {
    "test_suit_type": ...,
    "result_state": ...,
    "test_case_type": ...,
    "tx_rate_percent": ...,
    "is_final": ...,
    "frame_size": ...,
    "repetition": ...,
    "port_data": {
        "__all__": {
            "tx_counter": {"frames"},
            "rx_counter": {"frames"},
            "latency": {"minimum", "maximum", "average"},
            "jitter": {"minimum", "maximum", "average"},
        }
    },
    "total": {
        "tx_counter": {"frames", "l1_bps", "fps"},
        "rx_counter": {"frames"},
    },
}

FRAME_LOSS_OUTPUT = {
    "test_suit_type": ...,
    "test_case_type": ...,
    "result_state": ...,
    "tx_rate_percent": ...,
    "is_final": ...,
    "frame_size": ...,
    "repetition": ...,
    "port_data": {
        "__all__": {
            "tx_counter": {"frames", "l1_bps", "fps"},
            "rx_counter": {"frames", "l1_bps", "fps"},
        }
    },
    "total": {
        "tx_counter": {"frames", "l1_bps", "fps"},
        "rx_counter": {"frames", "l1_bps", "fps"},
        "rx_loss_frames": ...,
        "rx_loss_percent": ...,
    },
}
