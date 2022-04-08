from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..function_factory import TesterSaver


async def connect_chasses_main(
    tester_saver: "TesterSaver", debug_on: bool = False
) -> None:
    await tester_saver.connect_chasses(debug_on)
