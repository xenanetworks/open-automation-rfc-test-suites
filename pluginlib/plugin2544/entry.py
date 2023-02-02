from xoa_core.types import PluginAbstract
from typing import TYPE_CHECKING, Generator, Tuple, List

from .plugin.config_checkers import check_test_type_config
from .plugin.tc_base import TestCaseProcessor
from .plugin.test_resource import ResourceManager
from .plugin.test_config import TestConfigData
from .plugin.test_type_config import get_available_test_type_config, AllTestTypeConfig
if TYPE_CHECKING:
    from .dataset import PluginModel2544


class TestSuite2544(PluginAbstract["PluginModel2544"]):
    def prepare(self) -> None:
        self.tpld_id = 0
        self.mac_learned = False
        self.iteration: int = 1
        self.__test_conf = TestConfigData(self.cfg.test_configuration)
        self.resources = ResourceManager(
            self.testers,
            self.cfg.ports_configuration,
            self.port_identities,
            self.__test_conf,
            self.xoa_out,
        )
        self._test_type_conf: List["AllTestTypeConfig"] = get_available_test_type_config(self.cfg.test_types_configuration)


    async def __pre_test(self) -> None:
        check_test_type_config(self._test_type_conf)
        await self.resources.init_resource(
            self.cfg.test_types_configuration.latency_test.latency_mode,
        )

    def gen_loop(self, type_conf: "AllTestTypeConfig") -> Generator[Tuple[int, float], None, None]:
        max_iteration = type_conf.common_options.repetition
        if self.__test_conf.is_iteration_outer_loop_mode:
            for iteration in range(1, max_iteration + 1):
                for current_packet_size in self.__test_conf.packet_size_list:
                    yield iteration, current_packet_size
        else:
            for current_packet_size in self.__test_conf.packet_size_list:
                for iteration in range(1, max_iteration + 1):
                    yield iteration, current_packet_size

    async def __do_test(self) -> None:
        tc = TestCaseProcessor(self.resources, self.xoa_out)
        await tc.prepare()
        while True:
            for type_conf in self._test_type_conf:
                for iteration, current_packet_size in self.gen_loop(type_conf):
                    await self.state_conditions.wait_if_paused()
                    await self.state_conditions.stop_if_stopped()
                    await self.resources.setup_packet_size(current_packet_size)
                    await tc.run(type_conf, current_packet_size, iteration)
                    if (
                        not self.__test_conf.is_iteration_outer_loop_mode
                        and type_conf.repetition > 1
                        and iteration == type_conf.repetition
                    ):  # calculate average 
                        tc.cal_average(type_conf, current_packet_size)
                if (
                    self.__test_conf.is_iteration_outer_loop_mode
                    and type_conf.repetition > 1
                ):  # calculate average at last
                    tc.cal_average(type_conf)

            if not self.__test_conf.repeat_test_until_stopped:
                break

    async def __post_test(self) -> None:
        pass
        # TODO: wait for callback exception catch
        # await asyncio.gather(*[port_struct.clear() for port_struct in self.control_ports])

    async def start(self) -> None:
        await self.__pre_test()
        await self.__do_test()
        # await self.__post_test()
