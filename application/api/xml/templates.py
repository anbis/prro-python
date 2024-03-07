from application.api.common import CheckDocumentType, Documents, CheckDocumentSubType, CashShiftTotalsPayForm, \
    CardShiftTotalsPayForm
from application.templates.offline_templates import OfflineTemplate
from application.templates.xml_template import XMLTemplate


class OpenShiftCheckTemplate(XMLTemplate):
    request = Documents.OpenShiftCheck
    variables = {
        'doctype': CheckDocumentType.OpenShift,
    }


class CloseShiftCheckTemplate(XMLTemplate):
    request = Documents.CloseShiftCheck
    variables = {
        'doctype': CheckDocumentType.CloseShift,
    }


class ServiceDepositTemplate(XMLTemplate):
    request = Documents.ServiceDeposit
    variables = {
        'doctype': CheckDocumentType.SaleGoods,
        'docsubtype': CheckDocumentSubType.ServiceDeposit
    }


class ServiceIssueTemplate(XMLTemplate):
    request = Documents.ServiceIssue
    variables = {
        'doctype': CheckDocumentType.SaleGoods,
        'docsubtype': CheckDocumentSubType.ServiceIssue
    }


class StornoCheckTemplate(XMLTemplate):
    request = Documents.StornoCheck
    variables = {
        'doctype': CheckDocumentType.SaleGoods,
        'docsubtype': CheckDocumentSubType.CheckStorno
    }


class OfflineBeginTemplate(OfflineTemplate):
    request = Documents.OfflineBegin
    variables = {
        'doctype': CheckDocumentType.OfflineBegin,
    }


class OfflineEndTemplate(OfflineTemplate):
    request = Documents.OfflineEnd
    variables = {
        'doctype': CheckDocumentType.OfflineEnd,
    }


class ZRepCheckTemplate(XMLTemplate):
    request = Documents.ZRepCheck

    mapper = {
        'head': 'ZREPHEAD',
        'zrealiz': 'ZREPREALIZ',
        'zreturn': 'ZREPRETURN',
        'zbody': 'ZREPBODY',
        'payforms': 'PAYFORMS',
        'taxes': 'TAXES',
    }
    root_tag = 'ZREP'

    def cleanup(self, check):
        zrealiz = check.get(self.mapper.get('zrealiz'))
        zrealiz['SUM'] = zrealiz.get('SUM') or 0
        zrealiz['ORDERSCNT'] = self.process_value('ORDERSCNT', zrealiz.get('ORDERSCNT') or 0)

        zreturn = check.get(self.mapper.get('zreturn'))
        zreturn['SUM'] = zreturn.get('SUM') or 0
        zreturn['ORDERSCNT'] = self.process_value('ORDERSCNT', zreturn.get('ORDERSCNT') or 0)

        zbody = check.get(self.mapper.get('zbody'))
        zbody['SERVICEINPUT'] = self.process_value('SERVICEINPUT', zbody.get('SERVICEINPUT') or 0)
        zbody['SERVICEOUTPUT'] = self.process_value('SERVICEOUTPUT', zbody.get('SERVICEOUTPUT') or 0)

        super().cleanup(check)

    async def predispatch(self, request: str, body: dict, data: dict) -> dict:
        return await super().predispatch(request, body, data)


class GoodsCheckTemplate(XMLTemplate):
    request = Documents.GoodsCheck
    variables = {
        'doctype': CheckDocumentType.SaleGoods,
        'docsubtype': CheckDocumentSubType.CheckGoods,
    }

    def fill_data(self, content, data=None) -> dict:
        content = super().fill_data(content, data)
        check = content.get('CHECK')

        self.prepare_pay(check.get('CHECKPAY'), data)
        return content

    def get_pay_by_code(self, code):
        for pay in [CashShiftTotalsPayForm(), CardShiftTotalsPayForm()]:
            if pay.Code == code:
                return pay

        raise Exception('Wrong pay code')

    def prepare_pay(self, obj, data):
        for index, pay in enumerate(data.get('pay'), start=0):
            method = self.get_pay_by_code(pay.get('payformcd'))
            obj['ROW'][index]['PAYFORMCD'] = method.Code
            obj['ROW'][index]['PAYFORMNM'] = method.Name


class ReturnCheckTemplate(GoodsCheckTemplate):
    request = Documents.ReturnCheck
    variables = {
        'doctype': CheckDocumentType.SaleGoods,
        'docsubtype': CheckDocumentSubType.CheckReturn,
    }
