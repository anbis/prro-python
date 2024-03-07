import asyncio
import json
from multiprocessing import Process
from datetime import datetime
from random import randint

from application.application import Application
from skeleton import Skeleton
from state_queue import StateQueue


class Balancer(Skeleton):
    """Balancer Class"""
    last_time = datetime.now()

    def __init__(self, debug: bool = False) -> None:
        super().__init__()
        self.debug = debug

        self.process_list = list()

    def __del__(self):
        for process in self.process_list:
            process.terminate()

            self.logger.log('{name} terminated.'.format(
                name=process
            ))

        super().__del__()

    def create_process(self) -> None:
        proc = Process(target=self.create_application, args=())
        self.process_list.append(proc)
        proc.start()

        prefix = 'queue_resolver.>'
        proc = Process(target=self.create_application, args=(prefix,))
        self.process_list.append(proc)
        proc.start()

        queue = Process(target=self.create_queue, args=())
        self.process_list.append(queue)
        queue.start()

    def create_application(self, prefix=None) -> None:
        args = {'debug': self.debug}
        if prefix:
            args['prefix'] = prefix

        application = Application(**args)
        application.run()

    def create_queue(self) -> None:
        args = {'debug': self.debug}
        queue = StateQueue(**args)
        queue.run()

    def create_tasks(self) -> list:
        tasks = list()
        tasks.append(
            asyncio.ensure_future(
                self.nc.subscribe(self.config.get_channel_config(debug=self.debug), cb=self.config_message_handler)
            )
        )

        self.print_listener_info(channel=self.config.get_channel_config(debug=self.debug))

        tasks.append(
            asyncio.ensure_future(
                self.nc.subscribe(self.config.get_channel('>', debug=self.debug), cb=self.all_message_handler)
            )
        )

        self.print_listener_info(channel=self.config.get_channel('>', debug=self.debug))

        return tasks

    async def all_message_handler(self, msg) -> None:
        pass
        # self.logger.log('Received \'{channel}\''.format(
        #     channel=msg.subject
        # ))

    async def config_message_handler(self, msg) -> None:
        channel = randint(0, 1000)
        await self.nc.publish(
            msg.reply,
            json.dumps({'channel': self.config.get_channel(channel, debug=self.debug)}).encode()
        )
        self.logger.log('New client with channel \'{channel}\''.format(channel=channel))

    def run(self):
        self.create_process()

        super().run()
