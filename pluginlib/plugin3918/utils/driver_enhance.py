# from asyncio import sleep
# from typing import Union, Iterable, Generator
# from xoa_driver.utils import apply_iter
# from xoa_driver.misc import Token


# async def pause_batch_apply(
#     pause_count: int,
#     sleep_time: int,
#     cmd_tokens: Union[Iterable[Token], Generator[Token, None, None]],
# ):
#     assert pause_count <= 200
#     tokens_iter = iter(cmd_tokens)
#     done = False
#     while True:
#         this_patch = []
#         try:
#             for _ in range(pause_count):
#                 obj = next(tokens_iter)
#                 this_patch.append(obj)
#         except StopIteration:
#             done = True

#         async for r in apply_iter(*this_patch):
#             yield r
#         if done:
#             break
#         await sleep(sleep_time)
