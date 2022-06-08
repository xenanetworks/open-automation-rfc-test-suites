from decimal import Decimal
from typing import Iterable, List, Tuple
from pydantic import (
    BaseModel,
    Field,
    validator,
    NonNegativeInt,
    PositiveInt,
)
from ..utils.field import NonNegativeDecimal

from ..utils import exceptions
from pluginlib.plugin2544.utils import constants as const


class FrameSizesOptions(BaseModel):
    field_0: NonNegativeInt = Field(56)
    field_1: NonNegativeInt = Field(60)
    field_14: NonNegativeInt = Field(9216)
    field_15: NonNegativeInt = Field(16360)


class FrameSizeConfiguration(BaseModel):
    # FrameSizes
    packet_size_type: const.PacketSizeType
    # FixedSizesPerTrial
    custom_packet_sizes: List[NonNegativeInt]
    fixed_packet_start_size: NonNegativeInt
    fixed_packet_end_size: NonNegativeInt
    fixed_packet_step_size: PositiveInt
    # VaryingSizesPerTrial
    varying_packet_min_size: NonNegativeInt
    varying_packet_max_size: NonNegativeInt
    mixed_length_config: FrameSizesOptions
    mixed_sizes_weights: List[NonNegativeInt] = const.MIXED_DEFAULT_WEIGHTS


    @validator("mixed_sizes_weights", pre=True, always=True)
    def is_mixed_weights_valid(
        cls, v: List[NonNegativeInt], values
    ) -> List[NonNegativeInt]:
        if "packet_size_type" in values:
            if values["packet_size_type"] == const.PacketSizeType.MIX:
                if not v or len(v) != len(const.MIXED_DEFAULT_WEIGHTS):
                    raise exceptions.MixWeightsNotEnough()
                sum_of_weights = sum(v)
                if not sum_of_weights == 100:
                    raise exceptions.MixWeightsSumError(sum_of_weights)
        return v

    @property
    def mixed_packet_length(self) -> List[int]:
        mix_size_length_dic = self.mixed_length_config.dict()
        return [
            const.MIXED_PACKET_SIZE[index]
            if not (mix_size_length_dic.get(f"field_{index}", 0))
            else mix_size_length_dic.get(f"field_{index}", 0)
            for index in range(len(const.MIXED_PACKET_SIZE))
        ]

    @property
    def mixed_average_packet_size(self) -> int:
        weighted_size = 0.0
        for index, size in enumerate(self.mixed_packet_length):
            weight = self.mixed_sizes_weights[index]
            weighted_size += size * weight
        return int(round(weighted_size / 100.0))

    @property
    def packet_size_list(self) -> Iterable[int]:
        packet_size_type = self.packet_size_type
        if packet_size_type == const.PacketSizeType.IETF_DEFAULT:
            return const.DEFAULT_PACKET_SIZE_LIST
        elif packet_size_type == const.PacketSizeType.CUSTOM:
            return list(sorted(self.custom_packet_sizes))
        elif packet_size_type == const.PacketSizeType.MIX:
            return [self.mixed_average_packet_size]

        elif packet_size_type == const.PacketSizeType.RANGE:
            return range(
                self.fixed_packet_start_size,
                self.fixed_packet_end_size + self.fixed_packet_step_size,
                self.fixed_packet_step_size,
            )

        elif packet_size_type in {
            const.PacketSizeType.INCREMENTING,
            const.PacketSizeType.BUTTERFLY,
            const.PacketSizeType.RANDOM,
        }:

            return [
                (self.varying_packet_min_size + self.varying_packet_max_size)
                // 2
            ]
        else:
            raise exceptions.FrameSizeTypeError(packet_size_type.value)


    @property
    def size_range(self) -> Tuple[int, int]:
        if (
            self.packet_size_type in [const.PacketSizeType.INCREMENTING,
            const.PacketSizeType.RANDOM,
            const.PacketSizeType.BUTTERFLY]
        ):
            min_size = self.varying_packet_min_size
            max_size = self.varying_packet_max_size
        else:
            # Packet length is useless when mixed
            min_size = max_size = int(self.mixed_average_packet_size)
        return (min_size, max_size)


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
    flow_creation_type: const.FlowCreationType
    tid_allocation_scope: const.TidAllocationScope
    mac_base_address: str
    # PortScheduling
    enable_speed_reduction_sweep: bool
    use_port_sync_start: bool
    port_stagger_steps: NonNegativeInt
    # TestScheduling
    outer_loop_mode: const.OuterLoopMode
    # MacLearningOptions
    mac_learning_mode: const.MACLearningMode
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
    topology: const.TestTopology
    direction: const.TrafficDirection

    frame_sizes: FrameSizeConfiguration
    # FrameTestPayload
    use_micro_tpld_on_demand: bool

    # payload_definition PayloadDefinition
    payload_type: const.PayloadTypeStr
    payload_pattern: str  # full number string

    # MultiStreamConfiguration
    multi_stream_config: MultiStreamConfig
    repeat_test_until_stopped: bool = False

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
