"""
Unit tests for the PRRO Python application.
"""
import base64
import gzip
import json
import unittest

from application.api.common import (
    Commands,
    Documents,
    DocumentClass,
    CheckDocumentSubType,
    CheckDocumentType,
    Endpoints,
    ErrorCode,
    ResultCode,
)
from application.config import Config
from application.interfaces.connector_interface import ConnectorInterface
from application.templates.template import Template
from application.templates.json_template import JsonTemplate
from application.repository import TemplateRepository


class TestConfig(unittest.TestCase):
    """Tests for the Config class."""

    def setUp(self):
        self.config = Config()

    def test_protocol_version(self):
        self.assertEqual(self.config.get_protocol_version(), 'v1')

    def test_nats_servers_is_list(self):
        servers = self.config.get_nats_servers()
        self.assertIsInstance(servers, list)
        self.assertGreater(len(servers), 0)

    def test_channel_base_no_debug(self):
        channel = self.config.channel_base('direct', debug=False)
        self.assertEqual(channel, 'v1.direct')

    def test_channel_base_debug(self):
        channel = self.config.channel_base('direct', debug=True)
        self.assertEqual(channel, 'debug.v1.direct')

    def test_get_channel(self):
        channel = self.config.get_channel('abc123', debug=False)
        self.assertEqual(channel, 'v1.direct.abc123')

    def test_get_channel_debug(self):
        channel = self.config.get_channel('abc123', debug=True)
        self.assertEqual(channel, 'debug.v1.direct.abc123')

    def test_get_channel_config(self):
        channel = self.config.get_channel_config(debug=False)
        self.assertEqual(channel, 'v1.configuration')

    def test_get_channel_signer(self):
        # signer channel always uses debug=False internally
        channel = self.config.get_channel_signer('signer1', debug=True)
        self.assertEqual(channel, 'v1.signer.signer1')

    def test_get_channel_queue(self):
        channel = self.config.get_channel_queue('q1', debug=False)
        self.assertEqual(channel, 'v1.queue.q1')

    def test_get_channel_queue_resolver(self):
        channel = self.config.get_channel_queue_resolver('q1', debug=False)
        self.assertEqual(channel, 'v1.queue_resolver.q1')

    def test_get_timeout(self):
        self.assertEqual(self.config.get_timeout(), 5)

    def test_get_check_url(self):
        url = self.config.get_check_url(fn='123', identifier='abc')
        self.assertIn('cabinet.tax.gov.ua', url)
        self.assertIn('fn=123', url)
        self.assertIn('id=abc', url)


class TestApiCommon(unittest.TestCase):
    """Tests for the API common enums and constants."""

    def test_document_class_values(self):
        self.assertEqual(DocumentClass.Check, 0)
        self.assertEqual(DocumentClass.ZRep, 1)

    def test_check_document_sub_type_values(self):
        self.assertEqual(CheckDocumentSubType.CheckGoods, 0)
        self.assertEqual(CheckDocumentSubType.CheckReturn, 1)
        self.assertEqual(CheckDocumentSubType.ServiceDeposit, 2)
        self.assertEqual(CheckDocumentSubType.AdditionalDeposit, 3)
        self.assertEqual(CheckDocumentSubType.ServiceIssue, 4)
        self.assertEqual(CheckDocumentSubType.CheckStorno, 5)

    def test_check_document_type_values(self):
        self.assertEqual(CheckDocumentType.SaleGoods, 0)
        self.assertEqual(CheckDocumentType.TransferFunds, 1)
        self.assertEqual(CheckDocumentType.OpenShift, 100)
        self.assertEqual(CheckDocumentType.CloseShift, 101)
        self.assertEqual(CheckDocumentType.OfflineBegin, 102)
        self.assertEqual(CheckDocumentType.OfflineEnd, 103)

    def test_commands_strings(self):
        self.assertEqual(Commands.ServerState, 'ServerState')
        self.assertEqual(Commands.Check, 'Check')
        self.assertEqual(Commands.ZRep, 'ZRep')
        self.assertEqual(Commands.TransactionsRegistrarState, 'TransactionsRegistrarState')
        self.assertEqual(Commands.LastShiftTotals, 'LastShiftTotals')

    def test_documents_strings(self):
        self.assertEqual(Documents.ZRepCheck, 'ZRepCheck')
        self.assertEqual(Documents.GoodsCheck, 'GoodsCheck')
        self.assertEqual(Documents.OpenShiftCheck, 'OpenShiftCheck')
        self.assertEqual(Documents.CloseShiftCheck, 'CloseShiftCheck')

    def test_endpoints(self):
        self.assertTrue(Endpoints.Endpoint.startswith('http://'))
        self.assertEqual(Endpoints.DocumentEndpoint, '/doc')
        self.assertEqual(Endpoints.CommandEndpoint, '/cmd')
        self.assertEqual(Endpoints.PackageEndpoint, '/pck')

    def test_error_code_ok(self):
        self.assertEqual(ErrorCode.Ok, 0)

    def test_result_codes(self):
        self.assertEqual(ResultCode.OKCode, 200)
        self.assertEqual(ResultCode.NoContentCode, 204)
        self.assertEqual(ResultCode.BadRequestCode, 400)


