import asyncio
import base64
import gzip
import json

from nats.aio.errors import ErrTimeout

from application.exceptions import PrroBackendDisconnected, SignClientDisconnected
from application.logger import Logger
from skeleton import Skeleton


class StateQueue(Skeleton):
    queue = {}
    logger = Logger()

    def __init__(self, debug: bool = False) -> None:
        super().__init__()

        self.debug = debug

    async def message_handler(self, msg) -> None:
        data = json.loads(msg.data)
        signer = data.get('signer')
        num_fiscal = data.get('num_fiscal')
        section = data.get('section')
        section = section if section is not None else list()

        if not num_fiscal:
            return  self.logger.log([
                self.__class__.__name__,
                'ERROR: fiscal_num is None',
                data
            ])

        if not self.queue.get(signer):
            self.queue[signer] = {}

        if not self.queue.get(signer).get('state'):
            state = await self.get_registrar_state(signer=signer, fiscal_number=num_fiscal)
            self.queue[signer].update({'state': state})

        if 'totals' in section:
            totals = await self.get_last_shift_totals(signer=signer, fiscal_number=num_fiscal)
            self.queue[signer].update({'totals': totals})

        if msg.reply:
            await self.nc.publish(
                msg.reply,
                json.dumps(
                    self.get_for(signer, section)
                ).encode()
            )

    async def get_last_shift_totals_handler(self, msg) -> None:
        data = json.loads(msg.data)
        signer = data.get('signer')
        result = json.dumps(
            self.get_for(signer, section=['totals'])
        ).encode()

        await self.nc.publish(
            msg.reply,
            result
        )

    async def get_registrar_state_handler(self, msg) -> None:
        data = json.loads(msg.data)
        signer = data.get('signer')

        await self.nc.publish(
            msg.reply,
            json.dumps(
                self.get_for(signer, section=['state'])
            ).encode()
        )

    def get_for(self, signer: str, section: list) -> dict:
        result = {}
        if not len(section):
            return self.queue.pop(signer) if self.queue.get(signer) else {}

        for item in section:
            queue = self.queue.get(signer) if self.queue.get(signer) else {}
            result.update({item: queue.pop(item) if queue.get(item) else {}})

        return result

    def gzip_content(self, content: dict) -> str:
        return base64.b64encode(gzip.compress(json.dumps(content).encode())).decode()

    def gzip_request(self, content: dict) -> bytes:
        return gzip.compress(json.dumps(content).encode())

    def ungzip_response(self, content: bytes):
        return gzip.decompress(base64.b64decode(json.loads(gzip.decompress(content)).get('content'))).decode()

    def is_json(self, string):
        try:
            json.loads(string)
        except ValueError:
            return False
        return True

    async def do_request(self, signer: str, request: str, raw: dict) -> dict:
        body = {"data": {"request": request, "action": "command", 'signer': signer, 'skip_dispatch': True},
                "content": self.gzip_content(raw)
                }

        try:
            response = await self.nc.request(
                self.config.get_channel_queue_resolver(identifier=signer, debug=self.debug),
                self.gzip_request(body),
                timeout=20
            )
        except ErrTimeout:
            raise PrroBackendDisconnected('Немає з\'єднання з сервером.')

        ungzipped = gzip.decompress(response.data)
        body = json.loads(ungzipped)
        # content = body.get('content')
        data = body.get('data')

        try:
            response = await self.nc.request(
                self.config.get_channel_signer(identifier=signer, debug=self.debug),
                self.gzip_request(body),
                timeout=20
            )
        except ErrTimeout:
            raise SignClientDisconnected('Немає з\'єднання з клієнтом для підпису.')

        ungzipped = gzip.decompress(response.data)
        content = json.loads(ungzipped).get('content')

        body = {"data": data, "content": content}

        try:
            response = await self.nc.request(
                self.config.get_channel_queue_resolver(identifier=signer, debug=self.debug),
                self.gzip_request(body),
                timeout=20
            )
        except ErrTimeout:
            raise PrroBackendDisconnected('Немає з\'єднання з сервером.')

        result = self.ungzip_response(response.data)
        if not self.is_json(result):
            raise Exception(result)

        return json.loads(result)

    async def get_server_state(self, signer: str) -> dict:
        content = {}
        return await self.do_request(signer=signer, request='ServerState', raw=content)

    async def get_registrar_state(self, signer: str, fiscal_number: str) -> dict:
        content = {'NumFiscal': fiscal_number}
        return await self.do_request(signer=signer, request='TransactionsRegistrarState', raw=content)

    async def get_last_shift_totals(self, signer: str, fiscal_number: str) -> dict:
        content = {'NumFiscal': fiscal_number}
        return await self.do_request(signer=signer, request='LastShiftTotals', raw=content)

    def create_tasks(self) -> list:
        tasks = list()
        tasks.append(
            asyncio.ensure_future(
                self.nc.subscribe(self.config.get_channel_queue('>', debug=self.debug), cb=self.message_handler)
            )
        )
        tasks.append(
            asyncio.ensure_future(
                self.nc.subscribe('get_registrar_state', cb=self.get_registrar_state_handler)
            )
        )
        tasks.append(
            asyncio.ensure_future(
                self.nc.subscribe('get_last_shift_totals', cb=self.get_last_shift_totals_handler)
            )
        )

        self.print_listener_info(channel=self.config.get_channel_queue('>', debug=self.debug))

        return tasks
