class Config(object):
    """Config Class"""
    protocol_version = 'v1'
    nats_servers = ['nats://nats.anbis.pp.ua:5222', ]
    request_timeout = 5

    def get_protocol_version(self) -> str:
        return self.protocol_version

    def get_check_url(self, fn, identifier) -> str:
        return 'https://cabinet.tax.gov.ua/cashregs/check?fn={fn}&id={id}'.format(fn=fn, id=identifier)

    def get_nats_servers(self) -> list:
        return self.nats_servers

    def channel_base(self, prefix: str, debug: bool = False):
        return '{debug_prefix}{version}.{prefix}'.format(
            debug_prefix='debug.' if debug else '',
            prefix=prefix,
            version=self.get_protocol_version()
        )

    def get_channel(self, identifier: str, debug: bool = False) -> str:
        return '{base}.{id}'.format(
            base=self.channel_base('direct', debug),
            id=identifier
        )

    def get_channel_config(self, debug: bool = False) -> str:
        return self.channel_base('configuration', debug)

    def get_channel_signer(self, identifier: str, debug: bool = False) -> str:
        debug = False

        return '{base}.{id}'.format(
            base=self.channel_base('signer', debug),
            id=identifier
        )

    def get_channel_queue(self, identifier: str, debug: bool = False) -> str:
        return '{base}.{id}'.format(
            base=self.channel_base('queue', debug),
            id=identifier
        )

    def get_channel_queue_resolver(self, identifier: str, debug: bool = False) -> str:
        return '{base}.{id}'.format(
            base=self.channel_base('queue_resolver', debug),
            id=identifier
        )

    def get_timeout(self) -> int:
        return self.request_timeout
