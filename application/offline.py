from application.connector import Connector


class Offline(Connector):
    async def predispatch(self, request: str, content: bytes, data: dict) -> bytes:
        return await super().predispatch(request, content, data)

    async def postdispatch(self, request: str, content: bytes, data: dict):
        return await super().postdispatch(request, content, data)