class TestConnectorInterface(unittest.TestCase):
    """Tests for the ConnectorInterface base class."""

    def setUp(self):
        self.interface = ConnectorInterface()

    def test_json_parse_returns_none(self):
        self.assertIsNone(self.interface.json_parse(b'{}'))

    def test_json_encode_returns_none(self):
        self.assertIsNone(self.interface.json_encode({}))

    def test_ungzip_returns_none(self):
        self.assertIsNone(self.interface.ungzip(b'data'))

    def test_base64_decode_returns_none(self):
        self.assertIsNone(self.interface.base64_decode(b'data'))

    def test_base64_encode_returns_none(self):
        self.assertIsNone(self.interface.base64_encode(b'data'))

    def test_gzip_returns_none(self):
        self.assertIsNone(self.interface.gzip(b'data'))


class TestTemplate(unittest.TestCase):
    """Tests for the base Template class."""

    def setUp(self):
        self.template = Template()

    def test_match_correct_request(self):
        self.template.request = 'TestRequest'
        result = self.template.match('TestRequest')
        self.assertIs(result, self.template)

    def test_match_wrong_request(self):
        self.template.request = 'TestRequest'
        result = self.template.match('OtherRequest')
        self.assertIsNone(result)

    def test_get_endpoint(self):
        self.template.endpoint = '/test'
        self.assertEqual(self.template.get_endpoint(), '/test')

    def test_get_type(self):
        self.template.doc_type = 'json'
        self.assertEqual(self.template.get_type(), 'json')

    def test_fill_data_returns_content(self):
        result = self.template.fill_data('template_content', {})
        self.assertEqual(result, 'template_content')

    def test_parse_reply_passthrough(self):
        data = b'some bytes'
        result = self.template.parse_reply(data)
        self.assertEqual(result, data)

    def test_parse_response_passthrough(self):
        data = b'response bytes'
        result = self.template.parse_response({}, data)
        self.assertEqual(result, data)


class TestJsonTemplate(unittest.TestCase):
    """Tests for the JsonTemplate class."""

    def setUp(self):
        self.template = JsonTemplate()
        self.template.content = {"Command": "TestCmd", "Value": None}

    def test_post_process_returns_json_string(self):
        content = {"key": "value"}
        result = self.template.post_process(content)
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), content)

    def test_fill_data_merges_fields(self):
        template_content = {"Command": "TestCmd", "Value": None}
        data = {"Value": 42, "Extra": "hello"}
        result = self.template.fill_data(template_content, data)
        self.assertEqual(result.get("Value"), 42)
        self.assertEqual(result.get("Extra"), "hello")

    def test_fill_data_preserves_existing_keys(self):
        template_content = {"Command": "TestCmd", "Value": None}
        data = {"Value": 99}
        result = self.template.fill_data(template_content, data)
        self.assertEqual(result.get("Command"), "TestCmd")

    def test_get_content_returns_base64_gzipped_bytes(self):
        result = self.template.get_content({"Value": 1})
        self.assertIsInstance(result, bytes)
        # Should be decodable as base64-encoded gzip
        decoded = base64.b64decode(result)
        decompressed = gzip.decompress(decoded)
        obj = json.loads(decompressed.decode('cp1251'))
        self.assertIn("Command", obj)


class TestTemplateRepository(unittest.TestCase):
    """Tests for the TemplateRepository class."""

    def setUp(self):
        self.repo = TemplateRepository()

    def test_match_server_state(self):
        template = self.repo.match(Commands.ServerState)
        self.assertIsNotNone(template)
        self.assertEqual(template.request, Commands.ServerState)

    def test_match_check(self):
        template = self.repo.match(Commands.Check)
        self.assertIsNotNone(template)
        self.assertEqual(template.request, Commands.Check)

    def test_match_zrep(self):
        template = self.repo.match(Commands.ZRep)
        self.assertIsNotNone(template)
        self.assertEqual(template.request, Commands.ZRep)

    def test_match_goods_check(self):
        template = self.repo.match(Documents.GoodsCheck)
        self.assertIsNotNone(template)
        self.assertEqual(template.request, Documents.GoodsCheck)

    def test_match_zrep_check(self):
        template = self.repo.match(Documents.ZRepCheck)
        self.assertIsNotNone(template)
        self.assertEqual(template.request, Documents.ZRepCheck)

    def test_match_open_shift(self):
        template = self.repo.match(Documents.OpenShiftCheck)
        self.assertIsNotNone(template)

    def test_match_close_shift(self):
        template = self.repo.match(Documents.CloseShiftCheck)
        self.assertIsNotNone(template)

    def test_match_service_deposit(self):
        template = self.repo.match(Documents.ServiceDeposit)
        self.assertIsNotNone(template)

    def test_match_service_issue(self):
        template = self.repo.match(Documents.ServiceIssue)
        self.assertIsNotNone(template)

    def test_match_not_found_raises(self):
        with self.assertRaises(Exception) as ctx:
            self.repo.match('NonExistentRequest')
        self.assertIn('not found', str(ctx.exception).lower())

    def test_match_transactions_registrar_state(self):
        template = self.repo.match(Commands.TransactionsRegistrarState)
        self.assertIsNotNone(template)

    def test_match_last_shift_totals(self):
        template = self.repo.match(Commands.LastShiftTotals)
        self.assertIsNotNone(template)


if __name__ == '__main__':
    unittest.main()
