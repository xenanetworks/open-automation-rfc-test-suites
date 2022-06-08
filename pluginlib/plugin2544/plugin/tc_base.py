import asyncio, time
from typing import Optional, TYPE_CHECKING

from loguru import logger
from pluginlib.plugin2544.model.m_test_type_config import LatencyTest
from pluginlib.plugin2544.plugin.learning import (
    AddressRefreshHandler,
    add_L3_learning_preamble_steps,
    add_flow_based_learning_preamble_steps,
    add_mac_learning_steps,
    schedule_arp_refresh,
    setup_address_arp_refresh,
)
from pluginlib.plugin2544.plugin.setup_source_port_rates import setup_source_port_rates
from pluginlib.plugin2544.plugin.test_result import aggregate_latency_data
from pluginlib.plugin2544.utils.constants import MACLearningMode

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
        await add_L3_learning_preamble_steps(self.resources, current_packet_size)
        await add_mac_learning_steps(self.resources, MACLearningMode.EVERYTRIAL)
        await add_flow_based_learning_preamble_steps(
            self.resources, current_packet_size
        )

    async def latency(
        self, test_type_conf: LatencyTest, current_packet_size, repetition
    ):
        logger.info(f"packet size: {current_packet_size}")
        for k, rate_percent in enumerate(
            test_type_conf.rate_sweep_options.rate_sweep_list
        ):
            logger.info(f"rate: {rate_percent}")
            self.resources.set_rate(rate_percent)
            await self.resources.stop_traffic()
            await self.add_learning_steps(current_packet_size)
            await setup_source_port_rates(self.resources, current_packet_size)
            await self.resources.set_tx_time_limit(
                test_type_conf.common_options.actual_duration * 1_000_000
            )
            await self.resources.clear_statistic()
            await self.resources.start_traffic(
                self.resources.test_conf.use_port_sync_start
            )
            await schedule_arp_refresh(self.resources, self.address_refresh_handler)
            while True:
                start_time = time.time()
                await self.resources.collect(
                    current_packet_size,
                    test_type_conf.common_options.duration,
                    is_final=True,
                )
                data = aggregate_latency_data(
                    self.resources,
                    current_packet_size,
                    repetition,
                    rate_percent,
                    is_final=False,
                )
                logger.info(data.json(indent=2))
                if self.resources.should_quit(
                    start_time, test_type_conf.common_options.actual_duration
                ):
                    break
                await asyncio.sleep(1)
            await asyncio.sleep(2)
            logger.info("final result:")
            await self.resources.collect(
                current_packet_size,
                test_type_conf.common_options.duration,
                is_final=True,
            )
            data = aggregate_latency_data(
                self.resources,
                current_packet_size,
                repetition,
                rate_percent,
                is_final=True,
            )
            logger.info(data.json(indent=2))
            await self.resources.set_tx_time_limit(0)
