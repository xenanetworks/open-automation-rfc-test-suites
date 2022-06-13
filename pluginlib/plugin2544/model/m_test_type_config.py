from decimal import Decimal
from typing import Iterable, List, Union
from pydantic import (
    BaseModel,
    Field,
    validator,
    NonNegativeInt,
    PositiveInt,
)

from pluginlib.plugin2544.utils.constants import (
    DurationType,
    DurationTimeUnit,
    SearchType,
    RateResultScopeType,
    TestType,
    AdditionalStatisticsOption,
    LatencyModeStr,
    AcceptableLossType,
)
from ..utils import exceptions


class CommonOptions(BaseModel):
    duration_type: DurationType
    duration: Decimal
    duration_time_unit: DurationTimeUnit
    iterations: PositiveInt

    @property
    def actual_duration(self) -> int:
        return int(self.duration * self.duration_time_unit.scale)


class RateIterationOptions(BaseModel):
    search_type: SearchType
    result_scope: RateResultScopeType
    initial_value_pct: float = Field(ge=0.0, le=100.0)
    maximum_value_pct: float = Field(ge=0.0, le=100.0)
    minimum_value_pct: float = Field(ge=0.0, le=100.0)
    value_resolution_pct: float = Field(ge=0.0, le=100.0)

    @validator("initial_value_pct", "minimum_value_pct")
    def check_if_larger_than_maximun(cls, v: float, values) -> float:
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
    additional_statisics: List[AdditionalStatisticsOption]


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


class BackToBackTest(BaseModel):
    test_type: TestType
    enabled: bool
    common_options: CommonOptions
    rate_sweep_options: RateSweepOptions


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
