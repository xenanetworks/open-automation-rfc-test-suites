from typing import TYPE_CHECKING, List

from .check_ports import check_ports
from .check_testers import check_testers
from .check_test_config import check_test_config

if TYPE_CHECKING:
    from ..structure import (
        Structure,
    )
    from pluginlib.plugin2544.dataset import PluginModel2544



async def check_config(
    data: "PluginModel2544",
    control_ports: List["Structure"],
) -> None:
    test_conf = data.test_configuration
    await check_testers(control_ports, test_conf)
    await check_ports(control_ports)
    await check_test_config(control_ports, test_conf)
