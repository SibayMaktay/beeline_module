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
    records_per_page: int = Field(50, description="Записей на страницу", le=50, ge=1)

class ModelCTNAmountPerPage(BaseModel):
    ctn_amount_per_page: int = Field(50, description="Количество CTN на страницу", le=50, ge=1)

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
    ctn: str = Field(..., description="Номер телефона", min_length=10)
    citizenship: Optional[str] = Field(None, description="Гражданство")
    docNo: str = Field(..., description="Номер документа")
    docType: Optional[str] = Field(None, description="Тип документа")
    docIssueDate: str = Field(..., description="Дата выдачи")
    docIssuer: Optional[str] = Field(None, description="Кем выдан")
    docIssuerCode: Optional[str] = Field(None, description="Код подразделения выдавшего документ")
    docExpirationDate: Optional[str] = Field(None, description="Документ действителен до")
    birthdate: str = Field(..., description="Дата рождения")
    frnMigcard: Optional[str] = Field(None, description="Номер миграционной карты")
    frnMigcardEffDate: Optional[str] = Field(None, description="Дата выдачи миграционной карты")
    frnMigcardExpDate: Optional[str] = Field(None, description="Срок действия миграционной карты")
    frnDoc: Optional[str] = Field(None, description="Документ нерезидента")
    firstName: str = Field(..., description="Имя")
    surName: Optional[str] = Field(None, description="Отчество")
    lastName: str = Field(..., description="Фамилия")
    birthplace: Optional[str] = Field(None, description="Место рождения")
    gender: str = Field(..., description="Пол", maxLength=1, min_length=1)
    taxNumber: Optional[str] = Field(None, description="ИНН")
    snils: Optional[str] = Field(None, description="СНИЛС")
    legalPostcode: Optional[str] = Field(None, description="Адрес Регистрации - Индекс")
    legalCountryCode: Optional[str] = Field(None, description="Адрес Регистрации - Код страны")
    legalRegion: Optional[str] = Field(None, description="Адрес Регистрации - Регион")
    legalArea: Optional[str] = Field(None, description="Адрес Регистрации - Район")
    legalPlaceType: str = Field(..., description="Адрес Регистрации - Тип Населенного пункта")
    legalPlace: str = Field(..., description="Адрес Регистрации - Населенный пункт")
    legalStreetType: Optional[str] = Field(None, description="Адрес Регистрации - Тип улицы")
    legalStreetName: Optional[str] = Field(None, description="Адрес Регистрации - Улица")
    legalHouseType: Optional[str] = Field(None, description="Адрес Регистрации - Тип дома")
    legalHouseNo: Optional[str] = Field(None, description="Адрес Регистрации - Номер дома")
    legalBuildingType: Optional[str] = Field(None, description="Адрес Регистрации - Тип строения")
    legalBuildingNo: Optional[str] = Field(None, description="Адрес Регистрации - Номер строения")
    legalApartmentType: Optional[str] = Field(None, description="Адрес Регистрации - Тип помещения")
    legalApartmentNo: Optional[str] = Field(None, description="Адрес Регистрации - Номер помещения")
    legalAddrComment: Optional[str] = Field(None, description="Адрес Регистрации - Комментарий")
    legalFiasId: Optional[str] = Field(None, description="Адрес Регистрации - ФИАС ИД")
    actualPostcode: Optional[str] = Field(None, description="Адрес Проживания - Индекс")
    actualCountryCode: Optional[str] = Field(None, description="Адрес Проживания - Код страны")
    actualRegion: Optional[str] = Field(None, description="Адрес Проживания - Регион")
    actualArea: Optional[str] = Field(None, description="Адрес Проживания - Район")
    actualPlaceType: str = Field(..., description="Адрес Проживания - Тип Населенного пункта")
    actualPlace: str = Field(..., description="Адрес Проживания - Населенный пункт")
    actualStreetType: Optional[str] = Field(None, description="Адрес Проживания - Тип улицы")
    actualStreetName: Optional[str] = Field(None, description="Адрес Проживания - Улица")
    actualHouseType: Optional[str] = Field(None, description="Адрес Проживания - Тип дома")
    actualHouseNo: Optional[str] = Field(None, description="Адрес Проживания - Номер дома")
    actualBuildingType: Optional[str] = Field(None, description="Адрес Проживания - Тип строения")
    actualBuildingNo: Optional[str] = Field(None, description="Адрес Проживания - Номер строения")
    actualApartmentType: Optional[str] = Field(None, description="Адрес Проживания - Тип помещения")
    actualApartmentNo: Optional[str] = Field(None, description="Адрес Проживания - Номер помещения")
    actualAddrComment: Optional[str] = Field(None, description="Адрес Проживания - Комментарий")
    actualFiasId: Optional[str] = Field(None, description="Адрес Проживания - ФИАС ИД")


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