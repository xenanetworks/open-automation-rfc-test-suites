from xoa_core.types import PluginAbstract
from typing import TYPE_CHECKING, Iterator, List, Tuple
from decimal import getcontext
from pluginlib.plugin2544.plugin.tc_base import TestCaseProcessor
from pluginlib.plugin2544.plugin.test_resource import ResourceManager
from pluginlib.plugin2544.utils.field import NonNegativeDecimal

if TYPE_CHECKING:
    from .dataset import PluginModel2544
from .plugin.test_result_structure import TestCaseResult
from .utils.logger import logger
# from .plugin.common import setup_macaddress, TPLDControl
# from .plugin.outer_loop import gen_loop, test_run

getcontext().prec = 12
from xoa_driver.testers import L23Tester

class TestSuit2544(PluginAbstract["PluginModel2544"]):
    def prepare(self) -> None:
        self.tpld_id = 0
        self.mac_learned = False
        self.iteration: int = 1
        self.test_conf = self.cfg.test_configuration
        self.test_case_result = TestCaseResult()
        self.recources = ResourceManager(
            self.testers,
            list(self.cfg.ports_configuration.values()),
            self.port_identities,
            self.cfg.test_configuration,
            self.xoa_out,
        )
        return super().prepare()

    # async def __configure_resource(self) -> None:
    #     setup_packet_header(self.stream_lists)
    #     await create_source_stream(self.stream_lists, self.test_conf)

    async def __prepare_data(self) -> None:
        await self.recources.init_resource(
            self.cfg.test_types_configuration.latency_test.latency_mode,
        )
        # self.stream_lists = configure_source_streams(
        #     self.control_ports, self.tpld_controller, self.test_conf
        # )  # SetupSourceStreams -- order rebuild

    async def __pre_test(self) -> None:
        await self.__prepare_data()
        # await self.__configure_resource()
    def gen_loop(self, type_conf
    ) -> Iterator[Tuple[int, NonNegativeDecimal]]:
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
        tc = TestCaseProcessor(self.recources)
        while True:

            for type_conf in self.cfg.test_types_configuration.available_test:
                # if isinstance(type_conf, LatencyTest):
    #                 await setup_latency_mode(self.control_ports, type_conf.latency_mode)
                for iteration, current_packet_size in self.gen_loop(
                    type_conf
                    # self.xoa_out,
                ):
                    await self.state_conditions.wait_if_paused()
                    await self.state_conditions.stop_if_stopped()
                    await tc.latency(type_conf, current_packet_size, iteration)
    #                 await test_run(
    #                     self.stream_lists,
    #                     self.control_ports,
    #                     type_conf,
    #                     self.cfg.test_configuration,
    #                     self.cfg.has_l3,
    #                     current_packet_size,
    #                     iteration,
    #                     self.test_case_result,
    #                     self.xoa_out,
    #                 )
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
