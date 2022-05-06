import asyncio
from typing import TYPE_CHECKING, List
from ...utils.errors import ConfigError

if TYPE_CHECKING:
    from xoa_driver.ports import GenericL23Port
    from ..structure import (
        Structure,
    )

    from ...model import (
        CommonOptions,
        TestTypesConfiguration,
    )


def check_common_option(port: "GenericL23Port", common_option: "CommonOptions") -> None:
    if common_option.duration_type.is_time_duration:
        return

    if common_option.duration > port.info.capabilities.max_tx_packet_limit:
        raise ConfigError(
            f"Frame Duration ({common_option.duration}) is larger than port capability ({port.info.capabilities.max_tx_packet_limit})"
        )


async def check_port_test_type(
    port: "GenericL23Port", type_conf: "TestTypesConfiguration"
) -> None:
    for test_case in type_conf.available_test:
        check_common_option(port, test_case.common_options)


async def check_test_case_config(
    control_ports: List["Structure"], type_conf: "TestTypesConfiguration"
) -> None:
    await asyncio.gather(
        *[
            check_port_test_type(port_struct.port, type_conf)
            for port_struct in control_ports
        ]
    )
