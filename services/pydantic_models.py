"""
Pydantic модели для валидации запросов API.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
import re


# ============================================================================
# REST Beeline - Call Forward
# ============================================================================

class PutCallForwardRequestEdit(BaseModel):
    """Модель для редактирования переадресации."""
    ctn: str = Field(..., description="Номер абонента", min_length=10, max_length=15)
    call_forward_edit_request: list = Field(..., description="Список запросов на редактирование")
    call_forward: list = Field(..., description="Параметры переадресации")
    cf_type: Optional[str] = Field(None, description="Тип переадресации")
    cf_ctn: Optional[str] = Field(None, description="Номер для переадресации", min_length=10, max_length=15)
    client: Optional[str] = Field(None, description="Код клиента")

    @field_validator('ctn', 'cf_ctn')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r'^\d{10,15}$', v):
            raise ValueError('Номер телефона должен содержать 10-15 цифр')
        return v


# ============================================================================
# SOAP Beeline - Service Management
# ============================================================================

class AddDelSoc(BaseModel):
    """Модель для подключения/отключения услуги."""
    soc: str = Field(..., description="Код услуги (SOC)", min_length=1, max_length=50)
    inclusion_type: Optional[str] = Field(None, description="Тип включения")
    eff_date: Optional[str] = Field(None, description="Дата начала действия")
    exp_date: Optional[str] = Field(None, description="Дата окончания действия")


class SuspendRestoreCTN(BaseModel):
    """Модель для блокировки/разблокировки номера."""
    reason_code: str = Field(..., description="Код причины блокировки")
    actv_date: Optional[str] = Field(None, description="Дата активации")


class ReplaceSim(BaseModel):
    """Модель для замены SIM-карты."""
    serial_number: str = Field(..., description="Серийный номер SIM-карты")


class Details(BaseModel):
    """Модель для получения детализации."""
    request_id: str = Field(..., description="ID запроса", min_length=1, max_length=100)


class CTNInfoList(BaseModel):
    """Модель для получения информации об абоненте."""
    ban: str = Field(..., description="Лицевой счёт (BAN)", min_length=1, max_length=50)


class CTNInfoListPaged(CTNInfoList):
    """Модель для получения информации об абоненте с пагинацией."""
    page: Optional[int] = Field(None, description="Номер страницы", ge=1)
    records_per_page: Optional[str] = Field(None, description="Записей на страницу")


class ChangePP(BaseModel):
    """Модель для смены тарифного плана."""
    price_plan: str = Field(..., description="Код тарифного плана", min_length=1, max_length=50)
    future_date: Optional[str] = Field(None, description="Дата смены тарифа")
    free_change: Optional[str] = Field(None, description="Флаг бесплатной смены")


class SIMList(BaseModel):
    """Модель для получения списка SIM-карт."""
    ban: str = Field(..., description="Лицевой счёт (BAN)", min_length=1, max_length=50)


class SIMListPaged(SIMList):
    """Модель для получения списка SIM-карт с пагинацией."""
    page: Optional[int] = Field(None, description="Номер страницы", ge=1)
    records_per_page: Optional[str] = Field(None, description="Записей на страницу")


class RequestList(BaseModel):
    """Модель для получения списка запросов."""
    page: Optional[int] = Field(None, description="Номер страницы", ge=1)
    start_date: Optional[str] = Field(None, description="Дата начала периода")
    end_date: Optional[str] = Field(None, description="Дата окончания периода")
    request_id: Optional[str] = Field(None, description="ID запроса")
    records_per_page: Optional[str] = Field(None, description="Записей на страницу")


class ServicesList(BaseModel):
    """Модель для получения списка услуг."""
    ban: str = Field(..., description="Лицевой счёт (BAN)", min_length=1, max_length=50)


class ServicesListPaged(ServicesList):
    """Модель для получения списка услуг с пагинацией."""
    page: Optional[int] = Field(None, description="Номер страницы", ge=1)
    ctn_amount_per_page: Optional[str] = Field(None, description="Количество CTN на страницу")


class PaymentList(BaseModel):
    """Модель для получения информации о платежах."""
    ban: str = Field(..., description="Лицевой счёт (BAN)", min_length=1, max_length=50)
    start_date: str = Field(..., description="Дата начала периода")
    end_date: str = Field(..., description="Дата окончания периода")


class PaymentListPaged(PaymentList):
    """Модель для получения информации о платежах с пагинацией."""
    page: Optional[int] = Field(None, description="Номер страницы", ge=1)
    records_per_page: Optional[str] = Field(None, description="Записей на страницу")


class AdjustmentList(BaseModel):
    """Модель для получения информации о корректировках."""
    ban: str = Field(..., description="Лицевой счёт (BAN)", min_length=1, max_length=50)
    start_date: str = Field(..., description="Дата начала периода")
    end_date: str = Field(..., description="Дата окончания периода")


class GetBillCalls(BaseModel):
    """Модель для получения отчёта по звонкам."""
    request_id: str = Field(..., description="ID запроса", min_length=1, max_length=100)


class GetBillCallsPaged(GetBillCalls):
    """Модель для получения отчёта по звонкам с пагинацией."""
    page: Optional[int] = Field(None, description="Номер страницы", ge=1)
    records_per_page: Optional[str] = Field(None, description="Записей на страницу")


class GetBillCharges(BaseModel):
    """Модель для получения начислений."""
    request_id: str = Field(..., description="ID запроса", min_length=1, max_length=100)


class GetBillChargesPaged(GetBillCharges):
    """Модель для получения начислений с пагинацией."""
    page: Optional[int] = Field(None, description="Номер страницы", ge=1)
    records_per_page: Optional[str] = Field(None, description="Записей на страницу")


class SharedNumber(BaseModel):
    """Базовая модель для shared number операций."""
    ctn_from: str = Field(..., description="Исходный номер", min_length=10, max_length=15)
    ctn_to: str = Field(..., description="Целевой номер", min_length=10, max_length=15)

    @field_validator('ctn_from', 'ctn_to')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r'^\d{10,15}$', v):
            raise ValueError('Номер телефона должен содержать 10-15 цифр')
        return v


class SharedNumberDOL(SharedNumber):
    """Модель для добавления номера в DOL shared list."""
    ctn_type: Optional[str] = Field(None, description="Тип номера")
    soc: Optional[str] = Field(None, description="Код услуги")
    prepaid_state_chk_cancel: Optional[str] = Field(None, description="Флаг проверки prepaid")
    check_add_number_registration: Optional[str] = Field(None, description="Флаг проверки регистрации")


class SharedNumberListDOL(SharedNumber):
    """Модель для добавления номера в shared list."""
    ctn_to_list: Optional[str] = Field(None, description="Список целевых номеров")
    soc: Optional[str] = Field(None, description="Код услуги")
    prepaid_state_chk_cancel: Optional[str] = Field(None, description="Флаг проверки prepaid")
    check_add_number_registration: Optional[str] = Field(None, description="Флаг проверки регистрации")


class SharedNumberDeleteDOL(SharedNumber):
    """Модель для удаления номера из shared list."""
    ctn_to_list: Optional[str] = Field(None, description="Список целевых номеров")


class PersonalDataUpdate(BaseModel):
    """Модель для обновления персональных данных."""
    ban: Optional[str] = Field(None, description="Лицевой счёт")
    statusBan: Optional[str] = Field(None, description="Статус BAN")
    ctn: Optional[str] = Field(None, description="Номер телефона")
    marketCode: Optional[str] = Field(None, description="Код рынка")
    docName: Optional[str] = Field(None, description="Название документа")
    changeDate: Optional[str] = Field(None, description="Дата изменения")
    startServiceDate: Optional[str] = Field(None, description="Дата начала обслуживания")
    confDate: Optional[str] = Field(None, description="Дата подтверждения")
    statusPdn: Optional[str] = Field(None, description="Статус PDN")
    blockDate: Optional[str] = Field(None, description="Дата блокировки")
    accessClientPdn: Optional[str] = Field(None, description="Доступ клиента к PDN")
    introPdn: Optional[str] = Field(None, description="Ввод PDN")
    citizenship: Optional[str] = Field(None, description="Гражданство")
    docNo: Optional[str] = Field(None, description="Номер документа")
    docType: Optional[str] = Field(None, description="Тип документа")
    docIssueDate: Optional[str] = Field(None, description="Дата выдачи документа")
    docIssuer: Optional[str] = Field(None, description="Орган выдачи документа")
    docIssuerCode: Optional[str] = Field(None, description="Код органа выдачи")
    docExpirationDate: Optional[str] = Field(None, description="Дата истечения документа")
    birthdate: Optional[str] = Field(None, description="Дата рождения")
    frnMigcard: Optional[str] = Field(None, description="FRN миг карты")
    frnMigcardEffDate: Optional[str] = Field(None, description="Дата начала FRN миг карты")
    frnMigcardExpDate: Optional[str] = Field(None, description="Дата истечения FRN миг карты")
    frnDoc: Optional[str] = Field(None, description="FRN документа")
    firstName: Optional[str] = Field(None, description="Имя")
    lastName: Optional[str] = Field(None, description="Фамилия")
    surName: Optional[str] = Field(None, description="Отчество")
    birthplace: Optional[str] = Field(None, description="Место рождения")
    gender: Optional[str] = Field(None, description="Пол")
    taxNumber: Optional[str] = Field(None, description="ИНН")
    snils: Optional[str] = Field(None, description="СНИЛС")
    # Адресные поля опущены для краткости, но могут быть добавлены аналогично


class PersonalDataResultRequest(BaseModel):
    """Модель для получения результата обновления персональных данных."""
    request_id: str = Field(..., description="ID запроса", min_length=1, max_length=100)


class GetDataReportRequest(BaseModel):
    """Модель для получения отчёта данных."""
    request_id: str = Field(..., description="ID запроса", min_length=1, max_length=100)
    page: Optional[int] = Field(None, description="Номер страницы", ge=1)
    records_per_page: Optional[str] = Field(None, description="Записей на страницу")


class GetBANInfoListPagedRequest(BaseModel):
    """Модель для получения списка BAN с пагинацией."""
    page: Optional[int] = Field(None, description="Номер страницы", ge=1)
    records_per_page: Optional[int] = Field(None, description="Записей на страницу", ge=1)


class CreateBillRequest(BaseModel):
    """Модель для создания запроса детализации."""
    ban: str = Field(..., description="Лицевой счёт (BAN)", min_length=1, max_length=50)
    bill_date: str = Field(..., description="Дата счёта")
    ctn_list: Optional[str] = Field(None, description="Список номеров")


class CreateDetailsRequest(BaseModel):
    """Модель для создания запроса на детализацию."""
    period_start: str = Field(..., description="Дата начала периода")
    period_end: str = Field(..., description="Дата окончания периода")
    format_: str = Field(..., alias="format", description="Формат детализации")
    channel: str = Field(..., description="Канал доставки")
    email: str = Field(..., description="Email для доставки")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
            raise ValueError('Некорректный email адрес')
        return v


class GetDataRequest(BaseModel):
    """Модель для получения данных."""
    ban: str = Field(..., description="Лицевой счёт (BAN)", min_length=1, max_length=50)
    hierarchy_id: str = Field(..., description="ID иерархии", min_length=1, max_length=100)
    subscriber_no: str = Field(..., description="Номер абонента", min_length=1, max_length=50)
