import json

from application.api.common import Endpoints
from application.templates.template import Template


class JsonTemplate(Template):
    endpoint = Endpoints.CommandEndpoint
    doc_type = 'json'

    def process(self, data) -> dict:
        content = super().process(data)
        return content

    def post_process(self, content: dict) -> str:
        return json.dumps(content)

    def fill_data(self, content, data=None):
        content = super().fill_data(content, data)
        for key in data:
            content[key] = data.get(key)

        return content
