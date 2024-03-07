from __future__ import annotations

import base64
import gzip
import os


class Template(object):
    request = ''
    endpoint = None
    doc_type = None
    content = None
    variables = {}
    endings = b'NOT_EXIST_PART'

    def match(self, request: str) -> Template:
        if request == self.request:
            result = self
        else:
            result = None

        return result

    def get_endpoint(self):
        return self.endpoint

    def get_type(self) -> str:
        return self.doc_type

    def get_filename(self):
        return '{dir}/{path}/{template}.{extension}'.format(
            path='application/api/xml/templates',
            dir=os.getcwd(),
            template=self.request,
            extension=self.get_type()
        )

    def get_template(self):
        if self.content is not None:
            result = self.content
        else:
            with open(self.get_filename(), 'r') as template:
                result = template.read()
                result = result.format(**self.variables)

        return result

    def get_content(self, data=None) -> bytes:
        if data is None:
            data = {}
        processed = self.process(data)
        content = self.post_process(processed).encode('cp1251')
        gzipped = gzip.compress(content)
        return base64.b64encode(gzipped)

    def post_process(self, content: dict) -> str:
        pass

    def process(self, data) -> dict:
        template = self.get_template()
        return self.fill_data(template, data)

    def fill_data(self, content: dict, data: dict = None) -> dict:
        return content

    def parse_reply(self, buffer: bytes) -> bytes:
        return buffer

    def parse_response(self, data: dict, buffer: bytes) -> bytes:
        return buffer

    async def predispatch(self, request: str, body: dict, data: dict) -> dict:
        return body
