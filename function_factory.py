""" 
Interact with xoa_driver
"""


import asyncio
from decimal import Decimal, getcontext
from typing import List, Optional, Tuple, Dict, Protocol as Interface

from xoa_driver import testers, ports, modules
from xoa_driver.utils import apply
from .plugin2544.utils.errors import ConfigError
from .plugin2544.utils.constants import PortGroup
from .plugin2544.utils.data_model import BinarySearchModel
from .plugin2544.utils.logger import logger

# from valhalla_core.resources_manager.resource_pool import ResourcePool


class IPortIdentity(Interface):
    chassis_id: str
    module_index: int
    port_index: int


class IPortConf(Interface):
    port_slot: str
    port_group: PortGroup


class ITestModel(Interface):
    ports_configuration: Dict[str, IPortConf]
    port_identities: Dict[str, IPortIdentity]


class TesterSaver:
    def __init__(
        self,
        data: ITestModel,
        loop: Optional["asyncio.AbstractEventLoop"] = None,
    ) -> None:
        self.testers: Dict[str, "testers.L23Tester"] = {}
        self.loop = loop
        self.data = data
        self.ports: List["ports.GenericL23Port"] = []
        if not loop:
            self.loop = asyncio.get_event_loop()
        self.tmp = {
            "2906f8d041e9fd07191d6a37ef5785b2": "192.168.1.198",
            "b2611846f6a1934651c9d5ee4aa4596f": "192.168.1.197",
            "9734838bddcddadfd804659582d44ad2": "87.61.110.118",
        }

    async def connect_chasses(self, debug_on: bool = False) -> None:
        async def _connect_one_chassis(
            chassis_id: str, username: str = "user"
        ) -> testers.L23Tester:
            # info = ResourcePool.fetch_tester_data(chassis_id)
            tester = await testers.L23Tester(
                host=self.tmp[chassis_id],
                password="xena",
                username=username,
                port=22606,
                debug=True,
            )
            self.testers[chassis_id] = tester
            return tester

        chasses = set(p_id.chassis_id for p_id in self.data.port_identities.values())
        await asyncio.gather(*[_connect_one_chassis(c_id) for c_id in chasses])

    async def __reserve(self, port: "ports.GenericL23Port") -> None:
        if port.is_reserved_by_me():
            await port.reservation.set_release()
        elif not port.is_released():
            await port.reservation.set_relinquish()
        await apply(
            port.reservation.set_reserve(),
            port.reset.set(),
        )

    async def reserve_reset_ports(self):
        self.ports = [
            self.get_port(port_conf)
            for port_conf in self.data.ports_configuration.values()
        ]
        await asyncio.gather(*[self.__reserve(port) for port in self.ports])
        logger.debug(f"[Reset:] {self.ports}")

    def get_port(self, port_conf: "IPortConf") -> "ports.GenericL23Port":
        identity = self.data.port_identities[port_conf.port_slot]
        tester = self.testers.get(identity.chassis_id, None)
        if not tester:
            raise ConfigError(f"Chassis id {identity.chassis_id} does not exists! ")
        module = tester.modules.obtain(identity.module_index)
        if isinstance(module, modules.ModuleChimera):
            raise ConfigError(f"No support Chimera ")
        port = module.ports.obtain(identity.port_index)
        return port

    def get_tester(self, port_conf: "IPortConf") -> "testers.L23Tester":
        identity = self.data.port_identities[port_conf.port_slot]
        tester = self.testers[identity.chassis_id]
        return tester

    def get_all_testers(self) -> List["testers.L23Tester"]:
        return list(self.testers.values())

    async def free(self) -> None:
        await asyncio.gather(*[r.reservation.set_release() for r in self.ports])
        await asyncio.gather(*[t.session.logoff() for t in self.testers.values()])


