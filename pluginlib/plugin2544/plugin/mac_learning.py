import asyncio
from typing import List, TYPE_CHECKING


from ..utils.constants import MACLearningMode
from ..utils import exceptions
from ..utils.field import MacAddress
from xoa_driver.utils import apply

if TYPE_CHECKING:
    from .structure import Structure


async def add_mac_learning_steps(
    control_ports: List["Structure"],
    require_mode: "MACLearningMode",
    mac_learning_mode: "MACLearningMode",
    mac_learning_frame_count: int,
) -> None:
    if require_mode != mac_learning_mode:
        return

    for port_struct in control_ports:
        port_conf = port_struct.port_conf
        port = port_struct.port
        if port_conf.is_rx_port:
            dest_mac = "FFFFFFFFFFFF"
            four_f = "FFFF"
            paddings = "00" * 118
            own_mac = MacAddress(port_struct.properties.mac_address).to_hexstring()
            hex_data = f"{dest_mac}{own_mac}{four_f}{paddings}"
            packet = f"0x{hex_data}"
            max_cap = port.info.capabilities.max_xmit_one_packet_length
            cur_length = len(hex_data) // 2
            if cur_length > max_cap:
                raise exceptions.PacketLengthExceed(cur_length, max_cap)
            for _ in range(mac_learning_frame_count):
                await apply(port.tx_single_pkt.send.set(packet))  # P_XMITONE
                await asyncio.sleep(1)


async def add_L2_trial_learning_steps(
    control_ports: List["Structure"],
    mac_learning_mode: "MACLearningMode",
    mac_learning_frame_count: int,
) -> None:
    await add_mac_learning_steps(
        control_ports,
        MACLearningMode.EVERYTRIAL,
        mac_learning_mode,
        mac_learning_frame_count,
    )
