import asyncio
from typing import List, TYPE_CHECKING
from pluginlib.plugin2544.utils import exceptions
from xoa_driver import testers as xoa_testers

if TYPE_CHECKING:
    from pluginlib.plugin2544.model import TestConfiguration
    from ..structure import Structure


async def check_tester_sync_start(
    tester: "xoa_testers.L23Tester", use_sync_start: bool
) -> None:
    if not use_sync_start:
        return
    cap = await tester.capabilities.get()
    if not bool(cap.can_sync_traffic_start):
        raise exceptions.PortStaggeringNotSupport()


async def check_testers(
    control_ports: List["Structure"], test_conf: "TestConfiguration"
) -> None:
    await asyncio.gather(
        *[
            check_tester_sync_start(port_struct.tester, test_conf.use_port_sync_start)
            for port_struct in control_ports
        ]
    )
