class DocumentClass(object):
    """DocumentClass Class"""
    # Чек
    Check = 0

    # Z - звіт
    ZRep = 1


class CheckDocumentSubType(object):
    """CheckDocumentSubType Class"""
    # Касовий чек (реалізація)
    CheckGoods = 0

    # Видатковий чек (повернення)
    CheckReturn = 1

    # Чек операції «службове внесення» / «отримання авансу»
    ServiceDeposit = 2

    # Чек операції «отримання підкріплення»
    AdditionalDeposit = 3

    # Чек операції «службова видача» / «інкасація»
    ServiceIssue = 4

    # Чек сторнування попереднього чека
    CheckStorno = 5


class CheckDocumentType(object):
    """CheckDocumentType Class"""
    # Чек реалізації товарів / послуг
    SaleGoods = 0

    # Чек переказу коштів
    TransferFunds = 1

    # Чек операції обміну валюти
    CurrencyExchange = 2

    # Чек видачі готівки
    CashWithdrawal = 3

    # Відкриття зміни
    OpenShift = 100

    # Закриття зміни
    CloseShift = 101

    # Початок офлайн сесії
    OfflineBegin = 102

    # Завершення офлайн сесії
    OfflineEnd = 103


class ShiftTotalsPayForm(object):
    """ShiftTotalsPayForm Class"""
    # Код формы оплаты
    Code = None

    # Ім'я форми оплати
    Name = None


class CashShiftTotalsPayForm(ShiftTotalsPayForm):
    """CashShiftTotalsPayForm Class"""
    Code = 0
    Name = 'ГОТІВКА'


class CardShiftTotalsPayForm(ShiftTotalsPayForm):
    """CardShiftTotalsPayForm Class"""
    Code = 1
    Name = 'КАРТКА'


class Commands(object):
    """Commands Class"""
    ServerState = 'ServerState'
    Objects = 'Objects'
    TransactionsRegistrarState = 'TransactionsRegistrarState'
    Check = 'Check'
    CheckExt = 'CheckExt'
    ZRep = 'ZRep'
    ZRepExt = 'ZRepExt'
    Shifts = 'Shifts'
    Documents = 'Documents'
    LastShiftTotals = 'LastShiftTotals'
    DocumentInfoByLocalNum = 'DocumentInfoByLocalNum'


class Documents(object):
    ServiceDeposit = 'ServiceDeposit'
    ServiceIssue = 'ServiceIssue'
    ZRepCheck = 'ZRepCheck'
    OpenShiftCheck = 'OpenShiftCheck'
    GoodsCheck = 'GoodsCheck'
    ReturnCheck = 'CheckReturn'
    StornoCheck = 'StornoCheck'
    OfflineBegin = 'OfflineBegin'
    OfflineEnd = 'OfflineEnd'
    CloseShiftCheck = 'CloseShiftCheck'


class Endpoints(object):
    """Endpoints Class"""
    # Main URL
    Endpoint = 'http://fs.tax.gov.ua:8609/fs'

    # одержання документів (чеків, Z-звітів тощо)
    DocumentEndpoint = '/doc'

    # одержання пакетів документів (офлайн документи тощо)
    PackageEndpoint = '/pck'

    # одержання команд
    CommandEndpoint = '/cmd'


class ErrorCode(object):
    """ErrorCode Class"""
    # OK
    Ok = 0

    # ПРРО не зареєстрований
    TransactionsRegistrarAbsent = 1

    # Відсутній доступ до ПРРО для користувача
    OperatorAccessToTransactionsRegistrarNotGranted = 2

    # В документі зазначено реєстраційний код платника, що не дорівнює реєстраційному коду господарської одиниці
    InvalidTin = 3

    # Зміну для ПРРО наразі відкрито
    ShiftAlreadyOpened = 4

    # Зміну для ПРРО наразі не відкрито
    ShiftNotOpened = 5

    # Останній документ, зареєстрований перед закриттям зміни, повинен бути Z-звітом
    LastDocumentMustBeZRep = 6

    # Некоректний локальний номер чека
    CheckLocalNumberInvalid = 7

    # Z-звіт наразі зареєстрований для поточної зміни
    ZRepAlreadyRegistered = 8

    # Помилка валідації документа
    DocumentValidationError = 9

    # Помилка валідації пакету офлайн документів
    PackageValidationError = 10

    # Некоректний параметр запиту
    InvalidQueryParameter = 11

    # Помилка криптографічних функцій
    CryptographyError = 12


class ResultCode(object):
    """ResultCode Class"""
    # Корректне завершення
    OKCode = 200

    # У разі відсутності даних,
    NoContentCode = 204

    # Bad Request
    BadRequestCode = 400
