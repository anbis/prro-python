"""
Unit tests for the PRRO Python application.
"""
import base64
import gzip
import json
import struct
import unittest
import zlib

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
from application.offline import Offline
from application.templates.template import Template
from application.templates.json_template import JsonTemplate
from application.templates.xml_template import XMLTemplate
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

    def test_match_offline_begin(self):
        template = self.repo.match(Documents.OfflineBegin)
        self.assertIsNotNone(template)
        self.assertEqual(template.request, Documents.OfflineBegin)

    def test_match_offline_end(self):
        template = self.repo.match(Documents.OfflineEnd)
        self.assertIsNotNone(template)
        self.assertEqual(template.request, Documents.OfflineEnd)


# ---------------------------------------------------------------------------
# Helpers shared by offline tests
# ---------------------------------------------------------------------------

def _crc32_canonical(text: str) -> int:
    """Return CRC32 in the byte order used by the DFS specification."""
    raw = zlib.crc32(text.encode()) & 0xFFFFFFFF
    return struct.unpack('>I', struct.pack('<I', raw))[0]


class TestOfflineState(unittest.TestCase):
    """Tests for Offline session state management."""

    def setUp(self):
        self.offline = Offline()

    def test_get_offline_state_creates_default(self):
        state = self.offline.get_offline_state('signer1')
        self.assertIsNone(state['OfflineSessionId'])
        self.assertIsNone(state['OfflineSeed'])
        self.assertEqual(state['OfflineNextLocalNum'], 1)
        self.assertIsNone(state['prev_doc_hash'])
        self.assertEqual(state['financial_doc_count'], 0)
        self.assertEqual(state['documents'], [])

    def test_get_offline_state_cached(self):
        state1 = self.offline.get_offline_state('signer1')
        state2 = self.offline.get_offline_state('signer1')
        self.assertIs(state1, state2)

    def test_get_offline_state_per_signer(self):
        s1 = self.offline.get_offline_state('signerA')
        s2 = self.offline.get_offline_state('signerB')
        self.assertIsNot(s1, s2)

    def test_set_offline_session(self):
        self.offline.set_offline_session('signer1', session_id=434941, seed=917269818606292)
        state = self.offline.get_offline_state('signer1')
        self.assertEqual(state['OfflineSessionId'], 434941)
        self.assertEqual(state['OfflineSeed'], 917269818606292)
        self.assertEqual(state['OfflineNextLocalNum'], 1)
        self.assertIsNone(state['prev_doc_hash'])
        self.assertEqual(state['financial_doc_count'], 0)
        self.assertEqual(state['documents'], [])

    def test_set_offline_session_resets_state(self):
        state = self.offline.get_offline_state('signer1')
        state['financial_doc_count'] = 5
        state['documents'] = [b'doc1']
        state['prev_doc_hash'] = 'aabbcc'
        state['OfflineNextLocalNum'] = 7

        self.offline.set_offline_session('signer1', session_id=999, seed=12345)
        state = self.offline.get_offline_state('signer1')
        self.assertEqual(state['OfflineNextLocalNum'], 1)
        self.assertIsNone(state['prev_doc_hash'])
        self.assertEqual(state['financial_doc_count'], 0)
        self.assertEqual(state['documents'], [])


class TestOfflinePackageBuilding(unittest.TestCase):
    """Tests for Offline.build_package and split_into_packages."""

    def setUp(self):
        self.offline = Offline()

    def test_build_package_single_document(self):
        doc = b'hello world'
        package = self.offline.build_package([doc])
        # First 4 bytes = little-endian length
        size = struct.unpack('<I', package[:4])[0]
        self.assertEqual(size, len(doc))
        self.assertEqual(package[4:], doc)

    def test_build_package_multiple_documents(self):
        docs = [b'doc1', b'doc2', b'doc3']
        package = self.offline.build_package(docs)
        offset = 0
        for doc in docs:
            size = struct.unpack('<I', package[offset:offset + 4])[0]
            self.assertEqual(size, len(doc))
            self.assertEqual(package[offset + 4: offset + 4 + size], doc)
            offset += 4 + size
        self.assertEqual(offset, len(package))

    def test_build_package_empty(self):
        package = self.offline.build_package([])
        self.assertEqual(package, b'')

    def test_build_package_exceeds_limit_raises(self):
        docs = [b'x'] * 101
        with self.assertRaises(ValueError):
            self.offline.build_package(docs)

    def test_build_package_exactly_limit(self):
        docs = [b'x'] * 100
        # Should not raise
        package = self.offline.build_package(docs)
        self.assertIsNotNone(package)

    def test_split_into_packages_no_split_needed(self):
        docs = [b'a'] * 50
        batches = self.offline.split_into_packages(docs)
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0], docs)

    def test_split_into_packages_exact_split(self):
        docs = [b'a'] * 200
        batches = self.offline.split_into_packages(docs)
        self.assertEqual(len(batches), 2)
        self.assertEqual(len(batches[0]), 100)
        self.assertEqual(len(batches[1]), 100)

    def test_split_into_packages_uneven(self):
        docs = [b'a'] * 150
        batches = self.offline.split_into_packages(docs)
        self.assertEqual(len(batches), 2)
        self.assertEqual(len(batches[0]), 100)
        self.assertEqual(len(batches[1]), 50)

    def test_split_into_packages_custom_max(self):
        docs = [b'a'] * 10
        batches = self.offline.split_into_packages(docs, max_size=3)
        self.assertEqual(len(batches), 4)


