from application.templates.xml_template import XMLTemplate


class OfflineTemplate(XMLTemplate):
    """Base template for offline session document types (OfflineBegin /
    OfflineEnd).

    Offline fiscal number generation (ORDERTAXNUM) is handled automatically
    by the parent :class:`XMLTemplate` whenever ``OfflineSessionId`` is
    present in the document data injected by the :class:`Offline` connector.
    """
