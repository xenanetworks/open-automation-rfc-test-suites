import json
import time
import asyncio
import requests
from ..utils.logger import logger

from .data_model import MessageModel
from ..utils.constants import SERVER_CONFIG_PATH

def get_urls():
    with open(SERVER_CONFIG_PATH, "r") as f:
        d = json.load(f)
    return d


def data_handling(url, queue):
    while True:
        try:
            data = queue.get_nowait()
            if data:
                while True:
                    timeout = 10 if data.confirm_needed else 0.000000001
                    response = requests.post(url, json=data.json(), timeout=timeout)
                    logger.debug(f"sending data: {data.json()}")
                    if not data.confirm_needed or response.status_code == 200:
                        break
                    time.sleep(0.1)
        except asyncio.queues.QueueEmpty:
            pass
        except Exception as e:
            logger.exception(e)
        finally:
            time.sleep(0.1)


class MessagePool:
    # waiting = {}
    # msg_queue = Queue()
    # rsp_queue = Queue()
    # count: int = 1
    queues = []

    def __init__(self, loop):
        self.loop = loop
        self.urls = get_urls()

    def start(self):
        for url in self.urls:
            queue = asyncio.Queue()
            self.queues.append(queue)
            logger.debug(f"create a queue for {url}")
            self.loop.run_in_executor(None, data_handling, url, queue)

    @classmethod
    async def push(cls, msg: MessageModel):
        logger.debug(f"receive message: {msg}")
        await asyncio.gather(*[queue.put(msg) for queue in cls.queues])

    @classmethod
    async def send(cls, msg: MessageModel, is_final: bool = False):
        """make sure the message is send and received"""
        logger.info(msg)
        # while True:
        #     data = await cls.msg_queue.get()

        # if msg.is_waited:
        #     msg.mid = cls.count
        #     cls.waiting[msg.mid] = fut = Future()
        #     cls.count = 1 if cls.count > REQUEST_ID_LIMIT else cls.count + 1
        #     return fut
        # await cls.msg_queue.put(msg)

    # async def receive(self):
    #     data = await self.rsp_queue.get()
    #     if data.mid in self.waiting:
    #         fut = self.waiting.pop(data.mid)
    #         fut.set_result(data.result)
    #     self.loop.create_task(self.receive())
