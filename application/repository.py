from application.api.xml.templates import *
from application.api.json.templates import *
from application.templates.template import Template


class TemplateRepository(object):
    templates = []

    def __init__(self) -> None:
        super().__init__()
        self.templates.append(ServerStateTemplate())
        self.templates.append(ObjectsTemplate())
        self.templates.append(ShiftsTemplate())
        self.templates.append(DocumentsTemplate())
        self.templates.append(CheckTemplate())
        self.templates.append(ZRepTemplate())
        self.templates.append(TransactionsRegistrarStateTemplate())
        self.templates.append(LastShiftTotalsTemplate())
        self.templates.append(ZRepCheckTemplate())
        self.templates.append(ServiceDepositTemplate())
        self.templates.append(ServiceIssueTemplate())
        self.templates.append(OpenShiftCheckTemplate())
        self.templates.append(GoodsCheckTemplate())
        self.templates.append(StornoCheckTemplate())
        self.templates.append(ReturnCheckTemplate())
        self.templates.append(CloseShiftCheckTemplate())
        self.templates.append(OfflineBeginTemplate())
        self.templates.append(OfflineEndTemplate())
        self.templates.append(ZRepExtTemplate())
        self.templates.append(CheckExtTemplate())

    def match(self, request: str) -> Template:
        for template in self.templates:
            found = template.match(request)
            if found:
                return found

        raise Exception('Template not found')
