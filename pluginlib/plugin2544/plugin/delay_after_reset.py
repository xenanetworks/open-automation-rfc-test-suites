from ..utils.logger import logger
import asyncio


async def delay_after_reset_main(delay_after_port_reset_second: int) -> None:
    seconds = delay_after_port_reset_second
    logger.debug(f"[Delay] {seconds} seconds")
    await asyncio.sleep(seconds)