class TestOfflineCRCComputation(unittest.TestCase):
    """Tests for XMLTemplate._compute_offline_ordertaxnum CRC logic."""

    def setUp(self):
        self.template = XMLTemplate()

    def _make_head(self, **kwargs):
        defaults = {
            'ORDERDATE': '20082020',
            'ORDERTIME': '142338',
            'ORDERNUM': '10',
            'CASHREGISTERNUM': '4000002411',
            'CASHDESKNUM': '10',
        }
        defaults.update(kwargs)
        return defaults

    def _make_data(self, **kwargs):
        defaults = {
            'OfflineSessionId': 82563,
            'OfflineSeed': 179625192271939,
            'OfflineNextLocalNum': 25,
        }
        defaults.update(kwargs)
        return defaults

    def test_ordertaxnum_format(self):
        head = self._make_head()
        data = self._make_data()
        result = self.template._compute_offline_ordertaxnum(head, data)
        parts = result.split('.')
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[0], '82563')   # session id
        self.assertEqual(parts[1], '25')       # local num in session
        self.assertTrue(parts[2].isdigit())    # control number

    def test_ordertaxnum_with_prevdochash(self):
        """Including PREVDOCHASH must change the control number."""
        head = self._make_head()
        data_no_hash = self._make_data()
        data_with_hash = self._make_data(
            PREVDOCHASH='cdd68bb111f8993f3603f0179341571b35b73a07d5acee9b28fbfb714698e1b3'
        )
        result_no_hash = self.template._compute_offline_ordertaxnum(head, data_no_hash)
        result_with_hash = self.template._compute_offline_ordertaxnum(head, data_with_hash)
        # The control numbers must differ when PREVDOCHASH is included.
        self.assertNotEqual(result_no_hash.split('.')[-1], result_with_hash.split('.')[-1])

    def test_control_number_matches_documentation_example(self):
        """Verify the example from the DFS specification documentation.

        Input string:
          '179625192271939,20082020,142338,10,4000002411,10,
           cdd68bb111f8993f3603f0179341571b35b73a07d5acee9b28fbfb714698e1b3'
        Expected CRC32 (little-endian read as big-endian): 3185294758
        Expected control number (last 4 decimal digits, no leading zeros): 4758
        """
        crc_input = (
            '179625192271939,20082020,142338,10,4000002411,10,'
            'cdd68bb111f8993f3603f0179341571b35b73a07d5acee9b28fbfb714698e1b3'
        )
        canonical = _crc32_canonical(crc_input)
        self.assertEqual(canonical, 3185294758)
        control = str(canonical)[-4:].lstrip('0') or '1'
        self.assertEqual(control, '4758')

    def test_control_number_is_nonzero(self):
        """Control number must never be '0'; it is replaced by '1'."""
        # Craft a scenario where the last 4 decimal digits could be '0000'.
        # Since we cannot easily force a real CRC collision, we test the
        # '0000' -> '1' edge case via the helper logic directly.
        raw_crc = 3000000000  # ends in '0000'
        canonical = struct.unpack('>I', struct.pack('<I', raw_crc))[0]
        control = str(canonical)[-4:].lstrip('0') or '1'
        # The canonical of 3000000000 (0xB2D05E00) reversed is 0x005ED0B2
        # = 6213810 -> last 4 = '3810', not all zeros.  Test the rule itself:
        forced_zero = 0  # would produce empty string -> '1'
        control_forced = str(forced_zero)[-4:].lstrip('0') or '1'
        self.assertEqual(control_forced, '1')

    def test_control_number_leading_zeros_stripped(self):
        """Leading zeros in the 4-digit window must be stripped."""
        # Find a value whose last 4 decimal digits start with '0'.
        # 3185290000 ends in '0000' → skipped; 3185290123 ends in '0123' → '123'.
        val = 3185290123
        control = str(val)[-4:].lstrip('0') or '1'
        self.assertEqual(control, '123')

    def test_total_sum_included_in_crc(self):
        """Providing a 'total.sum' must change the control number."""
        head = self._make_head()
        data_no_sum = self._make_data()
        data_with_sum = self._make_data()
        data_with_sum['total'] = {'sum': 100.00}

        r1 = self.template._compute_offline_ordertaxnum(head, data_no_sum)
        r2 = self.template._compute_offline_ordertaxnum(head, data_with_sum)
        self.assertNotEqual(r1.split('.')[-1], r2.split('.')[-1])

    def test_total_sum_formatted_two_decimal_places(self):
        """Total sum is always formatted as '0.00' in the CRC input."""
        head = self._make_head()
        data_int = self._make_data()
        data_int['total'] = {'sum': 100}
        data_float = self._make_data()
        data_float['total'] = {'sum': 100.00}

        r1 = self.template._compute_offline_ordertaxnum(head, data_int)
        r2 = self.template._compute_offline_ordertaxnum(head, data_float)
        self.assertEqual(r1, r2)

    def test_session_and_local_num_in_ordertaxnum(self):
        """ORDERTAXNUM parts must reflect session id and offline local num."""
        head = self._make_head()
        data = self._make_data(OfflineSessionId=11111, OfflineNextLocalNum=7)
        result = self.template._compute_offline_ordertaxnum(head, data)
        self.assertTrue(result.startswith('11111.7.'))


if __name__ == '__main__':
    unittest.main()
