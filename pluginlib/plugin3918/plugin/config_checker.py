from ..utils.constants import RPacketSizeType
from .resource_manager import ResourceManager
from ..utils.errors import (
    CustomMixLengthUnsupported,
    MixPacketLegnthTooLarge,
    MixPacketLegnthTooSmall,
)
from typing import TYPE_CHECKING
from xoa_driver.utils import apply

if TYPE_CHECKING:
    from ...plugin3918 import Model3918


class ConfigChecker:
    def __init__(self, data: "Model3918", resource_manager: ResourceManager) -> None:
        self.data = data
        self.resource_manager = resource_manager

    async def check_config(self) -> None:
        await self._check_min_max_packet_length()

    async def _check_min_max_packet_length(self):
        min_mix = self.data.test_configuration.frame_sizes.mixed_length_config.min
        max_mix = self.data.test_configuration.frame_sizes.mixed_length_config.max
        # tokens = []
        for src_instance in self.resource_manager.mc_src_ports():
            port_can_mix_length = False  # TODO: 替换成真实值
            if port_can_mix_length:
                if src_instance.min_packet_length > min_mix:
                    raise MixPacketLegnthTooSmall(
                        src_instance.name,
                        min_mix,
                        src_instance.min_packet_length,
                    )
                elif src_instance.max_packet_length < max_mix:
                    raise MixPacketLegnthTooLarge(
                        src_instance.name,
                        max_mix,
                        src_instance.max_packet_length,
                    )
            elif (
                self.data.test_configuration.frame_sizes.packet_size_type
                == RPacketSizeType.MIX
            ):
                raise CustomMixLengthUnsupported(src_instance.name)
