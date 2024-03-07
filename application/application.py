import asyncio
import base64
import gzip
import json
import os

from datetime import datetime
# from dateutil import parser
from mergedeep import merge

from application.offline import Offline
from application.repository import TemplateRepository
from skeleton import Skeleton


class Application(Skeleton, Offline):
    """Application Specific Logic"""

    total_requests: int = 0
    failed_request: int = 0
    average_time: float = 0
    application_index: int = None
    application_pid: int = None

    template_repository = TemplateRepository()

    def __init__(self, debug: bool = False, prefix: str = 'direct.>') -> None:
        super().__init__()

        self.debug = debug
        self.application_pid = os.getpid()
        self.prefix = prefix

    def get_num_fiscal(self, body: dict, data: dict):
        num_fiscal = body.get('NumFiscal')
        head = data.get('head')
        head = head if head else body.get('head')

        if head and head.get('cashregisternum') is not None:
            num_fiscal = num_fiscal if num_fiscal else head.get('cashregisternum')

        return num_fiscal

    def prepare_z_rep_section(self, name: str, data: dict) -> dict:
        result = {
            name: {
                "sum": data.get('Sum') or 0,
                "orderscnt": data.get('OrdersCount') or 0,
                "payforms": [
                    {
                        "payformcd": None,
                        "payformnm": None,
                        "sum": None
                    }
                ],
                "taxes": [
                    {
                        "type": None,
                        "name": None,
                        "letter": None,
                        "prc": None,
                        "turnover": None,
                        "sum": None
                    }
                ]
            }
        }

        if data.get('Tax') is None:
            del result[name]['taxes']
        if data.get('PayForm') is None:
            del result[name]['payforms']

        return result

    def map_fields(self, obj: dict, result: dict) -> None:
        mapper = {
            'Sum': 'sum',
            'OrdersCount': 'orderscnt',
            'PayForm': 'payforms',
            'Tax': 'taxes',
            'PayFormCode': 'payformcd',
            'PayFormName': 'payformnm',
            'Type': 'type',
            'Name': 'name',
            'Letter': 'letter',
            'Prc': 'prc',
            'Turnover': 'turnover',
        }

        notnull = ['PayForm', 'Tax']

        for field, value in (obj.items() if type(obj) == dict else enumerate(obj, start=0)):
            if mapper.get(field) is None:
                continue

            if type(value) == list:
                for index, item in enumerate(value, start=0):
                    if len(result.get(mapper.get(field))) <= index:
                        result.get(mapper.get(field)).append({})

                    self.map_fields(item, result.get(mapper.get(field))[index])

            if type(value) != list:
                if value is None and field in notnull:
                    continue

                result[mapper.get(field)] = value

    async def predispatch(self, request: str, content: bytes, data: dict) -> bytes:
        content = await super().predispatch(request, content, data)
        body = json.loads(content.decode())

        signer = data.get('signer')
        num_fiscal = self.get_num_fiscal(body, data)

        if body.get('head') is None:
            return content

        response = await self.nc.request(
            'get_registrar_state',
            json.dumps({
                'signer': signer,
            }).encode()
        )
        state = json.loads(response.data.decode()).get('state')

        # --------------------Z-REP----------------------
        from application.api.common import Documents
        if request == Documents.ZRepCheck:
            response = await self.nc.request(
                self.config.get_channel_queue(identifier=signer, debug=self.debug),
                json.dumps({
                    'signer': signer,
                    'num_fiscal': num_fiscal,
                    'section': ['state', 'totals'],
                }).encode(),
                timeout=10
            )
            response_data = json.loads(response.data.decode())
            totals_response = response_data.get('totals')
            state = response_data.get('state')
            totals = totals_response.get('Totals') or {}
            real = totals.get('Real') or {}
            ret = totals.get('Ret') or {}

            if totals is None or totals_response.get('ZRepPresent'):
                return content

            result = {
                "zbody": {
                    "serviceinput": totals.get('ServiceInput') or 0,
                    "serviceoutput": totals.get('ServiceOutput') or 0
                }
            }

            result.update(self.prepare_z_rep_section('zrealiz', real))
            result.update(self.prepare_z_rep_section('zreturn', ret))

            self.map_fields(real, result.get('zrealiz'))
            self.map_fields(ret, result.get('zreturn'))

            body.update(result)
        # --------------------Z-REP----------------------

        if not len(state):
            try:
                response = await self.nc.request(
                    self.config.get_channel_queue(identifier=signer, debug=self.debug),
                    json.dumps({
                        'signer': signer,
                        'num_fiscal': num_fiscal,
                        'section': ['state'],
                    }).encode(),
                    timeout=10
                )
                state = json.loads(response.data.decode()).get('state')
            except Exception as error:
                print(error)

        next_local_num = state.get('NextLocalNum')
        # formatted_date = parser.parse(state.get('Timestamp'))
        # order_date = formatted_date.strftime("%d%m%Y")
        # order_time = formatted_date.strftime("%H%M%S")
        merge(body, {'head': {'ordernum': next_local_num}})
        content = json.dumps(body).encode()

        return content

    async def postdispatch(self, request: str, content: bytes, data: dict):
        content = await super().postdispatch(request, content, data)

        signer = data.get('signer')
        num_fiscal = self.get_num_fiscal(data, data)

        await self.nc.publish(
            self.config.get_channel_queue(identifier=signer, debug=self.debug),
            json.dumps({
                'signer': signer,
                'num_fiscal': num_fiscal,
            }).encode()
        )

        return content

    async def subscribe(self) -> None:
        channel = self.config.channel_base(self.prefix, debug=self.debug)
        await self.nc.subscribe(channel, cb=self.message_handler)

        self.print_listener_info(channel=channel)

    def create_tasks(self) -> list:
        tasks = list()
        tasks.append(
            asyncio.ensure_future(
                self.subscribe()
            )
        )

        return tasks

    def print_stats(self, start_time) -> None:
        current_time = datetime.now()
        total_seconds = (current_time - start_time).total_seconds()
        self.average_time = (self.average_time + total_seconds) / 2

        self.logger.log(
            '\n{index} :: {time}      Avg. {avg:.4f} sec.  //  Total {total}  //  Failed {failed}'.format(
                time=current_time,
                avg=self.average_time,
                total=self.total_requests,
                failed=self.failed_request,
                index=self.application_pid,
            ))

    def ungzip(self, data: bytes) -> bytes:
        if not data:
            raise Exception('Request is empty')

        return gzip.decompress(data)

    def gzip(self, content: bytes) -> bytes:
        return gzip.compress(content)

    def json_parse(self, data: bytes) -> dict:
        return json.loads(data)

    def json_encode(self, obj: dict) -> bytes:
        return json.dumps(obj).encode()

    def base64_encode(self, string: bytes) -> str:
        return base64.b64encode(string).decode()

    def base64_decode(self, string: bytes) -> bytes:
        return base64.b64decode(string)

    async def message_handler(self, msg) -> None:
        self.total_requests += 1
        self.failed_request += 1

        start_time = datetime.now()

        try:
            await super().message_handler(msg)
            self.failed_request -= 1
        except Exception as error:
            if msg.reply is not None:
                await self.nc.publish(msg.reply, str(error).encode())

            if self.debug:
                raise Exception(error)

            self.logger.log('{pid} / {channel} :: {time} ERROR: {error}'.format(
                pid=self.application_pid,
                channel=msg.subject,
                time=datetime.now(),
                error=error
            ))

        self.print_stats(start_time)
