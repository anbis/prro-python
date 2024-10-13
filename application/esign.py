import gzip
import json
import re
from application.connector import Connector
import base64
import requests

class eSign(Connector):
    def __init__(self) -> None:
        super().__init__()
        
        self.url = 'https://sign.e-life.com.ua/api/EDG/Sign'
        
    async def command_handler(self, request: str, content: bytes, data: dict) -> dict:
        processed = await super().command_handler(request, content, data)
        
        if (data.get('args') is None or (data.get('args') and data.get('args').get('edrpou') is None)):
            return processed

        document = gzip.decompress(base64.b64decode(processed.get('content')));
        template = processed.get('template')
        
        edrpou = data.get('args').get('edrpou')
        password = data.get('args').get('password')
        
        signed = self.singContent(document, edrpou, password)
        
        response = super().send_to_dfs(template.get_endpoint(), signed)
        response_content = template.parse_response(data, response.content)

        result = {
            'data': {'status_code': response.status_code},
            'content': base64.b64encode(gzip.compress(response_content)).decode(),
        }
        return result
    
    def singContent(self, content: bytes, edrpou: str, password: str):
        response = requests.post(
            url=self.url,
            json={
                "content": base64.b64encode(content).decode(),
                "edrpou": edrpou,
                "password": password,
                "signatureParameters": {
                    "addContentTimeAttribute": False
                }
            },
            headers={
                'Content-Type': 'application/json'
            }
        )

        result = response.json()
        content = base64.b64decode(result.get('signature'))

        return content
