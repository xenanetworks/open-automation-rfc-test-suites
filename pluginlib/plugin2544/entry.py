from xoa_core.types import PluginAbstract
from typing import TYPE_CHECKING, Iterator, List, Tuple
from decimal import getcontext
from pluginlib.plugin2544.plugin.tc_base import TestCaseProcessor
from pluginlib.plugin2544.plugin.test_resource import ResourceManager
from pluginlib.plugin2544.utils import constants as const
from pluginlib.plugin2544.utils.field import NonNegativeDecimal

if TYPE_CHECKING:
    from .dataset import PluginModel2544
from .plugin.test_result_structure import TestCaseResult
from .utils.logger import logger

getcontext().prec = 12


class TestSuit2544(PluginAbstract["PluginModel2544"]):
    def prepare(self) -> None:
        self.tpld_id = 0
        self.mac_learned = False
        self.iteration: int = 1
        self.test_conf = self.cfg.test_configuration
        self.test_case_result = TestCaseResult()
        self.resources = ResourceManager(
            self.testers,
            list(self.cfg.ports_configuration.values()),
            self.port_identities,
            self.cfg.test_configuration,
            self.xoa_out,
        )
        return super().prepare()

    async def __prepare_data(self) -> None:
        await self.resources.init_resource(
            self.cfg.test_types_configuration.latency_test.latency_mode,
        )


    async def __pre_test(self) -> None:
        await self.__prepare_data()

    def gen_loop(self, type_conf) -> Iterator[Tuple[int, NonNegativeDecimal]]:
        max_iteration = type_conf.common_options.iterations
        packet_size_list = self.test_conf.frame_sizes.packet_size_list
        if self.test_conf.outer_loop_mode.is_iteration:
            for iteration in range(1, max_iteration + 1):
                for current_packet_size in packet_size_list:
                    yield iteration, current_packet_size
            # result_handler = test_case_result.get_result_handler(type_conf.test_type)
            # avg_result(result_handler, max_iteration, type_conf, xoa_out)
        else:
            for current_packet_size in packet_size_list:
                for iteration in range(1, max_iteration + 1):
                    yield iteration, current_packet_size
                # result_handler = test_case_result.get_result_handler(type_conf.test_type)
                # avg_result(
                #     result_handler, max_iteration, type_conf, xoa_out, current_packet_size
                # )

    async def __do_test(self) -> None:
        tc = TestCaseProcessor(self.resources)
        while True:

            for type_conf in self.cfg.test_types_configuration.available_test:

                for iteration, current_packet_size in self.gen_loop(
                    type_conf
                ):
                    await self.state_conditions.wait_if_paused()
                    await self.state_conditions.stop_if_stopped()
                    await self.resources.setup_packet_size(current_packet_size)
                    if type_conf.test_type == const.TestType.THROUGHPUT:
                        pass
                    elif type_conf.test_type == const.TestType.LATENCY_JITTER:
                        await tc.latency(type_conf, current_packet_size, iteration) # type:ignore
                    elif type_conf.test_type == const.TestType.FRAME_LOSS_RATE:
                        await tc.frame_loss(type_conf, current_packet_size, iteration) # type:ignore
                    elif type_conf.test_type == const.TestType.BACK_TO_BACK:
                        pass

            if not self.cfg.test_configuration.repeat_test_until_stopped:
                break

    async def __post_test(self) -> None:
        logger.info("test finish")
        # TODO: wait for callback exception catch
        # await asyncio.gather(*[port_struct.clear() for port_struct in self.control_ports])

    async def start(self) -> None:
        try:
            await self.__pre_test()
            await self.__do_test()
            await self.__post_test()
        # except [exceptions.LossofPortOwnership, exceptions.LossofTester]:
        #     pass
        except Exception as e:
            logger.exception(e)
            raise e
