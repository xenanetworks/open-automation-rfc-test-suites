from xoa_core.types import PluginAbstract
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dataset import PluginModel2544


import asyncio
from typing import List

from .model.m_test_type_config import LatencyTest
from .plugin.statistics import stop_traffic
from .plugin.test_result_structure import TestCaseResult
from .utils.logger import logger
from .plugin.structure import (
    StreamInfo,
    Structure,
)
from .plugin.toggle_port_sync_state import add_toggle_port_sync_state_steps
from .utils.constants import MACLearningMode
from .plugin.control_ports import collect_control_ports
from .plugin.resolve_port_relations import resolve_port_relations_main
from .plugin.common import setup_macaddress, TPLDControl
from .plugin.arp_request import set_arp_request
from .plugin.port_base_settings import (
    base_setting,
    set_reduction_sweep,
    setup_latency_mode,
)
from .plugin.resolve_stream_relations import (
    setup_packet_header,
    configure_source_streams,
    create_source_stream,
)
from .plugin.checker.config_checkers import check_config
from .plugin.mac_learning import add_mac_learning_steps
from .plugin.outer_loop import gen_loop, test_run
from decimal import getcontext
from xoa_core.types import PluginAbstract

getcontext().prec = 12


class TestSuit2544(PluginAbstract["PluginModel2544"]):
    def prepare(self) -> None:
        self.tpld_id = 0
        self.mac_learned = False
        self.iteration: int = 1
        self.test_conf = self.cfg.test_configuration
        self.control_ports: List["Structure"] = []
        self.tpld_controller = TPLDControl(self.test_conf.tid_allocation_scope)
        self.stream_lists: List["StreamInfo"] = []
        self.test_case_result = TestCaseResult()
        return super().prepare()

    async def __setup_macaddress(self) -> None:
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

    async def __configure_resource(self) -> None:
        await stop_traffic(self.control_ports)
        await asyncio.gather(
            *[
                base_setting(self.test_conf, port_struct, self.xoa_out)
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

    async def __init_resource(self) -> None:

        self.control_ports = await collect_control_ports(
            self.testers, self.cfg.ports_configuration, self.port_identities
        )
        resolve_port_relations_main(
            self.test_conf.topology, self.control_ports
        )  # setup test_port_index

    async def __prepare_data(self) -> None:
        await check_config(self.cfg, self.control_ports)
        await self.__setup_macaddress()
        self.stream_lists = configure_source_streams(
            self.control_ports, self.tpld_controller, self.test_conf
        )  # SetupSourceStreams -- order rebuild

    async def __pre_test(self) -> None:
        await self.__init_resource()
        await self.__prepare_data()
        await asyncio.sleep(self.test_conf.delay_after_port_reset_second)
        await self.__configure_resource()

    async def __do_test(self) -> None:
        while True:
            for type_conf in self.cfg.test_types_configuration.available_test:
                if isinstance(type_conf, LatencyTest):
                    await setup_latency_mode(self.control_ports, type_conf.latency_mode)

                for iteration, current_packet_size in gen_loop(
                    type_conf,
                    self.cfg.test_configuration,
                    self.test_case_result,
                    self.xoa_out,
                ):
                    await self.state_conditions.wait_if_paused()
                    await self.state_conditions.stop_if_stopped()
                    await test_run(
                        self.stream_lists,
                        self.control_ports,
                        type_conf,
                        self.cfg.test_configuration,
                        self.cfg.has_l3,
                        current_packet_size,
                        iteration,
                        self.test_case_result,
                        self.xoa_out,
                    )
            if not self.cfg.test_configuration.repeat_test_until_stopped:
                break

    async def __post_test(self) -> None:
        logger.info("test finish")

    async def start(self) -> None:
        try:
            await self.__pre_test()
            await self.__do_test()
            await self.__post_test()
        except Exception as e:
            logger.exception(e)
            raise e
        finally:
            await asyncio.gather(*[port_struct.free() for port_struct in self.control_ports])
