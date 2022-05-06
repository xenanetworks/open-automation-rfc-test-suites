from typing import TYPE_CHECKING, List

from .check_ports import check_ports
from .check_test_case_config import check_test_case_config
from .check_testers import check_testers
from .check_test_config import check_test_config

if TYPE_CHECKING:
    from xoa_driver import testers
    from ..structure import (
        Structure,
    )
    from ...model import (
        Model2544,
    )


async def check_config(
    data: "Model2544",
    testers: List["testers.L23Tester"],
    control_ports: List["Structure"],
) -> None:
    test_conf = data.test_configuration
    await check_testers(testers, test_conf)
    await check_ports(control_ports)
    await check_test_config(control_ports, test_conf)
    await check_test_case_config(control_ports, data.test_types_configuration)
