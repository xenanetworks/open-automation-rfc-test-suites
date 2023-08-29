from xoa_core.types import PluginAbstract
from xoa_driver.hlfuncs import mgmt, anlt
from asyncio import gather
from typing import TYPE_CHECKING
from .plugin.test_resource import ResourceManagerAnlt, FreyaModule, FreyaPort
from .plugin.tc_coeff_boundary_eq_limit_test import TcCoeffBoundaryEqLimitTest
from .plugin.tc_coeff_boundary_max_min_limit_test import TcCoeffBoundaryMaxLimitTest, TcCoeffBoundaryMinLimitTest
from .plugin.tc_preset_frame_lock import TcPresetFrameLock
from .plugin.tc_preset_performance import TcPresetPerformance
from .plugin.tc_base import TcBase
if TYPE_CHECKING:
    from .dataset import ModelAnlt


class TestSuiteAnlt(PluginAbstract["ModelAnlt"]):

    async def __pre_test(self) -> None:
        await gather(*self.testers.values())
        self.resource = ResourceManagerAnlt(self.testers, self.port_identities, self.cfg, self.xoa_out)

    async def __do_test(self) -> None:
        for tc in (TcCoeffBoundaryEqLimitTest, TcCoeffBoundaryMaxLimitTest, TcCoeffBoundaryMinLimitTest, TcPresetFrameLock, TcPresetPerformance):
            testcase = tc(self.resource)
            await testcase.run()

    async def __post_test(self) -> None:
        pass
        # await mgmt.free_port(self.resource.port)
        # await anlt.anlt_stop(self.resource.port)

    async def start(self) -> None:
        await self.__pre_test()
        await self.__do_test()
        await self.__post_test()
