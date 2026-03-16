import base64
import gzip
import hashlib
import json
import struct

from application.api.common import Documents, Endpoints
from application.connector import Connector
from application.logger import Logger


# Documents that participate in the financial hash chain and include the
# payment total in the CRC computation (Check-class documents and Z-reports).
_FINANCIAL_REQUESTS = frozenset({
    Documents.GoodsCheck,
    Documents.ReturnCheck,
    Documents.ZRepCheck,
    Documents.ServiceDeposit,
    Documents.ServiceIssue,
    Documents.StornoCheck,
})

# Maximum documents per offline package (DFS specification: 100).
_MAX_DOCS_PER_PACKAGE = 100


class Offline(Connector):
    """Connector for ПРРО offline mode.

    Responsibilities
    ----------------
    * Injects offline session parameters (``OfflineSessionId``,
      ``OfflineSeed``, ``OfflineNextLocalNum``, ``PREVDOCHASH``) into each
      document so :class:`XMLTemplate` can compute the correct offline
      ``ORDERTAXNUM``.
    * Tracks the SHA-256 hash chain over financial documents (checks /
      Z-reports) per the DFS specification.
    * Accumulates all signed documents in memory so they can be sent as one
      or more packages to the DFS ``/pck`` endpoint once connectivity is
      restored.
    * Builds and dispatches offline packages, respecting the 100-document
      per-package limit.
    """

    logger = Logger()

    def __init__(self) -> None:
        super().__init__()
        # Per-signer offline state dictionaries.
        self._offline_state: dict = {}

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def get_offline_state(self, signer: str) -> dict:
        """Return (and lazily initialise) the offline state for *signer*."""
        if signer not in self._offline_state:
            self._offline_state[signer] = {
                'OfflineSessionId': None,
                'OfflineSeed': None,
                'OfflineNextLocalNum': 1,
                'prev_doc_hash': None,
                'financial_doc_count': 0,
                'documents': [],
            }
        return self._offline_state[signer]

    def set_offline_session(self, signer: str, session_id: int, seed: int) -> None:
        """Initialise a new offline session for *signer*.

        Call this with the ``OfflineSessionId`` / ``OfflineSeed`` that the
        server returned when the shift was last opened online.
        """
        state = self.get_offline_state(signer)
        state.update({
            'OfflineSessionId': session_id,
            'OfflineSeed': seed,
            'OfflineNextLocalNum': 1,
            'prev_doc_hash': None,
            'financial_doc_count': 0,
            'documents': [],
        })

    # ------------------------------------------------------------------
    # NATS message-handler overrides
    # ------------------------------------------------------------------

    async def predispatch(self, request: str, content: bytes, data: dict) -> bytes:
        """Inject offline session parameters into the document body so that
        :class:`XMLTemplate` can compute the offline ``ORDERTAXNUM``."""
        content = await super().predispatch(request, content, data)
        body = json.loads(content.decode())

        signer = data.get('signer')
        state = self.get_offline_state(signer)

        if state.get('OfflineSessionId') is None:
            return json.dumps(body).encode()

        # Inject session params for ORDERTAXNUM computation.
        body['OfflineSessionId'] = state['OfflineSessionId']
        body['OfflineSeed'] = state['OfflineSeed']
        body['OfflineNextLocalNum'] = state['OfflineNextLocalNum']

        # The previous-document hash is included in the CRC for all
        # financial documents after the first one (the document immediately
        # following OfflineBegin is also excluded because OfflineBegin may
        # be amended with REVOKELASTONLINEDOC).
        is_financial = request in _FINANCIAL_REQUESTS
        if is_financial and state['financial_doc_count'] >= 1 and state.get('prev_doc_hash'):
            body['PREVDOCHASH'] = state['prev_doc_hash']

        return json.dumps(body).encode()

    async def signed_handler(self, request: str, content: bytes, data: dict) -> dict:
        """Offline signed handler: do NOT forward the document to the DFS.

        Instead:
        1. Store the signed document for later package dispatch.
        2. Advance the SHA-256 hash chain for financial documents.
        3. Return a synthetic success response.
        """
        template = self.get_template(request)
        buffer = template.parse_reply(content)

        signer = data.get('signer')
        state = self.get_offline_state(signer)

        # Accumulate the signed document for the offline package.
        state['documents'].append(buffer)

        # Update the hash chain for financial documents.
        is_financial = request in _FINANCIAL_REQUESTS
        if is_financial:
            state['prev_doc_hash'] = hashlib.sha256(buffer).hexdigest()
            state['financial_doc_count'] += 1

        # Every document advances the per-session local counter.
        state['OfflineNextLocalNum'] += 1

        # Build a synthetic response that mirrors the online DFS response.
        ordertaxnum = data.get('offline_ordertaxnum') or ''
        response_content = self._build_offline_response(data, ordertaxnum)

        return {
            'data': {'status_code': 200},
            'content': base64.b64encode(gzip.compress(response_content)).decode(),
        }

    async def postdispatch(self, request: str, content: bytes, data: dict):
        """No state-queue update needed in offline mode."""
        return content

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------

    def _build_offline_response(self, data: dict, ordertaxnum: str) -> bytes:
        """Build a JSON response that mirrors what the online DFS would return.

        The response format matches :meth:`XMLTemplate.parse_response` so that
        the caller can handle online and offline responses identically.
        """
        from application.config import Config

        head = data.get('head') or {}
        cashregisternum = head.get('cashregisternum') or head.get('CASHREGISTERNUM')

        obj = {
            'ordertaxnum': ordertaxnum,
            'ordernum': head.get('ordernum') or head.get('ORDERNUM'),
            'orderdate': head.get('orderdate') or head.get('ORDERDATE'),
            'ordertime': head.get('ordertime') or head.get('ORDERTIME'),
            'cashregisternum': cashregisternum,
            'autoincrement': True,
        }

        if cashregisternum is not None:
            obj['url'] = Config().get_check_url(
                fn=cashregisternum,
                identifier=ordertaxnum,
            )

        return json.dumps(obj).encode()

    # ------------------------------------------------------------------
    # Package building and dispatch
    # ------------------------------------------------------------------

    def build_package(self, documents: list) -> bytes:
        """Serialise *documents* (a list of ``bytes`` objects) into the DFS
        offline package binary format::

            <size:4LE><document_1><size:4LE><document_2>...<size:4LE><document_N>

        Raises :class:`ValueError` if *documents* exceeds the allowed limit.
        """
        if len(documents) > _MAX_DOCS_PER_PACKAGE:
            raise ValueError(
                'Package exceeds the maximum of {max} documents per the DFS '
                'specification; split into multiple packages first.'.format(
                    max=_MAX_DOCS_PER_PACKAGE
                )
            )
        package = b''
        for doc in documents:
            package += struct.pack('<I', len(doc)) + doc
        return package

    def split_into_packages(
        self, documents: list, max_size: int = _MAX_DOCS_PER_PACKAGE
    ) -> list:
        """Split *documents* into batches no larger than *max_size* each.

        Returns a list of lists, ready to be passed to :meth:`build_package`.
        """
        return [
            documents[i: i + max_size]
            for i in range(0, len(documents), max_size)
        ]

    async def send_offline_package(self, signer: str) -> list:
        """Send all accumulated offline documents to the DFS ``/pck`` endpoint.

        Documents are split into batches of at most 100.  Each batch is sent
        in order; if a batch fails the remaining batches are **not** sent (the
        documents are retained for retry).

        Returns a list of ``{'status_code': int, 'content': bytes}`` dicts –
        one entry per batch sent.  When the batch that contains
        ``OfflineEnd`` is accepted, the server also returns the next
        ``OfflineSessionId`` / ``OfflineSeed``; those values are stored and
        the document queue is cleared.
        """
        state = self.get_offline_state(signer)
        documents = list(state.get('documents', []))

        if not documents:
            raise Exception(
                'No offline documents to send for signer: {}'.format(signer)
            )

        batches = self.split_into_packages(documents)
        results = []
        all_sent = True

        for batch in batches:
            package = self.build_package(batch)
            response = self.send_to_dfs(Endpoints.PackageEndpoint, package)
            result = {
                'status_code': response.status_code,
                'content': response.content,
            }
            results.append(result)

            if response.status_code not in (200, 204):
                all_sent = False
                break

            # The server returns new session params in response to the batch
            # that contains the OfflineEnd document.
            try:
                body = response.json()
                new_session_id = body.get('OfflineSessionId')
                new_seed = body.get('OfflineSeed')
                if new_session_id is not None:
                    state.update({
                        'OfflineSessionId': new_session_id,
                        'OfflineSeed': new_seed,
                        'OfflineNextLocalNum': 1,
                        'prev_doc_hash': None,
                        'financial_doc_count': 0,
                    })
            except Exception:
                pass

        if all_sent:
            # All batches sent successfully – clear the accumulated queue.
            state['documents'] = []

        return results

