from decimal import Decimal
from typing import List
from pydantic import (
    BaseModel,
    Field,
    validator,
    NonNegativeInt,
    PositiveInt,
)
from ..utils.field import NonNegativeDecimal
from ..utils.constants import (
    PacketSizeType,
    FlowCreationType,
    TidAllocationScope,
    TestTopology,
    TrafficDirection,
    PayloadTypeStr,
    OuterLoopMode,
    MACLearningMode,
    MIXED_DEFAULT_WEIGHTS,
    MIXED_PACKET_SIZE,
)
from ..utils import exceptions


class FrameSizesOptions(BaseModel):
    field_0: NonNegativeInt = Field(56)
    field_1: NonNegativeInt = Field(60)
    field_14: NonNegativeInt = Field(9216)
    field_15: NonNegativeInt = Field(16360)


class FrameSizeConfiguration(BaseModel):
    # FrameSizes
    packet_size_type: PacketSizeType
    # FixedSizesPerTrial
    custom_packet_sizes: List[NonNegativeInt]
    fixed_packet_start_size: NonNegativeInt
    fixed_packet_end_size: NonNegativeInt
    fixed_packet_step_size: PositiveInt
    # VaryingSizesPerTrial
    varying_packet_min_size: NonNegativeInt
    varying_packet_max_size: NonNegativeInt
    mixed_sizes_weights: List[NonNegativeInt] = MIXED_DEFAULT_WEIGHTS
    mixed_length_config: FrameSizesOptions

    # computed properties
    mixed_packet_length: List[int] = MIXED_PACKET_SIZE
    mixed_average_packet_size: Decimal = Decimal("0.0")
    packet_size_list: List[NonNegativeDecimal] = []

    @validator("mixed_sizes_weights", pre=True, always=True)
    def is_mixed_weights_valid(
        cls, v: List[NonNegativeInt], values
    ) -> List[NonNegativeInt]:
        if "packet_size_type" in values:
            if values["packet_size_type"] == PacketSizeType.MIX:
                if not v or len(v) != len(MIXED_DEFAULT_WEIGHTS):
                    raise exceptions.MixWeightsNotEnough()
                sum_of_weights = sum(v)
                if not sum_of_weights == 100:
                    raise exceptions.MixWeightsSumError(sum_of_weights)
        return v

    @validator("mixed_packet_length", pre=True, always=True)
    def set_mix_packet_length(cls, v: List[int], values) -> List[int]:
        mix_size_length_dic = values.get(
            "mixed_length_config", FrameSizesOptions()
        ).dict()
        return [
            MIXED_PACKET_SIZE[index]
            if not (mix_size_length_dic.get(f"field_{index}", 0))
            else mix_size_length_dic.get(f"field_{index}", 0)
            for index in range(len(MIXED_PACKET_SIZE))
        ]

    @validator("mixed_average_packet_size", pre=True, always=True)
    def set_mixed_average_packet_size(cls, v: Decimal, values) -> Decimal:
        if all(
            [
                i in values
                for i in [
                    "packet_size_type",
                    "mixed_length_config",
                    "mixed_sizes_weights",
                    "mixed_packet_length",
                ]
            ]
        ):
            if values["packet_size_type"] == PacketSizeType.MIX:
                weighted_size = 0.0
                for index, size in enumerate(values["mixed_packet_length"]):
                    weight = values["mixed_sizes_weights"][index]
                    weighted_size += size * weight
                v = Decimal(round(weighted_size / 100.0))
        return v

    @validator("packet_size_list", pre=True, always=True)
    def get_packet_sizes(
        cls, v: List[NonNegativeDecimal], values
    ) -> List[NonNegativeDecimal]:
        checked = all(
            {
                t in values
                for t in {
                    "packet_size_type",
                    "custom_packet_sizes",
                    "mixed_average_packet_size",
                    "fixed_packet_start_size",
                    "fixed_packet_end_size",
                    "fixed_packet_step_size",
                    "fixed_packet_step_size",
                    "varying_packet_min_size",
                    "varying_packet_max_size",
                }
            }
        )
        if not checked:
            return v

        packet_size_type = values["packet_size_type"]
        if packet_size_type == PacketSizeType.IETF_DEFAULT:
            return [64, 128, 256, 512, 1024, 1280, 1518]
        elif packet_size_type == PacketSizeType.CUSTOM:
            return list(sorted(values["custom_packet_sizes"]))
        elif packet_size_type == PacketSizeType.MIX:
            return [values["mixed_average_packet_size"]]

        elif packet_size_type == PacketSizeType.RANGE:
            return list(
                range(
                    values["fixed_packet_start_size"],
                    values["fixed_packet_end_size"] + values["fixed_packet_step_size"],
                    values["fixed_packet_step_size"],
                )
            )

        elif packet_size_type in {
            PacketSizeType.INCREMENTING,
            PacketSizeType.BUTTERFLY,
            PacketSizeType.RANDOM,
        }:

            return [
                (values["varying_packet_min_size"] + values["varying_packet_max_size"])
                // 2
            ]
        else:
            raise exceptions.FrameSizeTypeError(packet_size_type)


