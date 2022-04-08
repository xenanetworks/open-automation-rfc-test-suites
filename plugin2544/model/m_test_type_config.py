from decimal import Decimal, getcontext
from typing import List, Union
from pydantic import (
    BaseModel,
    Field,
    validator,
    NonNegativeInt,
    PositiveInt,
)

from ..utils.constants import (
    DurationType,
    DurationTimeUnit,
    DurationFrameUnit,
    SearchType,
    RateResultScopeType,
    TestType,
    AdditionalStatisticsOption,
    LatencyModeStr,
    AcceptableLossType,
)
from ..utils.errors import ConfigError


class CommonOptions(BaseModel):
    duration_type: DurationType
    duration: Decimal
    duration_time_unit: DurationTimeUnit
    # duration_frames: PositiveInt
    # duration_frame_unit: DurationFrameUnit
    iterations: PositiveInt

    # computed properties
    actual_duration: Decimal = Decimal("0")
    # actual_frames: Decimal = Decimal("0")

    # def get_set_actual_duration(
    #     self, actual_duration: Decimal = Decimal("0")
    # ) -> Decimal:
    #     if self.duration_type == DurationType.TIME or actual_duration == Decimal("0"):
    #         self.actual_duration = Decimal(str(self.duration)) * Decimal(
    #             str(self.duration_time_unit.scale)
    #         )
    #     else:
    #         self.actual_duration = actual_duration
    #     return self.actual_duration

    @validator("actual_duration", pre=True, always=True)
    def set_actual_duration(cls, v, values):
        return values['duration'] * values['duration_time_unit'].scale 


    # @validator("actual_frames", pre=True, always=True)
    # def set_actual_frames(cls, v, values):
    #     return values["duration_frames"] * values["duration_frame_unit"].scale


class RateIterationOptions(BaseModel):
    search_type: SearchType
    result_scope: RateResultScopeType
    initial_value_pct: float = Field(ge=0.0, le=100.0)
    maximum_value_pct: float = Field(ge=0.0, le=100.0)
    minimum_value_pct: float = Field(ge=0.0, le=100.0)
    value_resolution_pct: float = Field(ge=0.0, le=100.0)

    @validator("initial_value_pct", "minimum_value_pct")
    def check_if_larger_than_maximun(cls, v, values):
        if "maximum_value_pct" in values:
            if v > values["maximum_value_pct"]:
                raise ConfigError(f"{v} cannot be larger than the maximum rate")
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


def rate_sweep_range(rate_sweep_options: "RateSweepOptions") -> List:
    result = []
    start_value_pct = rate_sweep_options.start_value_pct
    end_value_pct = rate_sweep_options.end_value_pct
    step_value_pct = rate_sweep_options.step_value_pct
    if start_value_pct > end_value_pct:
        raise ConfigError("Start rate cannot be larger than the End rate.")
    if step_value_pct <= Decimal("0"):
        raise ConfigError("Step value percent must be larger than 0!")
    pct = start_value_pct
    while pct <= end_value_pct:
        result.append(pct)
        pct += step_value_pct
    if result[-1] != end_value_pct:
        result.append(end_value_pct)
    return result


def set_rate_sweep_list(v, values) -> List[Decimal]:

    if any(
        [
            not "enabled" in values,
            not "rate_sweep_options" in values,
            not values["enabled"],
        ]
    ):
        return v
    return rate_sweep_range(values["rate_sweep_options"])


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
    def set_pcts(cls, v):
        return Decimal(str(v))

    def set_throughput_relative(self, throughput_rate: Decimal):
        self.start_value_pct = self.start_value_pct * throughput_rate / 100
        self.end_value_pct = self.end_value_pct * throughput_rate / 100
        self.step_value_pct = self.step_value_pct * throughput_rate / 100


class LatencyTest(BaseModel):
    test_type: TestType
    enabled: bool
    common_options: CommonOptions
    rate_sweep_options: RateSweepOptions
    latency_mode: LatencyModeStr
    use_relative_to_throughput: bool
    throughput: Decimal = Decimal("0")

    # Computed Properties
    rate_sweep_list: List[Decimal] = []

    _set_rate_sweep_list = validator(
        "rate_sweep_list", allow_reuse=True, pre=True, always=True
    )(set_rate_sweep_list)


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

    # Computed Properties
    rate_sweep_list: List[Decimal] = []

    _set_rate_sweep_list = validator(
        "rate_sweep_list", allow_reuse=True, pre=True, always=True
    )(set_rate_sweep_list)


class BackToBackTest(BaseModel):
    test_type: TestType
    enabled: bool
    common_options: CommonOptions
    rate_sweep_options: RateSweepOptions

    # Computed Properties
    rate_sweep_list: List[Decimal] = []
    _set_rate_sweep_list = validator(
        "rate_sweep_list", allow_reuse=True, pre=True, always=True
    )(set_rate_sweep_list)


class TestTypesConfiguration(BaseModel):
    throughput_test: ThroughputTest
    latency_test: LatencyTest
    frame_loss_rate_test: FrameLossRateTest
    back_to_back_test: BackToBackTest

    # Computed Properties
    available_test: List = []

    @validator("available_test", pre=True, always=True)
    def set_available_test(cls, v, values) -> List[Union[ThroughputTest, LatencyTest,FrameLossRateTest,BackToBackTest]]:
        v = []
        for test_type_config in values.values():
            if test_type_config.enabled:
                v.append(test_type_config)
        return v
