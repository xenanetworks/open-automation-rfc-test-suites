from typing import Dict, TYPE_CHECKING, List
from ..model import PortIdentity
from .structure import Structure

if TYPE_CHECKING:
    from ..function_factory import TesterSaver
    from ..model import PortConfiguration


def collect_control_ports(
    testers_saver: "TesterSaver",
    all_confs: Dict[str, "PortConfiguration"],
) -> List[Structure]:
    return [
        Structure(
            testers_saver.get_tester(port_conf),
            testers_saver.get_port(port_conf),
            port_conf,
        )
        for _, port_conf in all_confs.items()
    ]


def setup_port_identity(
    control_ports: List["Structure"], port_identities: Dict[str, "PortIdentity"]
) -> None:
    for port_struct in control_ports:
        port_struct.properties.set_identity(
            port_identities[port_struct.port_conf.port_slot]
        )
