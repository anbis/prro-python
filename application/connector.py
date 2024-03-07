import base64
import gzip
import random
import string
import requests
import re
from mergedeep import merge

from application.api.common import Endpoints
from application.intefraces.connector_interface import ConnectorInterface
from application.templates.template import Template


class Connector(ConnectorInterface):
    """Connector Class"""

    def get_template(self, request: str) -> Template:
        return self.template_repository.match(request)

    def parse_message(self, body: bytes) -> dict:
        ungzipped = self.ungzip(body)
        return self.json_parse(ungzipped)

    def parse_content(self, content: bytes) -> bytes:
        decoded = self.base64_decode(content)
        return self.ungzip(decoded)

    def get_signer(self, body: dict, data: dict):
        signer = data.get('signer')
        if signer is None:
            signer = body.get('NumFiscal')
            head = data.get('head')
            head = head if head else body.get('head')

            if head and head.get('cashregisternum') is not None:
                signer = signer if signer else head.get('cashregisternum')

        return signer if isinstance(signer, str) else str(signer or '')
    
    async def predispatch(self, request: str, content: bytes, data: dict) -> bytes:
        template = self.get_template(request)
        body = self.json_parse(content)

        data.update({'signer': self.get_signer(body=body, data=data)})
        body = await template.predispatch(request, body, data)

        return self.json_encode(body)

    async def postdispatch(self, request: str, content: bytes, data: dict):
        return content

    async def command_handler(self, request: str, content: bytes, data: dict) -> dict:
        body = self.json_parse(content)

        template = self.get_template(request)
        template_content = template.get_content(body).decode()

        data.update({'action': 'signed'})
        merge(data, body)

        return {'data': data, 'content': template_content}

    async def signed_handler(self, request: str, content: bytes, data: dict) -> dict:
        template = self.get_template(request)
        buffer = template.parse_reply(content)
        response = self.send_to_dfs(template.get_endpoint(), buffer)
        response_content = template.parse_response(data, response.content)

        result = {
            'data': {'status_code': response.status_code},
            'content': base64.b64encode(gzip.compress(response_content)).decode(),
        }
        return result

    def not_found_handler(self) -> dict:
        result = {
            'data': {'error': 'Request not found'},
            'content': self.base64_encode(self.gzip(b'Request not found')),
        }
        return result

    async def message_handler(self, msg) -> None:
        body: dict = self.parse_message(msg.data)
        data: dict = body.get('data')
        request: str = data.get('request')
        content: bytes = self.parse_content(body.get('content'))

        if data.get('action') == 'command':
            if not data.get('skip_dispatch'):
                content = await self.predispatch(request, content, data)

            result: dict = await self.command_handler(request=request, content=content, data=data)
        elif data.get('action') == 'signed':
            result: dict = await self.signed_handler(request=request, content=content, data=data)

            if not data.get('skip_dispatch'):
                await self.postdispatch(request, content, data)
        else:
            result: dict = self.not_found_handler()
            await self.send_result(msg.reply, result)
            return

        await self.send_result(msg.reply, result)

    async def send_result(self, reply: str, result: dict) -> None:
        response_str = self.json_encode(result)
        gzipped = gzip.compress(response_str)

        if reply:
            await self.nc.publish(reply, gzipped)

    def parse_trash_content(self, data: str):
        content = data

        json_pattern = re.compile(r'({.*})')
        json_match = json_pattern.search(content)

        xml_pattern = re.compile(r'<\?xml(\s|\w|\d|\W)+<\/\w+>')
        xml_match = xml_pattern.search(content)

        if json_match:
            content = json_match.group(1)
        if xml_match:
            content = xml_match.group(0)

        return content

    def send_to_dfs(self, endpoint: str, body: bytes):
        seed = ''.join(random.choices(string.digits, k=18))
        url = Endpoints.Endpoint + endpoint + '?randomseed={seed}'.format(seed=seed)

        self.logger.log(
            [
                '\n>>>>>>>>>>>>>>>>>>>>>>>\nTO_DFS:',
                self.parse_trash_content(body.decode("cp1251", "ignore")),
                'Content-Length:' + str(len(body)),
                '<<<<<<<<<<<<<<<<<<<<<<<\n'
            ]
        )

        response = requests.post(
            url=url,
            data=body,
            headers={
                'Content-Type': 'application/octet-stream',
                'Content-Length': str(len(body)),
            }
        )

        self.logger.log(
            [
                '\n>>>>>>>>>>>>>>>>>>>>>>>\nFROM_DFS:',
                self.parse_trash_content(response.content.decode("utf8", "ignore")),
                '<<<<<<<<<<<<<<<<<<<<<<<\n'
            ]
        )

        return response