class MultiStreamConfig(BaseModel):
    enable_multi_stream: bool
    per_port_stream_count: PositiveInt
    multi_stream_address_offset: PositiveInt
    multi_stream_address_increment: PositiveInt
    multi_stream_mac_base_address: str


class TogglePortSyncConfig(BaseModel):
    toggle_port_sync: bool
    sync_off_duration_second: PositiveInt
    delay_after_sync_on_second: PositiveInt


class TestConfiguration(BaseModel):
    # FlowCreation
    flow_creation_type: FlowCreationType
    tid_allocation_scope: TidAllocationScope
    mac_base_address: str
    # PortScheduling
    enable_speed_reduction_sweep: bool
    use_port_sync_start: bool
    port_stagger_steps: NonNegativeInt
    # TestScheduling
    outer_loop_mode: OuterLoopMode
    # MacLearningOptions
    mac_learning_mode: MACLearningMode
    mac_learning_frame_count: PositiveInt
    toggle_port_sync_config: TogglePortSyncConfig
    # L23LearningOptions
    learning_rate_pct: Decimal
    learning_duration_second: PositiveInt
    # FlowBasedLearningOptions
    use_flow_based_learning_preamble: bool
    flow_based_learning_frame_count: PositiveInt
    delay_after_flow_based_learning_ms: int = Field(..., ge=50)
    # ArpNdpOptions
    arp_refresh_enabled: bool
    arp_refresh_period_second: NonNegativeDecimal = NonNegativeDecimal(4000)
    use_gateway_mac_as_dmac: bool
    # ResetAndErrorHandling
    should_stop_on_los: bool
    delay_after_port_reset_second: PositiveInt
    # OverallTestTopology
    topology: TestTopology
    direction: TrafficDirection

    frame_sizes: FrameSizeConfiguration
    # FrameTestPayload
    use_micro_tpld_on_demand: bool

    # payload_definition PayloadDefinition
    payload_type: PayloadTypeStr
    payload_pattern: str  # full number string

    # MultiStreamConfiguration
    multi_stream_config: MultiStreamConfig

    @validator("payload_pattern", always=True, pre=True)
    def payload_type_str_list(cls, v: str) -> str:
        if v.startswith("0x") or v.startswith("0X"):
            return v
        else:
            return "".join(
                [hex(int(i)).replace("0x", "").zfill(2) for i in v.split(",")]
            )

    @validator("multi_stream_config")
    def validate_multi_stream(cls, v: MultiStreamConfig, values) -> MultiStreamConfig:
        if "flow_creation_type" not in values:
            return v
        if not values["flow_creation_type"].is_stream_based and v.enable_multi_stream:
            raise exceptions.ModifierBasedNotSupportMultiStream()
        return v
