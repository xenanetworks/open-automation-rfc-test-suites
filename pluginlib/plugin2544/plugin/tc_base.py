import asyncio, time
from typing import Optional, TYPE_CHECKING

from loguru import logger
from pluginlib.plugin2544.model.m_test_type_config import FrameLossRateTest, LatencyTest
from pluginlib.plugin2544.plugin.learning import (
    AddressRefreshHandler,
    add_L3_learning_preamble_steps,
    add_flow_based_learning_preamble_steps,
    add_mac_learning_steps,
    schedule_arp_refresh,
    setup_address_arp_refresh,
)
from pluginlib.plugin2544.plugin.setup_source_port_rates import setup_source_port_rates
from pluginlib.plugin2544.plugin.statistics import (
    FRAME_LOSS_OUTPUT,
    LATENCY_OUTPUT,
    FinalStatistic,
)
from pluginlib.plugin2544.plugin.test_result import aggregate_data
import pluginlib.plugin2544.utils.constants as const

if TYPE_CHECKING:
    from pluginlib.plugin2544.plugin.test_resource import ResourceManager


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

    async def add_learning_steps(self, current_packet_size) -> None:
        await self.resources.stop_traffic()
        await add_L3_learning_preamble_steps(self.resources, current_packet_size)
        await add_mac_learning_steps(self.resources, const.MACLearningMode.EVERYTRIAL)
        await add_flow_based_learning_preamble_steps(
            self.resources, current_packet_size
        )

    async def start_test(self, test_type_conf, current_packet_size):
        await self.add_learning_steps(current_packet_size)
        await setup_source_port_rates(self.resources, current_packet_size)
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
            self.resources.set_rate(rate_percent)
            await self.start_test(test_type_conf, current_packet_size)
            while True:
                start_time = time.time()
                data = await aggregate_data(
                    self.resources,
                    current_packet_size,
                    test_type_conf.common_options.actual_duration,
                    repetition,
                    rate_percent,
                    test_case_type=const.TestType.LATENCY_JITTER,
                    is_final=False,
                )
                logger.info(data.json(include=LATENCY_OUTPUT, indent=2))
                if self.resources.should_quit(
                    start_time, test_type_conf.common_options.actual_duration
                ):
                    break
                await asyncio.sleep(1)
            await asyncio.sleep(3)
            logger.info("final result:")
            data = await aggregate_data(
                self.resources,
                current_packet_size,
                test_type_conf.common_options.actual_duration,
                repetition,
                rate_percent,
                test_case_type=const.TestType.LATENCY_JITTER,
                is_final=True,
            )
            logger.info(data.json(include=LATENCY_OUTPUT, indent=2))
            await self.resources.set_tx_time_limit(0)

    async def frame_loss(
        self, test_type_conf: FrameLossRateTest, current_packet_size, repetition
    ):
        for rate_percent in test_type_conf.rate_sweep_options.rate_sweep_list:
            self.resources.set_rate(rate_percent)
            await self.start_test(test_type_conf, current_packet_size)
            while True:
                start_time = time.time()
                data = await aggregate_data(
                    self.resources,
                    current_packet_size,
                    test_type_conf.common_options.actual_duration,
                    repetition,
                    rate_percent,
                    test_case_type=const.TestType.FRAME_LOSS_RATE,
                    is_final=False,
                )
                logger.info(data.json(include=FRAME_LOSS_OUTPUT, indent=2))
                if self.resources.should_quit(
                    start_time, test_type_conf.common_options.actual_duration
                ):
                    break
                await asyncio.sleep(1)
            await asyncio.sleep(3)
            logger.info("final result:")
            data = await aggregate_data(
                self.resources,
                current_packet_size,
                test_type_conf.common_options.actual_duration,
                repetition,
                rate_percent,
                test_case_type=const.TestType.FRAME_LOSS_RATE,
                is_final=True,
            )
            check_if_frame_loss_success(test_type_conf, data)
            logger.info(data.json(include=FRAME_LOSS_OUTPUT, indent=2))
            await self.resources.set_tx_time_limit(0)


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
