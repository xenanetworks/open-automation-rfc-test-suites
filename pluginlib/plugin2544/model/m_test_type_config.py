from decimal import Decimal
from typing import Dict, Iterable, List, Union
from pydantic import (
    BaseModel,
    Field,
    validator,
    NonNegativeInt,
    PositiveInt,
)

from ..utils import output_format

from ..utils.constants import (
    DurationFrameUnit,
    DurationType,
    DurationTimeUnit,
    SearchType,
    RateResultScopeType,
    TestType,
    LatencyModeStr,
    AcceptableLossType,
)
from ..utils import exceptions
from ..utils import constants


class CommonOptions(BaseModel):
    duration_type: DurationType
    duration: Decimal
    duration_unit: Union[DurationFrameUnit, DurationTimeUnit]
    iterations: PositiveInt

    @validator("duration_unit", always=True)
    def validate_duration(cls, v, values):
        
        if "duration_type" in values and not values["duration_type"].is_time_duration:
            cur = values["duration"] * v.scale
            if cur > constants.MAX_PACKET_LIMIT_VALUE:
                raise exceptions.PacketLimitOverflow(cur)
        return v

    @property
    def actual_duration(self) -> Decimal:
        return self.duration * self.duration_unit.scale


class RateIterationOptions(BaseModel):
    search_type: SearchType
    result_scope: RateResultScopeType
    initial_value_pct: Decimal = Field(ge=0.0, le=100.0)
    maximum_value_pct: Decimal = Field(ge=0.0, le=100.0)
    minimum_value_pct: Decimal = Field(ge=0.0, le=100.0)
    value_resolution_pct: Decimal = Field(ge=0.0, le=100.0)

    @validator("initial_value_pct", "minimum_value_pct")
    def check_if_larger_than_maximun(cls, v: Decimal, values) -> Decimal:
        if "maximum_value_pct" in values:
            if v > values["maximum_value_pct"]:
                raise exceptions.RateRestriction(v, values["maximum_value_pct"])
        return v


class ThroughputTest(BaseModel):
    test_type: TestType
    enabled: bool
    common_options: CommonOptions
    rate_iteration_options: RateIterationOptions
    # pass_criteria PassCriteria
    use_pass_threshold: bool
    pass_threshold_pct: float
    acceptable_loss_pct: float
    collect_latency_jitter: bool
    # additional_statisics: List[AdditionalStatisticsOption]
    _output_format: Dict = output_format.THROUGHPUT_COMMON

    @property
    def format(self) -> Dict:
        if self.rate_iteration_options.result_scope.is_per_source_port:
            f = output_format.THROUGHPUT_PER_PORT
        else:
            f = output_format.THROUGHPUT_COMMON
        if self.collect_latency_jitter:
            f["port_data"]["__all__"]["latency"] = {"average", "minimum", "maximum"}
            f["port_data"]["__all__"]["jitter"] = {"average", "minimum", "maximum"}
        return f


class RateSweepOptions(BaseModel):
    start_value_pct: Decimal
    end_value_pct: Decimal
    step_value_pct: Decimal
    burst_resolution: Decimal = Decimal("0")

    @validator(
        "start_value_pct",
        "end_value_pct",
        "step_value_pct",
        "burst_resolution",
        pre=True,
        always=True,
    )
    def set_pcts(cls, v: Decimal) -> Decimal:
        return Decimal(str(v))

    def set_throughput_relative(self, throughput_rate: Decimal) -> None:
        self.start_value_pct = self.start_value_pct * throughput_rate / 100
        self.end_value_pct = self.end_value_pct * throughput_rate / 100
        self.step_value_pct = self.step_value_pct * throughput_rate / 100

    @property
    def rate_sweep_list(self) -> Iterable[Decimal]:
        start_value_pct = self.start_value_pct
        end_value_pct = self.end_value_pct
        step_value_pct = self.step_value_pct
        if start_value_pct > end_value_pct:
            raise exceptions.RangeRestriction()
        if step_value_pct <= Decimal("0"):
            raise exceptions.StepValueRestriction()
        pct = start_value_pct
        while True:
            yield pct
            if pct == end_value_pct:
                break
            elif pct < end_value_pct:
                pct += step_value_pct
            if pct > end_value_pct:
                break
        if pct != end_value_pct:
            yield end_value_pct


class LatencyTest(BaseModel):
    test_type: TestType
    enabled: bool
    common_options: CommonOptions
    rate_sweep_options: RateSweepOptions
    latency_mode: LatencyModeStr
    use_relative_to_throughput: bool
    throughput: Decimal = Decimal("0")

    @property
    def format(self):
        return output_format.LATENCY_OUTPUT


class FrameLossRateTest(BaseModel):
    test_type: TestType
    enabled: bool
    common_options: CommonOptions
    rate_sweep_options: RateSweepOptions

    # Convergence(BaseModel):
    use_gap_monitor: bool
    gap_monitor_start_microsec: NonNegativeInt
    gap_monitor_stop_frames: NonNegativeInt

    # PassCriteriaOptions
    use_pass_fail_criteria: bool
    acceptable_loss_pct: float
    acceptable_loss_type: AcceptableLossType

    @property
    def format(self) -> Dict:
        return output_format.FRAME_LOSS_OUTPUT


class BackToBackTest(BaseModel):
    test_type: TestType
    enabled: bool
    common_options: CommonOptions
    rate_sweep_options: RateSweepOptions

    @property
    def format(self) -> Dict:
        return output_format.BACKTOBACKOUTPUT


AllTestType = Union[ThroughputTest, LatencyTest, FrameLossRateTest, BackToBackTest]


class TestTypesConfiguration(BaseModel):
    throughput_test: ThroughputTest
    latency_test: LatencyTest
    frame_loss_rate_test: FrameLossRateTest
    back_to_back_test: BackToBackTest

    # Computed Properties
    available_test: List[AllTestType] = []

    @validator("available_test", pre=True, always=True)
    def set_available_test(cls, v: List[AllTestType], values) -> List[AllTestType]:
        v = []
        for test_type_config in values.values():
            if test_type_config.enabled:
                v.append(test_type_config)
        return v
