import asyncio
from typing import Any, Dict, List
from valhalla_core.test_suit_plugin.plugin_abstract import PluginAbstract
from valhalla_core.test_suit_plugin.plugins.plugin2544.plugin.statistics import (
    stop_traffic,
)
from valhalla_core.test_suit_plugin.plugins.plugin2544.plugin.test_result_structure import (
    TestCaseResult,
)
from ..utils.logger import logger
from .structure import (
    StreamInfo,
    Structure,
)
from .toggle_port_sync_state import add_toggle_port_sync_state_steps
from ..utils.constants import MACLearningMode
from ..model import Model2544
from .connect_chasses import connect_chasses_main
from .control_ports import collect_control_ports, setup_port_identity
from .reserve_ports import reserve_reset_ports
from .delay_after_reset import delay_after_reset_main
from .resolve_port_relations import resolve_port_relations_main
from .common import setup_macaddress, TPLDControl
from .arp_request import set_arp_request
from .port_base_settings import (
    base_setting,
    set_reduction_sweep,
    setup_latency_mode,
)
from .resolve_stream_relations import (
    setup_packet_header,
    configure_source_streams,
    create_source_stream,
)
from .checker.config_checkers import check_config
from .mac_learning import add_mac_learning_steps
from .outer_loop import setup_for_outer_loop
from decimal import getcontext

getcontext().prec = 12


class TestSuit2544(PluginAbstract):
    def __init__(self, ff: Any, params: "Model2544") -> None:
        super(TestSuit2544, self).__init__(ff)
        self.data = params
        self.testers_saver = ff.TesterSaver(self.data, self.loop)
        self.tpld_id = 0
        self.mac_learned = False
        self.iteration: int = 1
        self.test_conf = self.data.test_configuration
        self.control_ports: List["Structure"] = []
        self.test_conf = self.data.test_configuration
        self.tpld_controller = TPLDControl(self.test_conf.tid_allocation_scope)
        self.stream_lists: List["StreamInfo"] = []
        self.test_case_result = TestCaseResult()

    async def __setup_macaddress(self):
        await asyncio.gather(
            *[
                setup_macaddress(
                    port_struct,
                    self.test_conf.flow_creation_type.is_stream_based,
                    self.test_conf.mac_base_address,
                )
                for port_struct in self.control_ports
            ]
        )

    async def __configure_resource(self):
        await stop_traffic(self.control_ports)

        await asyncio.gather(
            *[
                base_setting(self.test_conf, port_struct)
                for port_struct in self.control_ports
            ]
        )  # AddPortConfigSteps
        await set_reduction_sweep(self.control_ports, self.test_conf)
        await add_toggle_port_sync_state_steps(
            self.control_ports, self.test_conf.toggle_port_sync_config
        )
        await add_mac_learning_steps(
            self.control_ports,
            MACLearningMode.ONCE,
            self.test_conf.mac_learning_mode,
            self.test_conf.mac_learning_frame_count,
        )  # AddMacLearningSteps(Once)

        await set_arp_request(
            self.stream_lists,
            self.test_conf.use_gateway_mac_as_dmac,
        )  # AddL3LearningSteps
        setup_packet_header(self.stream_lists)
        await create_source_stream(self.stream_lists, self.test_conf)

    async def __init_resource(self):
        await connect_chasses_main(self.testers_saver, True)
        self.control_ports = collect_control_ports(
            self.testers_saver, self.data.ports_configuration
        )
        setup_port_identity(self.control_ports, self.data.port_identities)
        resolve_port_relations_main(
            self.test_conf.topology, self.control_ports
        )  # setup test_port_index

    async def __prepare_data(self):
        await check_config(
            self.data, self.testers_saver.get_all_testers(), self.control_ports
        )
        await self.__setup_macaddress()
        self.stream_lists = configure_source_streams(
            self.control_ports, self.tpld_controller, self.test_conf
        )  # SetupSourceStreams -- order rebuild

    async def __pre_test(self) -> None:
        await self.__init_resource()
        await self.__prepare_data()
        await reserve_reset_ports(self.testers_saver)
        await delay_after_reset_main(self.test_conf.delay_after_port_reset_second)
        await self.__configure_resource()

    async def __do_test(self) -> None:
        for type_conf in self.data.test_types_configuration.available_test:
            if type_conf.test_type.is_latency:
                await setup_latency_mode(self.control_ports, type_conf.latency_mode)
            await setup_for_outer_loop(
                self.stream_lists,
                self.control_ports,
                type_conf,
                self.data.test_configuration,
                self.data.has_l3,
                self.test_case_result,
            )

    async def __post_test(self) -> None:
        logger.info("test finish")

    async def start(self) -> None:
        try:
            await self.__pre_test()
            await self.__do_test()
            await self.__post_test()
        except Exception as e:
            logger.exception(e)
            await self.testers_saver.free()
