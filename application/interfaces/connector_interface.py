class ConnectorInterface:
    template_repository = None
    debug = None

    def json_parse(self, data: bytes) -> dict:
        pass

    def json_encode(self, obj: dict) -> bytes:
        pass

    def ungzip(self, data: bytes) -> bytes:
        pass

    def base64_decode(self, string: bytes) -> bytes:
        pass

    def base64_encode(self, string: bytes) -> str:
        pass

    def gzip(self, content: bytes) -> bytes:
        pass