class BinarySearch:
    def __init__(self, data):
        getcontext().prec = 6
        self.start(data)

    @classmethod
    def set_traffic_tx_pct(cls, value: Decimal, port_cap_rate_bps: Decimal):
        current_tx_rate_pct = Decimal(value)
        actual_tx_bps = current_tx_rate_pct * port_cap_rate_bps
        logger.info(
            f"3. Set traffic rate to {current_tx_rate_pct * 100}% | {int(actual_tx_bps)} bps"
        )
        return current_tx_rate_pct

    @classmethod
    def update_left_boundary(
        cls, current_tx_rate_pct: Decimal, right_boundary: Decimal
    ):
        logger.info(f"5.1 Going up >>>")
        left_boundary = current_tx_rate_pct
        next_tx_rate_pct = (left_boundary + right_boundary) / 2
        logger.info(
            f"5.2 [Left: {left_boundary*100}%] ---[New TX: {next_tx_rate_pct * 100}%]--- [Right: {right_boundary*100}%]"
        )
        return left_boundary, next_tx_rate_pct

    @classmethod
    def update_right_boundary(
        cls,
        current_tx_rate_pct: Decimal,
        left_boundary: Decimal,
        is_fast_search: bool,
        loss_pct: Decimal,
    ):
        logger.info(f"5.1 Going down <<<")
        right_boundary = current_tx_rate_pct
        if is_fast_search:
            next_tx_rate_pct = max(
                current_tx_rate_pct * (Decimal(1.0) - loss_pct),
                left_boundary,
            )
        else:
            next_tx_rate_pct = (left_boundary + right_boundary) / 2
        logger.info(
            f"5.2 [Left: {left_boundary*100}%] ---[New TX: {next_tx_rate_pct * 100}%]--- [Right: {right_boundary*100}%]"
        )
        return right_boundary, next_tx_rate_pct

    @classmethod
    def compare_search_pointer(
        cls,
        current_tx_rate_pct: Decimal,
        next_tx_rate_pct: Decimal,
        res: Decimal,
        left_boundary: Decimal,
        right_boundary: Decimal,
    ) -> Tuple[Decimal, bool]:
        logger.info(
            f"6. Delta TX rate = {(next_tx_rate_pct - current_tx_rate_pct)*100}% (Resolution = {res*100}%)"
        )
        if abs(next_tx_rate_pct - current_tx_rate_pct) <= res:
            if next_tx_rate_pct >= current_tx_rate_pct:
                # make sure we report the right boundary if we are so close to it.
                if (right_boundary - current_tx_rate_pct) <= res:
                    current_tx_rate_pct = right_boundary
            else:
                if (current_tx_rate_pct - left_boundary) <= res:
                    current_tx_rate_pct = left_boundary
            return current_tx_rate_pct, True

        return current_tx_rate_pct, False

    @classmethod
    def pass_threshold(
        cls,
        current_tx_rate_pct: Decimal,
        pass_threshold_pct: Decimal,
        use_pass_threshold: bool,
    ) -> bool:
        logger.info(
            f"7. Current TX rate = {current_tx_rate_pct * 100}% (Pass threshold = {pass_threshold_pct * 100}%)"
        )
        if use_pass_threshold:
            return current_tx_rate_pct >= pass_threshold_pct
        return True

    @classmethod
    def start(cls, raw_data):
        data = BinarySearchModel.parse_obj(raw_data)
        port_id: str = data.port_id
        left_boundary: Decimal = data.min_rate
        right_boundary: Decimal = data.max_rate
        res: Decimal = data.res_rate
        is_fast_search: bool = data.is_fast_search
        statistics: List = data.statistics
        port_cap_rate_bps: Decimal = data.port_cap_rate_bps
        use_pass_threshold: bool = data.use_pass_threshold
        pass_threshold_pct: Decimal = data.pass_threshold_pct
        acceptable_loss_pct: Decimal = (
            data.acceptable_loss_pct
        )  # default acceptable loss = 0%
        # binary search algorithm default values
        current_tx_rate_pct: Decimal = Decimal(0.0)  # 100% of port tx rate
        next_tx_rate_pct: Decimal = data.initial_rate  # 99% of port tx rate
        loss_pct = Decimal(0.0)

        for i in range(len(statistics)):
            if left_boundary <= right_boundary:
                logger.info("2. Check search boundaries: L <= R")
                current_tx_rate_pct = cls.set_traffic_tx_pct(
                    next_tx_rate_pct, port_cap_rate_bps
                )
                tx_byte_count, rx_byte_count = statistics[i]
                loss_pct = (Decimal(tx_byte_count) - Decimal(rx_byte_count)) / Decimal(
                    tx_byte_count
                )
                logger.info(f"4.1 Loss percentage = {loss_pct * 100}%")
                logger.info(f"4.2 Acceptable      = {acceptable_loss_pct * 100}%")
                if loss_pct <= acceptable_loss_pct:
                    left_boundary, next_tx_rate_pct = cls.update_left_boundary(
                        current_tx_rate_pct, right_boundary
                    )
                else:
                    right_boundary, next_tx_rate_pct = cls.update_right_boundary(
                        current_tx_rate_pct, left_boundary, is_fast_search, loss_pct
                    )
                current_tx_rate_pct, smaller = cls.compare_search_pointer(
                    current_tx_rate_pct,
                    next_tx_rate_pct,
                    res,
                    left_boundary,
                    right_boundary,
                )
                if smaller:
                    if cls.pass_threshold(
                        current_tx_rate_pct, pass_threshold_pct, use_pass_threshold
                    ):
                        message = f"[PASS]: throughput found and passed for port {port_id} = {current_tx_rate_pct * 100}%"
                        logger.info(message)
                        break
                    else:
                        message = f"[FAILED]: throughput not passed for port {port_id}"
                        logger.info(message)
                        break
                else:
                    continue
            else:
                logger.info("2. Check search boundaries: L !<= R (!)")
                logger.info(f"[FAILED]: throughput not found for port {port_id}")
                break
