from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...function_factory import TesterSaver


async def reserve_reset_ports(testers_saver: "TesterSaver") -> None:
    await testers_saver.reserve_reset_ports()
