"""
Pydantic модели для валидации запросов API.
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
import re

class ModelBAN(BaseModel):
    ban: str = Field(..., description="Номер **ban** (ровно 9 цифр)", min_length=9, max_length=9)
    @field_validator('ban')
    @classmethod
    def validate_ban(cls, v: str) -> str:
        if not re.match(r'^\d{9}$', v):
            raise ValueError("ban должен содержать ровно 9 цифр")
        return v

class ModelPaged(BaseModel):
    page: Optional[int] = Field(None, description="Номер страницы", ge=1)
    records_per_page: Optional[int] = Field(None, description="Записей на страницу", ge=1, le=50)

class ModelCTNAmountPerPage(BaseModel):
    ctn_amount_per_page: Optional[int] = Field(None, description="Количество CTN на страницу", ge=1, le=50)

class PutCallForwardRequestEdit(BaseModel):
    """Модель для редактирования переадресации."""
    ctn: str = Field(..., description="Номер абонента")
    call_forward_edit_request: list = Field(..., description="Список запросов на редактирование")
    call_forward: list = Field(..., description="Параметры переадресации")
    cf_type: Optional[str] = Field(None, description="Тип переадресации")
    cf_ctn: Optional[str] = Field(None, description="Номер для переадресации")
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

class SuspendRestoreCTN(BaseModel):
    """Модель для блокировки/разблокировки номера."""
    reason_code: str = Field(..., description="Код причины блокировки/разблокировки")
    actv_date: Optional[str] = Field(None, description="Дата активации")


class ReplaceSIM(BaseModel):
    """Модель для замены SIM-карты."""
    serial_number: str = Field(..., description="Серийный номер SIM-карты")


class ChangePP(BaseModel):
    """Модель для смены тарифного плана."""
    price_plan: str = Field(..., description="Код тарифного плана")
    future_date: Optional[str] = Field(None, description="Дата смены тарифа")
    free_change: Optional[str] = Field(None, description="Флаг бесплатной смены")


class AddDelSOC(BaseModel):
    """Модель для подключения/отключения услуги."""
    soc: str = Field(..., description="Код услуги (SOC)")
    inclusion_type: str = Field(..., description="Тип включения")
    eff_date: Optional[str] = Field(None, description="Дата начала действия")
    exp_date: Optional[str] = Field(None, description="Дата окончания действия")


class GetSIMList(ModelBAN):
    """Модель для получения списка SIM-карт."""
    pass
class GetSIMListPaged(ModelBAN, ModelPaged):
    """Модель для получения списка SIM-карт с пагинацией."""
    pass


class GetRequestList(ModelPaged):
    """Модель для получения списка запросов."""
    start_date: Optional[str] = Field(None, description="Дата начала периода")
    end_date: Optional[str] = Field(None, description="Дата окончания периода")
    request_id: Optional[str] = Field(None, description="ID запроса")


class GetServicesList(ModelBAN):
    """Модель для получения списка услуг."""
    pass
class GetServicesListPaged(ModelBAN, ModelPaged, ModelCTNAmountPerPage):
    """Модель для получения списка услуг с пагинацией."""
    pass


class GetCTNInfoList(ModelBAN):
    """Модель для получения информации об абоненте."""
    pass
class GetCTNInfoListPaged(ModelBAN, ModelPaged):
    """Модель для получения информации об абоненте с пагинацией."""
    pass


class GetPaymentList(ModelBAN):
    """Модель для получения информации о платежах."""
    start_date: str = Field(..., description="Дата начала периода")
    end_date: str = Field(..., description="Дата окончания периода")
class GetPaymentListPaged(GetPaymentList, ModelPaged):
    """Модель для получения информации о платежах с пагинацией."""
    pass


class GetAdjustmentList(ModelBAN):
    """Модель для получения информации о корректировках."""
    start_date: str = Field(..., description="Дата начала периода")
    end_date: str = Field(..., description="Дата окончания периода")


class CreateBillCallsChargesRequest(ModelBAN):
    """Модель для создания запроса детализации."""
    bill_date: str = Field(..., description="Дата счёта")
    ctn_list: Optional[str] = Field(None, description="Список номеров")


class GetBillCallsCharges(BaseModel):
    """Модель для получения отчёта по звонкам/начислений."""
    request_id: str = Field(..., description="ID запроса")
class GetBillCallsChargesPaged(GetBillCallsCharges, ModelPaged):
    """Модель для получения отчёта по звонкам/начислений с пагинацией."""
    pass


class GetBANInfoListPaged(ModelPaged):
    """Модель для получения списка BAN с пагинацией."""
    pass


class CreateDetailsRequest(BaseModel):
    """Модель для создания запроса на детализацию."""
    period_start: str = Field(..., description="Дата начала периода")
    period_end: str = Field(..., description="Дата окончания периода")
    format_: str = Field(..., alias="format", description="Формат детализации")
    channel: Optional[str] = Field(None, description="Канал доставки")
    email: Optional[str] = Field(None, description="Email для доставки")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
            raise ValueError('Некорректный email адрес')
        return v


class GetDetails(BaseModel):
    """Модель для получение файла детализации (в формате PDF)."""
    request_id: str = Field(..., description="Номер запроса на отчет")


class SharedNumber(BaseModel):
    """Базовая модель для shared number операций."""
    ctn_from: str = Field(..., description="Основной номер")
    ctn_to: str = Field(..., description="Дополнительный номер")
class AddSharedNumberDOL(SharedNumber):
    """Модель для добавления номера в DOL shared list."""
    ctn_type: Optional[str] = Field(None, description="Тип номера")
    soc: Optional[str] = Field(None, description="Код услуги")
    prepaid_state_chk_cancel: Optional[str] = Field(None, description="Флаг проверки prepaid")
    check_add_number_registration: Optional[str] = Field(None, description="Флаг проверки регистрации")
class AddSharedNumberListDOL(SharedNumber):
    """Модель для добавления номера в shared list."""
    ctn_to_list: Optional[str] = Field(None, description="Список целевых номеров")
    soc: Optional[str] = Field(None, description="Код услуги")
    prepaid_state_chk_cancel: Optional[str] = Field(None, description="Флаг проверки prepaid")
    check_add_number_registration: Optional[str] = Field(None, description="Флаг проверки регистрации")
class DeleteSharedNumberListDOL(SharedNumber):
    """Модель для удаления номера из shared list."""
    ctn_to_list: Optional[str] = Field(None, description="Список целевых номеров")


class PersonalDataUpdate(ModelBAN):
    """Модель для обновления персональных данных."""
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
    legalPostcode: Optional[str] = Field(None, description="АдрРег Индекс")
    legalCountryCode: Optional[str] = Field(None, description="АдрРег Код страны")
    legalRegion: Optional[str] = Field(None, description="АдрРег Регион")
    legalArea: Optional[str] = Field(None, description="АдрРег Район")
    legalPlaceType: Optional[str] = Field(None, description="АдрРег Тип НП")
    legalPlace: Optional[str] = Field(None, description="АдрРег Населенный пункт")
    legalStreetType: Optional[str] = Field(None, description="АдрРег Тип улицы")
    legalStreetName: Optional[str] = Field(None, description="АдрРег Улица")
    legalHouseNo: Optional[str] = Field(None, description="АдрРег Номер дома")
    legalBuildingType: Optional[str] = Field(None, description="АдрРег Тип строения")
    legalBuildingNo: Optional[str] = Field(None, description="АдрРег Номер строения")
    legalApartmentType: Optional[str] = Field(None, description="АдрРег Тип помещения")
    legalApartmentNo: Optional[str] = Field(None, description="АдрРег Номер помещения")
    legalAddrComment: Optional[str] = Field(None, description="АдрРег Комментарий")
    legalFiasId: Optional[str] = Field(None, description="АдрРег ФИАС ИД")
    actualPostcode: Optional[str] = Field(None, description="АдрПрож Индекс")
    actualCountryCode: Optional[str] = Field(None, description="АдрПрож Код страны")
    actualRegion: Optional[str] = Field(None, description="АдрПрож Регион")
    actualArea: Optional[str] = Field(None, description="АдрПрож Район")
    actualPlaceType: Optional[str] = Field(None, description="АдрПрож Тип НП")
    actualPlace: Optional[str] = Field(None, description="АдрПрож Населенный пункт")
    actualStreetType: Optional[str] = Field(None, description="АдрПрож Тип улицы")
    actualStreetName: Optional[str] = Field(None, description="АдрПрож Улица")
    actualHouseNo: Optional[str] = Field(None, description="АдрПрож Номер дома")
    actualBuildingType: Optional[str] = Field(None, description="АдрПрож Тип строения")
    actualBuildingNo: Optional[str] = Field(None, description="АдрПрож Номер строения")
    actualApartmentType: Optional[str] = Field(None, description="АдрПрож Тип помещения")
    actualApartmentNo: Optional[str] = Field(None, description="АдрПрож Номер помещения")
    actualAddrComment: Optional[str] = Field(None, description="АдрПрож Комментарий")
    actualFiasId: Optional[str] = Field(None, description="АдрПрож ФИАС ИД")


class PersonalDataResult(BaseModel):
    """Модель для получения результата обновления персональных данных."""
    request_id: str = Field(..., description="ID запроса")


class GetData(ModelBAN):
    """Модель для получения данных."""
    hierarchy_id: str = Field(..., description="ID иерархии")
    subscriber_no: str = Field(..., description="Номер абонента")

class GetDataReport(ModelPaged):
    """Модель для получения отчёта данных."""
    request_id: str = Field(..., description="ID запроса")