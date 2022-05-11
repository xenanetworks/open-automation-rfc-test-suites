from typing import Dict, TYPE_CHECKING, List
from loguru import logger
from valhalla_core.core.test_suites.datasets import PortIdentity
from xoa_driver.testers import GenericAnyTester, L23Tester, L47Tester
from .structure import Structure
from xoa_driver.ports import  PortChimera
if TYPE_CHECKING:
    from ..model import PortConfiguration


def collect_control_ports(
    testers: Dict[str, "GenericAnyTester"],
    all_confs: Dict[str, "PortConfiguration"],
    port_identities: Dict[str, "PortIdentity"]
) -> List[Structure]:
    control_ports:List[Structure] = []
    for _, port_conf in all_confs.items():
        slot = port_conf.port_slot
        port_identity = port_identities[slot]
        tester = testers[port_identity.tester_id]
        if isinstance(tester, L47Tester):
            raise Exception("not support L47Tester")
        module = tester.modules.obtain(port_identity.module_index)
        port = module.ports.obtain(port_identity.port_index)
        if isinstance(port, PortChimera):
            raise Exception("not support Chimera")
        port_struct = Structure(tester, port, port_conf)
        port_struct.properties.set_identity(
            port_identities[port_struct.port_conf.port_slot]
        )
        control_ports.append(port_struct)
    return control_ports

