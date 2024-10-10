import json
import re
from application.connector import Connector
import base64
import requests

class eSign(Connector):
    def __init__(self) -> None:
        super().__init__()
        
        self.url = 'https://sign.e-life.com.ua/api/EDG/Sign'
        self.certs = {
            'БІСОВЕЦЬКА': {
                "edrpou": "NV411165",
                "password": "Aa1234567"
            },
            'БІСОВЕЦЬКИЙ': {
                "edrpou": "NV411165",
                "password": "Aa1234567"
            }
        }
        
    def send_to_dfs(self, endpoint: str, body: bytes):
        try:
            decoded = body.decode("utf8", "ignore")
            
            # if 'БІСОВЕЦЬКА' in decoded:
            #     edrpou = self.certs['БІСОВЕЦЬКА']['edrpou']
            #     password = self.certs['БІСОВЕЦЬКА']['password']
            # el
            if 'БІСОВЕЦЬКИЙ' in decoded:
                edrpou = self.certs['БІСОВЕЦЬКИЙ']['edrpou']
                password = self.certs['БІСОВЕЦЬКИЙ']['password']
            else:
                return super().send_to_dfs(endpoint, body)
                
            decoded = self.parse_trash_content(decoded)
            body64 = base64.b64encode(decoded.encode())
            body = self.singContent(body64, edrpou, password)
        except Exception as e:
            pass
            
        return super().send_to_dfs(endpoint, body)
    
    def singContent(self, content: bytes, edrpou: str, password: str):
        response = requests.post(
            url=self.url,
            json={
                "content": content.decode(),
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
