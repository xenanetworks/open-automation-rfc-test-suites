import asyncio
from typing import Dict, TYPE_CHECKING, List
from valhalla_core.core.test_suites.datasets import PortIdentity
from xoa_driver import utils, ports
from xoa_driver.testers import GenericAnyTester, L23Tester, L47Tester
from .structure import Structure

if TYPE_CHECKING:
    from ..model import PortConfiguration


async def collect_control_ports(
    testers: Dict[str, "GenericAnyTester"],
    all_confs: Dict[str, "PortConfiguration"],
    port_identities: Dict[str, "PortIdentity"],
) -> List[Structure]:
    control_ports: List[Structure] = []
    await connect_testers(testers.values())
    for _, port_conf in all_confs.items():
        slot = port_conf.port_slot
        port_identity = port_identities[slot]
        tester = testers[port_identity.tester_id]
        if isinstance(tester, L47Tester):
            raise Exception("not support L47Tester")
        module = tester.modules.obtain(port_identity.module_index)
        port = module.ports.obtain(port_identity.port_index)
        port_struct = Structure(tester, port, port_conf)
        port_struct.properties.set_identity(
            port_identities[port_struct.port_conf.port_slot]
        )
        control_ports.append(port_struct)
    await reserve_ports(control_ports)
    return control_ports


async def connect_testers(testers: List["L23Tester"]) -> None:
    await asyncio.gather(*testers)

async def reserve_port(port: "ports.GenericAnyPort"):
    if isinstance(port, ports.PortChimera):
        raise Exception("not support Chimera")
    if port.is_reserved_by_me():
        await port.reservation.set_release()
    elif port.is_reserved_by_others():
        await port.reservation.set_relinquish()
    await utils.apply(port.reservation.set_reserve(), port.reset.set())

async def reserve_ports(control_ports: List["Structure"]) -> None:
    await asyncio.gather(*[reserve_port(port_struct.port) for port_struct in control_ports])