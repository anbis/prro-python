import base64

import requests

if __name__ == '__main__':
    response = requests.post(
        url='https://sign.e-life.com.ua/api/EDG/Sign',
        json={
            "content": "eyJDb21tYW5kIjogIk9iamVjdHMifQ==",
            "edrpou": "NV411165",
            "password": "Aa1234567",
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

    response = requests.post(
        url='http://fs.tax.gov.ua:8609/fs/cmd',
        data=content,
        headers={
            'Content-Type': 'application/octet-stream',
            'Content-Length': str(len(content)),
        }
    )

    pass

