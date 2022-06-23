import asyncio, time
from copy import deepcopy
import math
from decimal import Decimal
from typing import Dict, List, Optional, TYPE_CHECKING, Tuple
from loguru import logger
from .tc_back_to_back import BackToBackBoutEntry
from ..model.m_test_type_config import (
    AllTestType,
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
    FinalStatistic,
    StatisticParams,
)
from .tc_throughput import get_initial_boundaries
from .test_result import aggregate_data
from ..utils import constants as const

if TYPE_CHECKING:
    from .test_resource import ResourceManager
    from ..utils.logger import TestSuitPipe


class TestCaseProcessor:
    def __init__(self, resources: "ResourceManager", xoa_out: "TestSuitPipe"):
        self.resources: "ResourceManager" = resources
        self.xoa_out = xoa_out
        self.address_refresh_handler: Optional[AddressRefreshHandler] = None
        self.test_results = {}
        self._throughput_map = {}

    async def prepare(self) -> None:
        if not self.resources.test_conf.arp_refresh_enabled:
            return None
        if self.resources.has_l3:
            return None
        self.address_refresh_handler = await setup_address_arp_refresh(self.resources)

    async def run(
        self, test_type_conf: AllTestType, current_packet_size: Decimal, iteration: int
    ) -> None:
        if isinstance(test_type_conf, ThroughputTest):
            await self._throughput(test_type_conf, current_packet_size, iteration)
        elif isinstance(test_type_conf, LatencyTest):
            await self._latency(
                test_type_conf, current_packet_size, iteration
            )  # type:ignore
        elif isinstance(test_type_conf, FrameLossRateTest):
            await self._frame_loss(
                test_type_conf, current_packet_size, iteration
            )  # type:ignore
        elif isinstance(test_type_conf, BackToBackTest):
            await self._back_to_back(test_type_conf, current_packet_size, iteration)

    async def add_learning_steps(self, current_packet_size: Decimal) -> None:
        await self.resources.stop_traffic()
        await add_L3_learning_preamble_steps(self.resources, current_packet_size)
        await add_mac_learning_steps(self.resources, const.MACLearningMode.EVERYTRIAL)
        await add_flow_based_learning_preamble_steps(
            self.resources, current_packet_size
        )

    async def start_test(
        self, test_type_conf: "AllTestType", current_packet_size: Decimal
    ) -> None:
        await setup_source_port_rates(self.resources, current_packet_size)
        if test_type_conf.common_options.duration_type.is_time_duration:
            await self.resources.set_tx_time_limit(
                test_type_conf.common_options.actual_duration * 1_000_000
            )

        await self.resources.clear_statistic()
        await self.resources.start_traffic(self.resources.test_conf.use_port_sync_start)
        await schedule_arp_refresh(self.resources, self.address_refresh_handler)

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
            self.xoa_out.send_statistics(data.json(include=data_format))
            if self.resources.should_quit(start_time, params.duration):
                break
            await asyncio.sleep(1)
        await asyncio.sleep(3)
        data = await aggregate_data(
            self.resources,
            params,
            is_final=True,
        )
        return data

    async def _latency(
        self, test_type_conf: LatencyTest, current_packet_size: Decimal, repetition: int
    ):
        factor = Decimal(100)
        if (
            test_type_conf.use_relative_to_throughput
            and self._throughput_map
        ):
            factor = self._throughput_map.get(current_packet_size)  or factor 
        for rate_percent in test_type_conf.rate_sweep_options.rate_sweep_list:
            tx_rate_nomial_percent = rate_percent
            rate_percent = rate_percent * factor / Decimal(100)
            params = StatisticParams(
                test_case_type=test_type_conf.test_type,
                rate_percent=rate_percent,
                frame_size=current_packet_size,
                repetition=repetition,
                duration=test_type_conf.common_options.actual_duration,
            )
            self.resources.set_rate(rate_percent)
            await self.add_learning_steps(current_packet_size)
            await self.start_test(test_type_conf, current_packet_size)
            result = await self.collect(params, test_type_conf.format)
            await self.resources.set_tx_time_limit(0)
            result.tx_rate_nomial_percent = tx_rate_nomial_percent
            self._add_result(True, test_type_conf.format, result)

    async def _frame_loss(
        self, test_type_conf: FrameLossRateTest, current_packet_size, repetition
    ):
        for rate_percent in test_type_conf.rate_sweep_options.rate_sweep_list:
            self.resources.set_rate(rate_percent)
            await self.add_learning_steps(current_packet_size)
            await self.start_test(test_type_conf, current_packet_size)
            params = StatisticParams(
                test_case_type=test_type_conf.test_type,
                rate_percent=rate_percent,
                frame_size=current_packet_size,
                repetition=repetition,
                duration=test_type_conf.common_options.actual_duration,
            )
            result = await self.collect(params, test_type_conf.format)
            await self.resources.set_tx_time_limit(0)
            is_test_passed = check_if_frame_loss_success(test_type_conf, result)
            self._add_result(is_test_passed, test_type_conf.format, result)

    async def _throughput(
        self, test_type_conf: ThroughputTest, current_packet_size, repetition
    ):
        await self.add_learning_steps(current_packet_size)
        result = None
        test_passed = False
        boundaries = get_initial_boundaries(test_type_conf, self.resources)
        params = StatisticParams(
            test_case_type=test_type_conf.test_type,
            frame_size=current_packet_size,
            repetition=repetition,
            duration=test_type_conf.common_options.actual_duration,
        )
        while True:
            for boundary in boundaries:
                boundary.update_boundary(result)
            should_continue = any(
                boundary.port_should_continue for boundary in boundaries
            )
            test_passed = all(boundary.port_test_passed for boundary in boundaries)
            if not should_continue:
                break
            for boundary in boundaries:
                boundary.update_rate()
            params.rate_percent = boundaries[0].rate
            await self.start_test(test_type_conf, current_packet_size)
            result = await self.collect(params, test_type_conf.format)
            await self.resources.set_tx_time_limit(0)
        if not test_type_conf.rate_iteration_options.result_scope.is_per_source_port:
            final = boundaries[0].best_final_result
        else:
            # Step 1: initial counter
            for port_struct in self.resources.port_structs:
                port_struct.init_counter(
                    params.frame_size, params.duration, is_final=True
                )
            # Step 2: aggregate counter
            for port_struct in self.resources.port_structs:
                for stream_struct in port_struct.stream_structs:
                    stream_struct.aggregate()
            # Step 3: calculate rate
            for port_struct in self.resources.port_structs:
                port_struct.statistic.calculate_rate()
            # can't merge these three steps above.

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
        self._set_throughput_for_frame_size(final.frame_size, final.tx_rate_percent)
        self._add_result(test_passed, test_type_conf.format, final)

    async def _back_to_back(
        self, test_type_conf: BackToBackTest, current_packet_size, repetition
    ) -> None:
        result = None
        await self.add_learning_steps(current_packet_size)
        for rate_percent in test_type_conf.rate_sweep_options.rate_sweep_list:
            params = StatisticParams(
                test_case_type=test_type_conf.test_type,
                rate_percent=rate_percent,
                frame_size=current_packet_size,
                repetition=repetition,
                duration=test_type_conf.common_options.actual_duration,
            )
            self.resources.set_rate(rate_percent)
            boundaries = [
                BackToBackBoutEntry(
                    test_type_conf, port_struct, current_packet_size, rate_percent
                )
                for port_struct in self.resources.port_structs
            ]
            while True:
                for boundary in boundaries:
                    boundary.update_boundaries()
                if not any(boundary.port_should_continue for boundary in boundaries):
                    break
                await self._setup_packet_limit(boundaries)
                await self.start_test(test_type_conf, current_packet_size)
                result = await self.collect(params, test_type_conf.format)
            self._add_result(
                all(boundary.port_test_passed for boundary in boundaries),
                test_type_conf.format,
                result,
            )

    def _set_throughput_for_frame_size(self, frame_size: Decimal, rate: Decimal):
        if frame_size not in self._throughput_map:
            self._throughput_map[frame_size] = 0
        self._throughput_map[frame_size] = max(rate, self._throughput_map[frame_size])

    def _average_per_frame_size(
        self, test_type_conf: AllTestType, frame_size: Decimal
    ) -> None:
        result = self.test_results[test_type_conf.test_type][frame_size]
        for rate_percent, statistic_lists in result.items():
            final: Optional[FinalStatistic] = None
            for statistic in statistic_lists:
                if not final:
                    final = deepcopy(statistic)

                else:
                    final.sum(statistic)
            if final:
                final.repetition = "avg"
                final.avg(len(statistic_lists))
                result[rate_percent].append(final)
                logger.info(final.json(include=test_type_conf.format, indent=2))

    def cal_average(
        self, test_type_conf: AllTestType, frame_size: Optional[Decimal] = None
    ) -> None:
        if frame_size:
            result = self.test_results[test_type_conf.test_type][frame_size]
            self._average_per_frame_size(test_type_conf, frame_size)
        else:
            result = self.test_results[test_type_conf.test_type]
            for frame_size in result.keys():
                self._average_per_frame_size(test_type_conf, frame_size)

    def _add_result(
        self, is_test_passed: bool, data_format: Dict, result: Optional[FinalStatistic]
    ) -> None:
        if not (result and result.is_final):
            return
        if is_test_passed:
            result.set_result_state(const.ResultState.SUCCESS)
        else:
            result.set_result_state(const.ResultState.FAIL)
        if result.test_case_type not in self.test_results:
            self.test_results[result.test_case_type] = {}
        if result.frame_size not in self.test_results[result.test_case_type]:
            self.test_results[result.test_case_type][result.frame_size] = {}
        if (
            result.tx_rate_percent
            not in self.test_results[result.test_case_type][result.frame_size]
        ):
            self.test_results[result.test_case_type][result.frame_size][
                result.tx_rate_percent
            ] = []
        self.test_results[result.test_case_type][result.frame_size][
            result.tx_rate_percent
        ].append(result)
        res = result.json(include=data_format, indent=2)
        self.xoa_out.send_statistics(res)
        logger.info(res)

    async def _setup_packet_limit(self, boundaries: List[BackToBackBoutEntry]) -> None:
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
) -> bool:
    is_test_passed = True
    if frame_loss_conf.use_pass_fail_criteria:
        if frame_loss_conf.acceptable_loss_type == const.AcceptableLossType.PERCENT:
            if result.total.rx_loss_percent > frame_loss_conf.acceptable_loss_pct:
                is_test_passed = False
        else:
            if result.total.rx_loss_frames > frame_loss_conf.acceptable_loss_pct:
                is_test_passed = False
    return is_test_passed
