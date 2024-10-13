import json
import uuid
import pytz
import xmltodict

from datetime import datetime

from application.api.common import Endpoints
from application.config import Config
from application.templates.respond_encrypted_template import TemplateResponseEncrypted


class XMLTemplate(TemplateResponseEncrypted):
    endpoint = Endpoints.DocumentEndpoint
    doc_type = 'xml'
    root_tag = 'CHECK'
    endings = b'</TICKET>'

    number_fields = [
        'SUM',
        'PRICE',
        'COST',
        'PROVIDED',
        'REMAINS',
        'PRC', 'TURNOVER',
        'SERVICEINPUT',
        'AMOUNT',
        'SERVICEOUTPUT'
    ]

    mapper = {
        'head': 'CHECKHEAD',
        'total': 'CHECKTOTAL',
        'taxes': 'CHECKTAX',
        'pay': 'CHECKPAY',
        'items': 'CHECKBODY',
    }

    def get_server_datetime(self):
        # TODO: Change this code!!!
        import random
        import string
        import requests
        from dateutil import parser

        seed = ''.join(random.choices(string.digits, k=18))
        url = Endpoints.Endpoint + '/cmd' + '?randomseed={seed}'.format(seed=seed)
        data = {'Command': 'ServerState'}
        response = requests.post(url=url, json=data)
        if response.status_code == 200:
            data = response.json()
            return parser.parse(data.get('Timestamp'))
        else:
            return datetime.now(pytz.timezone('Europe/Kiev'))

    def get_default_value(self, field: str, value: str = None):
        if field.upper() == 'UID':
            return str(uuid.uuid4())

        if field.upper() == 'ORDERDATE':
            return self.get_server_datetime().strftime("%d%m%Y")

        if field.upper() == 'ORDERTIME':
            return self.get_server_datetime().strftime("%H%M%S")

        if field.upper() == 'TYPE':
            return 0

        return value

    def process_value(self, field, value):
        if field.upper() in self.number_fields:
            mask = "{:.2f}"
            precision = 2

            if field.upper() in ['AMOUNT']:
                precision = 3
                mask = "{:.3f}"

            text = str(float(value or 0))
            comma = text.find('.')
            text = text[:comma + 1 + precision]
            value = mask.format(float(text))

        if field.upper() in ['NAME']:
            value = "{name}".format(name=value[:127])

        return value

    def get_template(self):
        content = super().get_template()
        return xmltodict.parse(content)

    def process(self, data) -> dict:
        content = super().process(data)
        check = content.get(self.root_tag)
        self.cleanup(check)
        return content

    def post_process(self, content: dict) -> str:
        return xmltodict.unparse(content, encoding='windows-1251')

    def fill_data(self, content: dict, data: dict = None) -> dict:
        content = super().fill_data(content, data)
        check = content.get(self.root_tag)

        if not check:
            raise Exception('Invalid document type')

        self.process_dict(check, data)
        return content

    def cleanup(self, check):
        self.cleanup_dict(check)

    def cleanup_dict(self, check: dict) -> None:
        clone = check.copy()

        for field, item in clone.items():
            if item is None:
                del check[field]
            elif isinstance(item, dict):
                self.cleanup_dict(item)

    def process_dict(self, obj, data) -> None:
        for field in data:
            value = data.get(field)
            if type(value) == dict:
                if obj.get(self.mapper.get(field)) is None:
                    return

                self.process_dict(obj.get(self.mapper.get(field)), data.get(field))
            elif type(value) == list:
                for index, item in enumerate(value, start=0):
                    if obj.get(self.mapper.get(field)) is None:
                        obj[self.mapper.get(field)] = {'ROW': list()}

                    if type(obj.get(self.mapper.get(field)).get('ROW')) != list:
                        obj.get(self.mapper.get(field))['ROW'] = list()

                    if len(obj.get(self.mapper.get(field)).get('ROW')) <= index:
                        obj.get(self.mapper.get(field)).get('ROW').append(
                            {'@ROWNUM': index + 1}
                        )

                    self.process_dict(obj.get(self.mapper.get(field)).get('ROW')[index], item)
            else:
                value = self.get_default_value(field, value)
                value = self.process_value(field, value)
                
                obj[field.upper()] = value

    async def predispatch(self, request: str, body: dict, data: dict) -> dict:
        return await super().predispatch(request, body, data)

    def parse_response(self, data: dict, buffer: bytes) -> bytes:
        buffer = super().parse_response(data, buffer)
        try:
            xml = json.loads(buffer)
        except:
            return buffer

        ticket = xml.get('TICKET')
        obj = dict()
        for key, value in ticket.items():
            if key.startswith('@'):
                continue

            obj[key.lower()] = value

        if data.get('head') is None:
            return buffer

        obj['url'] = Config().get_check_url(
            fn=data.get('head').get('cashregisternum'),
            identifier=ticket.get('ORDERTAXNUM')
        )
        obj['cashregisternum'] = data.get('head').get('cashregisternum')
        obj['autoincrement'] = True

        return json.dumps(obj).encode()
