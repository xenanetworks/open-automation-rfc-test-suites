import asyncio, time
import math
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING

from loguru import logger

from pluginlib.plugin2544.plugin.tc_back_to_back import BackToBackBoutEntry
from ..model.m_test_type_config import (
    BackToBackTest,
    FrameLossRateTest,
    LatencyTest,
    ThroughputTest,
)
from .learning import (
    AddressRefreshHandler,
    add_L3_learning_preamble_steps,
    add_flow_based_learning_preamble_steps,
    add_mac_learning_steps,
    schedule_arp_refresh,
    setup_address_arp_refresh,
)
from .setup_source_port_rates import setup_source_port_rates
from .statistics import (
    FRAME_LOSS_OUTPUT,
    LATENCY_OUTPUT,
    THROUGHPUT_COMMON,
    THROUGHPUT_PER_PORT,
    FinalStatistic,
    StatisticParams,
)
from .tc_throughput import get_initial_boundaries
from .test_result import aggregate_data
from ..utils import constants as const

if TYPE_CHECKING:
    from .test_resource import ResourceManager


class TestCaseProcessor:
    def __init__(self, resources: "ResourceManager"):
        self.resources: "ResourceManager" = resources
        self.address_refresh_handler: Optional[AddressRefreshHandler] = None

    async def prepare(self) -> None:
        if not self.resources.test_conf.arp_refresh_enabled:
            return None
        if self.resources.has_l3:
            return None
        self.address_refresh_handler = await setup_address_arp_refresh(self.resources)

    async def add_learning_steps(self, current_packet_size: Decimal) -> None:
        await self.resources.stop_traffic()
        await add_L3_learning_preamble_steps(self.resources, current_packet_size)
        await add_mac_learning_steps(self.resources, const.MACLearningMode.EVERYTRIAL)
        await add_flow_based_learning_preamble_steps(
            self.resources, current_packet_size
        )

    async def start_test(self, test_type_conf, current_packet_size: Decimal):
        await setup_source_port_rates(self.resources, current_packet_size)
        if test_type_conf.common_options.duration_type.is_time_duration:
            await self.resources.set_tx_time_limit(
                test_type_conf.common_options.actual_duration * 1_000_000
            )

        await self.resources.clear_statistic()
        await self.resources.start_traffic(self.resources.test_conf.use_port_sync_start)
        await schedule_arp_refresh(self.resources, self.address_refresh_handler)

    async def latency(
        self, test_type_conf: LatencyTest, current_packet_size, repetition
    ):
        for rate_percent in test_type_conf.rate_sweep_options.rate_sweep_list:
            params = StatisticParams(
                test_case_type=const.TestType.LATENCY_JITTER,
                rate_percent=rate_percent,
                frame_size=current_packet_size,
                repetition=repetition,
                duration=test_type_conf.common_options.actual_duration,
            )
            self.resources.set_rate(rate_percent)
            await self.add_learning_steps(current_packet_size)
            await self.start_test(test_type_conf, current_packet_size)
            result = await self.collect(params, LATENCY_OUTPUT)
            await self.resources.set_tx_time_limit(0)

    async def frame_loss(
        self, test_type_conf: FrameLossRateTest, current_packet_size, repetition
    ):
        for rate_percent in test_type_conf.rate_sweep_options.rate_sweep_list:
            self.resources.set_rate(rate_percent)
            await self.add_learning_steps(current_packet_size)
            await self.start_test(test_type_conf, current_packet_size)
            params = StatisticParams(
                test_case_type=const.TestType.FRAME_LOSS_RATE,
                rate_percent=rate_percent,
                frame_size=current_packet_size,
                repetition=repetition,
                duration=test_type_conf.common_options.actual_duration,
            )
            result = await self.collect(params, FRAME_LOSS_OUTPUT)
            await self.resources.set_tx_time_limit(0)

    async def collect(
        self, params: StatisticParams, data_format=None
    ) -> FinalStatistic:
        while True:
            start_time = time.time()
            data = await aggregate_data(
                self.resources,
                params,
                is_final=False,
            )
            # logger.info(data.json(include=data_format, indent=2))
            if self.resources.should_quit(start_time, params.duration):
                break
            await asyncio.sleep(1)
        await asyncio.sleep(3)
        logger.info("final result:")
        data = await aggregate_data(
            self.resources,
            params,
            is_final=True,
        )
        logger.info(data.json(include=data_format, indent=2))
        return data

    async def throughput(
        self, test_type_conf: ThroughputTest, current_packet_size, repetition
    ):
        await self.add_learning_steps(current_packet_size)
        result = None
        test_passed = False
        boundaries = get_initial_boundaries(test_type_conf, self.resources)
        params = StatisticParams(
            test_case_type=const.TestType.THROUGHPUT,
            frame_size=current_packet_size,
            repetition=repetition,
            duration=test_type_conf.common_options.actual_duration,
        )
        data_format = (
            THROUGHPUT_PER_PORT
            if test_type_conf.rate_iteration_options.result_scope.is_per_source_port
            else THROUGHPUT_COMMON
        )
        while True:
            [boundary.update_boundary(result) for boundary in boundaries]
            should_continue = any(
                [boundary.port_should_continue for boundary in boundaries]
            )
            if not should_continue:
                break
            [boundary.update_rate() for boundary in boundaries]
            params.rate_percent = boundaries[0].rate
            test_passed = all([boundary.port_test_passed for boundary in boundaries])
            await self.start_test(test_type_conf, current_packet_size)
            result = await self.collect(params, data_format)
            await self.resources.set_tx_time_limit(0)
        if not test_type_conf.rate_iteration_options.result_scope.is_per_source_port:
            final = boundaries[0].best_final_result
        else:
            for port_struct in self.resources.port_structs:
                port_struct.init_counter(
                    params.frame_size, params.duration, is_final=True
                )
            for port_struct in self.resources.port_structs:
                for stream_struct in port_struct.stream_structs:
                    stream_struct.aggregate()
                port_struct.statistic.calculate_rate()
            final = FinalStatistic(
                test_case_type=params.test_case_type,
                is_final=True,
                frame_size=params.frame_size,
                repetition=params.repetition,
                tx_rate_percent=params.rate_percent,
                port_data=[
                    port_struct.statistic for port_struct in self.resources.port_structs
                ],
                # stream_data=aggregate_stream_result(resource),
            )
        final.set_result_state(
            const.ResultState.SUCCESS if test_passed else const.ResultState.FAIL
        )
        logger.info(final)

    async def back_to_back(
        self, test_type_conf: BackToBackTest, current_packet_size, repetition
    ) -> None:
        await self.add_learning_steps(current_packet_size)
        for rate_percent in test_type_conf.rate_sweep_options.rate_sweep_list:
            params = StatisticParams(
                test_case_type=const.TestType.BACK_TO_BACK,
                rate_percent=rate_percent,
                frame_size=current_packet_size,
                repetition=repetition,
                duration=test_type_conf.common_options.actual_duration,
            )
            self.resources.set_rate(rate_percent)
            boundaries = [
                BackToBackBoutEntry(test_type_conf, port_struct, current_packet_size)
                for port_struct in self.resources.port_structs
            ]
            while True:
                [boundary.check_boundaries() for boundary in boundaries]
                should_continue = any(
                    [boundary.port_should_continue for boundary in boundaries]
                )
                if not should_continue:
                    break
                await self.setup_packet_limit(boundaries)
                await self.start_test(test_type_conf, current_packet_size)
                result = await self.collect(params)

    async def setup_packet_limit(self, boundaries: List[BackToBackBoutEntry]):
        for port_index, port_struct in enumerate(self.resources.port_structs):
            for peer_struct in port_struct.properties.peers:
                stream_info_list = [
                    stream_info
                    for stream_info in port_struct.stream_structs
                    if stream_info.is_rx_port(peer_struct)
                ]  # select same tx and rx port stream
                port_stream_count = len(port_struct.properties.peers) * len(
                    stream_info_list
                )
                total_frame_count = boundaries[port_index].current
                stream_burst = Decimal(str(total_frame_count)) / Decimal(
                    str(port_stream_count)
                )
                await asyncio.gather(
                    *[
                        stream_struct.set_frame_limit(math.floor(stream_burst))
                        for stream_struct in stream_info_list
                    ]
                )


def check_if_frame_loss_success(
    frame_loss_conf: "FrameLossRateTest", result: FinalStatistic
) -> None:
    result.set_result_state(const.ResultState.SUCCESS)
    if frame_loss_conf.use_pass_fail_criteria:
        if frame_loss_conf.acceptable_loss_type == const.AcceptableLossType.PERCENT:
            if result.total.rx_loss_percent > frame_loss_conf.acceptable_loss_pct:
                result.set_result_state(const.ResultState.FAIL)
        else:
            if result.total.rx_loss_frames > frame_loss_conf.acceptable_loss_pct:
                result.set_result_state(const.ResultState.FAIL)
