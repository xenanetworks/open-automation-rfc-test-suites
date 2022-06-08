import asyncio, time
from decimal import Decimal
from typing import Dict, List, TYPE_CHECKING, Tuple, Union

from loguru import logger
from pluginlib.plugin2544.plugin import stream_struct
from pluginlib.plugin2544.plugin.learning import add_mac_learning_steps
from xoa_driver import testers as xoa_testers, modules, enums, utils
from pluginlib.plugin2544.model.m_test_config import (
    TestConfiguration,
)
from pluginlib.plugin2544.plugin.config_checkers import check_config
from pluginlib.plugin2544.plugin.common import (
    get_peers_for_source,
)
from pluginlib.plugin2544.plugin.setup_streams import setup_streams
from pluginlib.plugin2544.plugin.structure import PortStruct
from pluginlib.plugin2544.utils import constants as const, exceptions
from pluginlib.plugin2544.utils.logger import TestSuitPipe

if TYPE_CHECKING:
    from xoa_core.core.test_suites.datasets import PortIdentity
    from ..model import (
        PortConfiguration,
        ThroughputTest,
        LatencyTest,
        FrameLossRateTest,
        BackToBackTest,
    )


class ResourceManager:
    def __init__(
        self,
        testers: Dict[str, "xoa_testers.GenericAnyTester"],
        all_confs: List["PortConfiguration"],
        port_identities: Dict[str, "PortIdentity"],
        test_conf: "TestConfiguration",
        xoa_out: "TestSuitPipe",
    ):
        self.all_confs = all_confs
        self.__port_identities = port_identities
        self._validate_tester_type(testers.values(), xoa_testers.L23Tester)
        self.__testers: Dict[str, "xoa_testers.L23Tester"] = testers  # type: ignore
        self.port_structs: List["PortStruct"] = []
        self.xoa_out: "TestSuitPipe" = xoa_out
        self.test_conf: "TestConfiguration" = test_conf
        self.mapping: Dict[str, List[int]] = {}

    @property
    def has_l3(self):
        return any([conf.profile.protocol_version.is_l3 for conf in self.all_confs])

    @staticmethod
    def _validate_tester_type(testers, valid_type) -> None:
        if not all(isinstance(t, valid_type) for t in testers):
            raise ValueError("")

    @property
    def tx_ports(self) -> List["PortStruct"]:
        return [
            port_struct
            for port_struct in self.port_structs
            if port_struct.port_conf.is_tx_port
        ]

    @property
    def rx_ports(self) -> List["PortStruct"]:
        return [
            port_struct
            for port_struct in self.port_structs
            if port_struct.port_conf.is_rx_port
        ]

    async def init_resource(self, latency_mode: const.LatencyModeStr):

        for port_struct in self.tx_ports:
            tester_id = port_struct.port_identity.tester_id
            if tester_id not in self.mapping:
                self.mapping[tester_id] = []
            self.mapping[tester_id] += [
                port_struct.port.kind.module_id,
                port_struct.port.kind.port_id,
            ]
        await self.collect_control_ports()
        self.resolve_port_relations()
        await check_config(self.port_structs, self.test_conf)
        await self.stop_traffic()
        await asyncio.sleep(self.test_conf.delay_after_port_reset_second)
        await asyncio.gather(
            *[
                port_struct.setup_port(self.test_conf, latency_mode)
                for port_struct in self.port_structs
            ]
        )
        await self.setup_sweep_reduction()
        await self.add_toggle_port_sync_state_steps()
        await add_mac_learning_steps(self, const.MACLearningMode.ONCE)
        await setup_streams(self.port_structs, self.test_conf)
        for port_struct in self.port_structs:
            await port_struct.configure_streams(self.test_conf)

    async def stop_traffic(self):
        await asyncio.gather(
            *[
                port_struct.set_traffic(enums.StartOrStop.STOP)
                for port_struct in self.port_structs
            ]
        )

    async def setup_sweep_reduction(self):
        if (
            not self.test_conf.enable_speed_reduction_sweep
            or self.test_conf.topology.is_pair_topology
        ):
            return
        await asyncio.gather(
            port_struct.set_sweep_reduction(10 * (index + 1))
            for index, port_struct in enumerate(self.port_structs)
        )

    async def collect_control_ports(self):
        await asyncio.gather(*self.__testers.values())
        for port_conf in self.all_confs:
            slot = port_conf.port_slot
            port_identity = self.__port_identities[slot]
            tester = self.__testers[port_identity.tester_id]
            if not isinstance(tester, xoa_testers.L23Tester):
                raise exceptions.WrongModuleTypeError(tester)
            module = tester.modules.obtain(port_identity.module_index)
            if isinstance(module, modules.ModuleChimera):
                raise exceptions.WrongModuleTypeError(module)
            port = module.ports.obtain(port_identity.port_index)
            port_struct = PortStruct(
                tester, port, port_conf, port_identity, self.xoa_out
            )
            self.port_structs.append(port_struct)
        await asyncio.gather(
            *[port_struct.reserve() for port_struct in self.port_structs]
        )

    async def add_toggle_port_sync_state_steps(
        self,
    ) -> None:  # AddTogglePortSyncStateSteps
        toggle_conf = self.test_conf.toggle_port_sync_config
        if not toggle_conf.toggle_port_sync:
            return
        await asyncio.gather(
            *[
                port_struct.set_toggle_port_sync(enums.OnOff.OFF)
                for port_struct in self.port_structs
            ]
        )
        await asyncio.sleep(toggle_conf.sync_off_duration_second)
        await asyncio.gather(
            *[
                port_struct.set_toggle_port_sync(enums.OnOff.ON)
                for port_struct in self.port_structs
            ]
        )
        # Delay After Sync On
        start_time = time.time()
        for port_struct in self.port_structs:
            while not port_struct.port.sync_status:
                await asyncio.sleep(1)
                if time.time() - start_time > 30:
                    raise TimeoutError(f"Waiting for {port_struct.port} sync timeout!")
        await asyncio.sleep(toggle_conf.delay_after_sync_on_second)

    def resolve_port_relations(self) -> None:
        topology = self.test_conf.topology
        test_port_index = 0
        if topology.is_mesh_topology:
            for port_struct in self.port_structs:
                port_struct.properties.test_port_index = test_port_index
                test_port_index += 1
        else:
            east_ports = [
                port_struct
                for port_struct in self.port_structs
                if port_struct.port_conf.port_group.is_east
            ]
            west_ports = [
                port_struct
                for port_struct in self.port_structs
                if port_struct.port_conf.port_group.is_west
            ]
            for port_struct in east_ports:
                port_struct.properties.test_port_index = test_port_index
                test_port_index += 1
            for port_struct in west_ports:
                port_struct.properties.test_port_index = test_port_index
                test_port_index += 1

        for port_struct in self.tx_ports:
            port_config = port_struct.port_conf
            dest_ports = get_peers_for_source(topology, port_config, self.port_structs)
            for peer_struct in dest_ports:
                port_struct.properties.register_peer(peer_struct)

    async def setup_packet_size(self, current_packet_size: Union[Decimal, int]) -> None:
        if self.test_conf.frame_sizes.packet_size_type.is_fix:
            min_size = max_size = int(current_packet_size)
        else:
            min_size, max_size = self.test_conf.frame_sizes.size_range
        await asyncio.gather(
            *[
                port_struct.set_streams_packet_size(
                    self.test_conf.frame_sizes.packet_size_type.to_xmp(),
                    min_size,
                    max_size,
                )
                for port_struct in self.port_structs
            ]
        )

    def monitor_status(self):
        if self.test_conf.should_stop_on_los:
            for port_struct in self.port_structs:
                port_struct.monitor_status()
        for port_struct in self.tx_ports:
            port_struct.monitor_traffic()

    def test_running(self) -> bool:
        return any([port_struct.traffic_status for port_struct in self.tx_ports])

    def los(self) -> bool:
        if self.test_conf.should_stop_on_los:
            return not all(
                [port_struct.sync_status for port_struct in self.port_structs]
            )
        return False

    def should_quit(self, start_time: float, actual_duration: int) -> bool:
        test_finished = not self.test_running()
        elapsed = time.time() - start_time
        actual_duration_elapsed = elapsed >= actual_duration + 5
        los = self.los()
        if los:
            logger.error("Test is stopped due to the loss of signal of ports.")
        return test_finished or los or actual_duration_elapsed

    def set_rate(self, rate: Decimal) -> None:
        for port_struct in self.tx_ports:
            port_struct.rate = rate

    async def set_tx_time_limit(self, tx_timelimit: int) -> None:
        await asyncio.gather(
            *[
                port_struct.set_tx_time_limit(int(tx_timelimit))
                for port_struct in self.tx_ports
            ]
        )

    async def set_frame_limit(self, frame_count: int) -> None:
        await asyncio.gather(
            *[
                stream_struct.set_frame_limit(frame_count)
                for port_struct in self.tx_ports
                for stream_struct in port_struct.stream_structs
            ]
        )

    async def clear_statistic(self) -> None:
        await asyncio.gather(
            *[port_struct.clear_statistic() for port_struct in self.port_structs]
        )
        await asyncio.sleep(1)

    async def query_traffic_status(self) -> None:
        await asyncio.gather(
            *[port_struct.port.traffic.state.get() for port_struct in self.tx_ports]
        )

    async def start_traffic_sync(
        self, tester: "xoa_testers.L23Tester", module_port_list: List[int]
    ) -> None:
        local_time = (await tester.time.get()).local_time
        delay_seconds = 2
        # logger.error(
        #     f"SYNC {tester.management_interface.ip_address} -> {local_time + delay_seconds}"
        # )
        await utils.apply(
            tester.traffic_sync.set(
                enums.OnOff.ON, local_time + delay_seconds, module_port_list
            )
        )

    async def start_traffic(self, port_sync=False) -> None:
        if not port_sync:
            await asyncio.gather(
                *[
                    port_struct.set_traffic(enums.StartOrStop.START)
                    for port_struct in self.tx_ports
                ]
            )
            return
        if len(self.mapping) == 1:
            # same tester
            tester_id = list(self.mapping.keys())[0]
            tester = self.__testers[tester_id]
            await utils.apply(
                tester.traffic.set(
                    enums.OnOff(enums.StartOrStop.START), self.mapping[tester_id]
                )
            )
        else:
            # multi tester need to use c_trafficsync cmd
            await asyncio.gather(
                *[
                    self.start_traffic_sync(self.__testers[tester_id], module_port_list)
                    for tester_id, module_port_list in self.mapping.items()
                ]
            )

    async def collect(
        self, packet_size: Decimal, duration: Decimal, is_final: bool = False
    ):
        [
            port_struct.init_counter(packet_size, duration, is_final)
            for port_struct in self.port_structs
        ]
        # for port_struct in self.port_structs:
        #     for stream in port_struct.stream_structs:
        #         await stream.query()
        await asyncio.gather(
            *[
                stream.query(packet_size, duration, is_final)
                for port_struct in self.port_structs
                for stream in port_struct.stream_structs
            ]
        )
        # logger.error([port_struct.statistic for port_struct in self.port_structs])
