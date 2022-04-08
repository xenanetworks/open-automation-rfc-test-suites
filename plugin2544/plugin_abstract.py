import asyncio
import types
from typing import TYPE_CHECKING
from abc import ABC, abstractmethod
from .utils.logger import logger


# if TYPE_CHECKING:
#     from valhalla_core.resources_manager.resource_pool import ResourcePool


class PluginAbstract(ABC):
    def __init__(self, ff: types.ModuleType) -> None:
        self.loop = asyncio.get_event_loop()
        self.resource_pool = None
        self.ff = ff

    async def run(self) -> None:
        try:
            await self.start()
        except Exception as e:
            logger.error(f"{type(e)}: {e}")

    @abstractmethod
    async def start(self) -> None:
        pass

    # @property
    # @abstractmethod
    # def model(self) -> Optional[Type["BaseModel"]]:
    #     return None

    # def link_pool(self, pool: "ResourcePool"):
    #     self.resource_pool = pool
