from application.api.common import Commands
from application.templates.json_template import JsonTemplate
from application.templates.respond_encrypted_template import TemplateResponseEncrypted


class ServerStateTemplate(JsonTemplate):
    request = Commands.ServerState
    content = {"Command": Commands.ServerState}


class ObjectsTemplate(JsonTemplate):
    request = Commands.Objects
    content = {"Command": Commands.Objects}


class TransactionsRegistrarStateTemplate(JsonTemplate):
    request = Commands.TransactionsRegistrarState
    content = {"Command": Commands.TransactionsRegistrarState, "NumFiscal": 0, "OfflineSessionId": None,
               "OfflineSeed": None}


class ShiftsTemplate(JsonTemplate):
    request = Commands.Shifts
    content = {"Command": Commands.Shifts, "NumFiscal": 0, "From": None, "To": None}


class DocumentsTemplate(JsonTemplate):
    request = Commands.Documents
    content = {"Command": Commands.Documents, "NumFiscal": 0, "ShiftId": 0, "OpenShiftFiscalNum": None}


class CheckTemplate(JsonTemplate, TemplateResponseEncrypted):
    request = Commands.Check
    content = {"Command": Commands.Check, "RegistrarNumFiscal": 0, "NumFiscal": "0"}
    endings = b'</CHECK>'


class CheckExtTemplate(JsonTemplate):
    request = Commands.CheckExt
    content = {"Command": Commands.CheckExt, "RegistrarNumFiscal": 0, "NumFiscal": "0", "Type": ""}


class ZRepTemplate(JsonTemplate, TemplateResponseEncrypted):
    request = Commands.ZRep
    content = {"Command": Commands.ZRep, "RegistrarNumFiscal": 0, "NumFiscal": "0"}
    endings = b'</ZREP>'


class ZRepExtTemplate(JsonTemplate):
    request = Commands.ZRepExt
    content = {"Command": Commands.ZRepExt, "RegistrarNumFiscal": 0, "NumFiscal": "0", "Type": ""}


class LastShiftTotalsTemplate(JsonTemplate):
    request = Commands.LastShiftTotals
    content = {"Command": Commands.LastShiftTotals, "NumFiscal": 0}
