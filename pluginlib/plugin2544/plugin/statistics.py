from decimal import Decimal
from typing import List, Union
from pydantic import BaseModel, Field, validator

from pluginlib.plugin2544.utils.constants import Enum


class CounterType(Enum):
    JITTER = -1
    LATENCY = -2147483648


class AvgMinMax(BaseModel):
    total: int = 0
    minimum: int = 0
    maximum: int = 0
    avg: int = 0


class DelayData(BaseModel):
    counter_type: CounterType = CounterType.LATENCY
    total: int = 0
    minimum: int = 0
    maximum: int = 0
    is_valid: bool = True

    @validator("total", "minimum", "maximum", always=True)
    def check_is_valid(cls, v, values):
        if v == values["counter_type"].value:
            values["is_valid"] = False
            return 0
        return v


class DelayCounter(AvgMinMax):
    count: int = 0

    def update(self, data: DelayData) -> None:
        if not data.is_valid:
            return
        self.total += data.total
        self.minimum = min(data.minimum, self.minimum)
        self.maximum = max(data.maximum, self.maximum)
        self.count += 1

    @property
    def average(self) -> Decimal:
        return Decimal(self.total) / Decimal(self.count) if self.count else Decimal(0)


class CommonCounter(BaseModel):
    is_final: bool = Field(False, exclude=True)
    frame_size: Decimal = Field(Decimal(0), exclude=True)
    duration: Decimal = Field(Decimal(0), exclude=True)
    interframe_gap: Decimal = Field(Decimal(0), exclude=True)
    frames: int = 0  # packet_count_since_cleared
    bps: int = 0  # bit_count_last_sec
    pps: int = 0  # packet_count_last_sec
    bytes_count: int = 0  # byte_count_since_cleared

    def update(self, counter: "StreamCounter"):
        if not int(self.frame_size):
            self.frame_size = counter.frame_size
        if not int(self.duration):
            self.duration = counter.duration
        self.frames += counter.frames  # _cal_port_tx_frames  + _cal_port_rx_frames
        self.bps += counter.bps
        self.pps += counter.pps
        self.bytes_count += counter.bytes_count

    @validator("frame_size", "duration", "interframe_gap", always=True)
    def set_type(cls, v) -> Decimal:
        return Decimal(str(v))

    @property
    def frame_rate(self):
        return self.frames / self.duration

    @property
    def l2_bit_rate(self):  # convert_l2_bit_rate
        return self.frame_rate * Decimal("8") * self.frame_size

    @property
    def l1_bit_rate(self):  # convert_l1_bit_rate
        return self.frame_rate * Decimal("8") * (self.frame_size + self.interframe_gap)


class StreamCounter(CommonCounter):
    pass


class PortCounterType(Enum):
    TX = 0
    RX = 1


class PortCounter(CommonCounter):
    counter_type: PortCounterType = PortCounterType.TX
    _tx_l1_bps: Decimal = Decimal("0")

    class Config:
        underscore_attrs_are_private = True

    def update(self, counter: "StreamCounter"):
        if not int(self.frame_size):
            self.frame_size = counter.frame_size
        if not int(self.duration):
            self.duration = counter.duration

        self.frames += counter.frames  # _cal_port_tx_frames  + _cal_port_rx_frames
        self.bps += counter.bps
        self.pps += counter.pps
        self.bytes_count += counter.bytes_count  # _cal_port_rx_bytes
        if self.is_final:  # _cal_port_tx_bps_l1
            self._tx_l1_bps += counter.l1_bit_rate
        else:
            self._tx_l1_bps += (
                counter.bps * (self.frame_size + self.interframe_gap) / self.frame_size
            )

    @property
    def l2_bps(self):  # _cal_port_tx_bps_l2 + _cal_port_rx_bps_l2
        if self.is_final:
            return self.l2_bit_rate
        else:
            return self.bps

    @property
    def fps(self):  # _cal_port_tx_pps + _cal_port_rx_pps
        if self.is_final:
            return self.frames
        else:
            return self.pps

    @property
    def l1_bps(self):
        if self.counter_type == PortCounterType.RX:
            return (
                self.l2_bps * (self.frame_size + self.interframe_gap) / self.frame_size
            )
        else:
            return self._tx_l1_bps


class Statistic(CommonCounter):
    tx_counter: PortCounter = PortCounter()
    rx_counter: PortCounter = PortCounter(counter_type=PortCounterType.RX)
    latency: DelayCounter = DelayCounter(counter_type=CounterType.LATENCY)
    jitter: DelayCounter = DelayCounter(counter_type=CounterType.JITTER)
    fcs_error_frames: int = 0
    loss_frames: int = 0

    def add_tx(self, tx_counter: StreamCounter) -> None:
        self.tx_counter.update(tx_counter)

    def add_rx(self, rx_counter: StreamCounter) -> None:
        self.rx_counter.update(rx_counter)

    def add_latency(self, delay_data: DelayData) -> None:
        self.latency.update(delay_data)

    def add_jitter(self, delay_data: DelayData) -> None:
        self.jitter.update(delay_data)

    def add_extra(self, fcs: int) -> None:
        self.fcs_error_frames += fcs

    def add_loss(self, loss_frames: int) -> None:
        self.loss_frames += loss_frames


class LatencyTotalStatistic(BaseModel):
    tx_frames: int
    rx_frames: int
    tx_rate_l1_bps: int
    tx_rate_fps: int


class LatencyBaseStatistic(BaseModel):
    tx_frames: int
    rx_frames: int
    latency_ns_avg: float = 0
    latency_ns_min: float = 0
    latency_ns_max: float = 0
    jitter_ns_avg: float = 0
    jitter_ns_min: float = 0
    jitter_ns_max: float = 0


class LatencyPortStatistic(LatencyBaseStatistic):
    port_id: str
    tx_rate_l1_bps: Decimal = Field()
    tx_rate_fps: Decimal = Field()


class LatencyStreamStatistic(LatencyBaseStatistic):
    src_port_id: str
    dest_port_id: str
    src_port_addr: str
    dest_port_addr: str


class LatencyStatistic(BaseModel):
    test_suit_type: str = "2544"
    result_state: str = "Done"
    tx_rate_percent: float
    is_final: bool
    frame_size: int
    repetition: Union[int, str]
    port_data: List[LatencyPortStatistic]
    stream_data: List[LatencyStreamStatistic]
    total: LatencyTotalStatistic
