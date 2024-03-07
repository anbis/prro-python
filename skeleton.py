import asyncio
import os

from nats.aio.client import Client as NATS

from application.config import Config
from application.logger import Logger


class Skeleton:
    nc = None
    config = Config()
    logger = Logger()

    def __init__(self) -> None:
        super().__init__()

        self.nc = NATS() if self.nc is None else self.nc

        self.logger.log('{name} created at PID: {pid}'.format(
            name=self.__class__.__name__,
            pid=os.getpid()
        ))

    def __del__(self):
        self.logger.log('{name} destroyed.'.format(
            name=self.__class__.__name__
        ))

    async def disconnected_cb(self):
        self.logger.log('{name} got disconnected!'.format(
            name=self.__class__.__name__
        ))

    async def reconnected_cb(self):
        self.logger.log('{name} got reconnected to {url}'.format(
            name=self.__class__.__name__,
            url=self.nc.connected_url.netloc
        ))

    async def error_cb(self, e):
        self.logger.log('{name} there was an error: {e}'.format(
            name=self.__class__.__name__,
            e=e
        ))

    async def closed_cb(self):
        self.logger.log('{name} connection is closed'.format(
            name=self.__class__.__name__
        ))

    def create_tasks(self) -> list:
        tasks = list()
        # tasks.append(
        #     asyncio.ensure_future(
        #         self.subscribe()
        #     )
        # )

        return tasks

    async def entrypoint(self, loop) -> None:
        options = {
            'servers': self.config.get_nats_servers(),
            'loop': loop,
            'max_reconnect_attempts': -1,
            'disconnected_cb': self.disconnected_cb,
            'reconnected_cb': self.reconnected_cb,
            # 'error_cb': self.error_cb,
            'closed_cb': self.closed_cb,
        }

        await self.nc.connect(**options)
        await asyncio.wait(self.create_tasks())

    async def close_conn(self):
        await self.nc.close()

    def print_listener_info(self, channel):
        self.logger.log('{name} listening \'{channel}\''.format(
            name=self.__class__.__name__,
            channel=channel
        ))

    def run(self):
        loop = asyncio.new_event_loop()

        try:
            loop.run_until_complete(self.entrypoint(loop))
            loop.run_forever()
        except KeyboardInterrupt:
            loop.run_until_complete(self.close_conn())
