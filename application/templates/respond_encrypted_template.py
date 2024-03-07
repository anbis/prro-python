import json

import xmltodict

from application.templates.template import Template


class TemplateResponseEncrypted(Template):
    def parse_response(self, data: dict, buffer: bytes) -> bytes:
        buffer = super().parse_response(data, buffer)

        b_array = bytearray(buffer)
        ending_p = b_array.find(self.endings)

        if ending_p < 0:
            return buffer

        start_p = b_array.find(b'<?xml')
        end_p = b_array.find(self.endings) + len(self.endings)

        if start_p < 0 or end_p < 0:
            return buffer

        buffer = b_array[start_p:end_p]

        try:
            xml = xmltodict.parse(buffer)
        except:
            return buffer

        return json.dumps(xml).encode()
