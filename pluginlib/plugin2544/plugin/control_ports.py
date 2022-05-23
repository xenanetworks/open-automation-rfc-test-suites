import asyncio
from typing import Dict, TYPE_CHECKING, List
from xoa_driver import modules, testers as xoa_testers
from pluginlib.plugin2544.utils import exceptions
from pluginlib.plugin2544.plugin.structure import Structure

if TYPE_CHECKING:
    from xoa_core.core.test_suites.datasets import PortIdentity
    from ..model import PortConfiguration


async def collect_control_ports(
    testers_dict: Dict[str, "xoa_testers.GenericAnyTester"],
    all_confs: Dict[str, "PortConfiguration"],
    port_identities: Dict[str, "PortIdentity"],
) -> List["Structure"]:
    control_ports: List[Structure] = []
    await asyncio.gather(*testers_dict.values())
    for _, port_conf in all_confs.items():
        slot = port_conf.port_slot
        port_identity = port_identities[slot]
        tester = testers_dict[port_identity.tester_id]
        if not isinstance(tester, xoa_testers.L23Tester):
            raise exceptions.WrongModuleTypeError(tester)
        module = tester.modules.obtain(port_identity.module_index)
        if isinstance(module, modules.ModuleChimera):
            raise exceptions.WrongModuleTypeError(module)
        port = module.ports.obtain(port_identity.port_index)
        port_struct = Structure(tester, port, port_conf)
        port_struct.properties.set_identity(
            port_identities[port_struct.port_conf.port_slot]
        )
        control_ports.append(port_struct)
    await asyncio.gather(*[port_struct.reserve() for port_struct in control_ports])
    return control_ports
