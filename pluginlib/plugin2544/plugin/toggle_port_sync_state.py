import time
import asyncio
from typing import List, TYPE_CHECKING
from xoa_driver.utils import apply
from xoa_driver.enums import OnOff

if TYPE_CHECKING:
    from .structure import Structure
    from ..model import TogglePortSyncConfig


async def add_toggle_port_sync_state_steps(
    control_ports: List["Structure"], toggle_port_sync_config: "TogglePortSyncConfig"
) -> None:  # AddTogglePortSyncStateSteps
    if not toggle_port_sync_config.toggle_port_sync:
        return
    sync_off_duration_second = toggle_port_sync_config.sync_off_duration_second
    delay_after_sync_on_second = toggle_port_sync_config.delay_after_sync_on_second
    # Set Port TX Off
    await apply(
        *[port_struct.port.tx_config.enable.set(OnOff.OFF) for port_struct in control_ports]
    )

    # Sync Off Period
    await asyncio.sleep(sync_off_duration_second)

    # Set Port TX On
    await apply(
        *[port_struct.port.tx_config.enable.set(OnOff.ON) for port_struct in control_ports]
    )

    # Delay After Sync On
    start_time = time.time()
    for port_struct in control_ports:
        while not port_struct.port.sync_status:
            await asyncio.sleep(1)
            if time.time() - start_time > 30:
                raise TimeoutError(f"Waiting for {port_struct.port} sync timeout!")
    await asyncio.sleep(delay_after_sync_on_second)
