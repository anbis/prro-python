import logging
import json


class Logger(object):

    def __init__(self) -> None:
        super().__init__()
        options = {
            'filename': 'debug.log',
            'level': logging.WARNING,
            'format': '%(message)s'
        }
        logging.basicConfig(
            **options
        )

    def log(self, data=None):
        if data is None:
            data = []
        if isinstance(data, str):
            data = [data]

        for item in data:
            if isinstance(item, dict):
                result = json.dumps(item)
            elif isinstance(item, bytes):
                result = item.decode()
            elif isinstance(item, str):
                result = item
            else:
                result = str(item)

            print(result)
            logging.warning(result)
