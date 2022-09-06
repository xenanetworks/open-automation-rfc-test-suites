from xoa_core.types import PluginAbstract
from typing import TYPE_CHECKING, Generator, Tuple
from decimal import getcontext

from .plugin.config_checkers import check_test_type_config
from .plugin.tc_base import TestCaseProcessor
from .plugin.test_resource import ResourceManager
from .utils import constants as const
from .utils.field import NonNegativeDecimal

if TYPE_CHECKING:
    from .dataset import PluginModel2544
from .utils.logger import logger

getcontext().prec = 12


class TestSuite2544(PluginAbstract["PluginModel2544"]):
    def prepare(self) -> None:
        self.tpld_id = 0
        self.mac_learned = False
        self.iteration: int = 1
        self.test_conf = self.cfg.test_configuration
        self.resources = ResourceManager(
            self.testers,
            list(self.cfg.ports_configuration.values()),
            self.port_identities,
            self.cfg.test_configuration,
            self.xoa_out,
        )

    async def __pre_test(self) -> None:
        check_test_type_config(self.cfg.test_types_configuration.available_test)
        await self.resources.init_resource(
            self.cfg.test_types_configuration.latency_test.latency_mode,
        )

    def gen_loop(
        self, type_conf
    ) -> Generator[Tuple[int, NonNegativeDecimal], None, None]:
        max_iteration = type_conf.common_options.iterations
        packet_size_list = self.test_conf.frame_sizes.packet_size_list
        if self.test_conf.outer_loop_mode.is_iteration:
            for iteration in range(1, max_iteration + 1):
                for current_packet_size in packet_size_list:
                    yield iteration, NonNegativeDecimal(current_packet_size)
        else:
            for current_packet_size in packet_size_list:
                for iteration in range(1, max_iteration + 1):
                    yield iteration, NonNegativeDecimal(current_packet_size)

    async def __do_test(self) -> None:
        tc = TestCaseProcessor(self.resources, self.xoa_out)
        await tc.prepare()
        while True:
            for type_conf in self.cfg.test_types_configuration.available_test:
                for iteration, current_packet_size in self.gen_loop(type_conf):
                    await self.state_conditions.wait_if_paused()
                    await self.state_conditions.stop_if_stopped()
                    await self.resources.setup_packet_size(current_packet_size)
                    await tc.run(type_conf, current_packet_size, iteration)
                    if (
                        not self.test_conf.outer_loop_mode.is_iteration
                        and type_conf.common_options.iterations > 1
                        and iteration == type_conf.common_options.iterations
                    ):
                        tc.cal_average(type_conf, current_packet_size)
                if (
                    self.test_conf.outer_loop_mode.is_iteration
                    and type_conf.common_options.iterations > 1
                ):
                    tc.cal_average(type_conf)

            if not self.cfg.test_configuration.repeat_test_until_stopped:
                break

    async def __post_test(self) -> None:
        logger.info("test finish")
        # TODO: wait for callback exception catch
        # await asyncio.gather(*[port_struct.clear() for port_struct in self.control_ports])

    async def start(self) -> None:
        await self.__pre_test()
        await self.__do_test()
        await self.__post_test()


