"""
Роутер для SOAP API Beeline (WSAPI)
Все методы WSAPI Beeline доступны через этот роутер
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, List
from pydantic import BaseModel, Field

from client.beeline_soap_client import BeelineSoapClient
from services.token_manager import get_beeline_token
from services.pydantic_models import (
    AddDelSoc, SuspendRestoreCTN, ReplaceSim, Details, CTNInfoList,
    CTNInfoListPaged, ChangePP, SIMList, SIMListPaged, RequestList,
    ServicesList, ServicesListPaged, PaymentList, PaymentListPaged,
    AdjustmentList, GetBillCalls, GetBillCallsPaged, GetBillCharges,
    GetBillChargesPaged, SharedNumberDOL, SharedNumberListDOL,
    SharedNumberDeleteDOL, PersonalDataUpdate, PersonalDataResultRequest,
    GetDataReportRequest, GetBANInfoListPagedRequest, CreateBillRequest,
    CreateDetailsRequest, GetDataRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/soap", tags=["SOAP Beeline"])


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    from config.config import module_api_key
    if x_api_key != module_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key


def get_soap_client() -> BeelineSoapClient:
    """Зависимость для получения SOAP клиента"""
    token = get_beeline_token()
    return BeelineSoapClient(token_provider=token)


# ============================================================================
# Информация об абонентах
# ============================================================================

@router.post("/getCTNInfoList", summary="Получить информацию об абонентах")
def get_ctn_info_list_app(
    request: CTNInfoList,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение информации об абонентах по списку номеров (CTN).

    - **ctn**: номер ctn
    - **ban**: номер ban
    """
    result = beeline_soap.get_ctn_info_list(
        ctn=ctn,
        ban=request.ban
    )
    return {"status": "success", "data": result}


@router.post("/getCTNInfoListPaged", summary="Получить информацию об абонентах (пагинация)")
def get_ctn_info_list_paged_app(
    request: CTNInfoListPaged,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение информации об абонентах с пагинацией.

    - **ctn**: номер ctn
    - **ban**: номер ban
    - **page**: Номер страницы
    - **records_per_page**: Размер страницы
    """
    result = beeline_soap.get_ctn_info_list_paged(
        ctn,
        ban=request.ban,
        page=request.page,
        records_per_page=request.records_per_page
    )
    return {"status": "success", "data": result}


# ============================================================================
# Платежи и балансы
# ============================================================================

@router.post("/getPaymentList", summary="Получить список платежей")
def get_payment_list_app(
    request: PaymentList,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка платежей за указанный период.

    - **contractNumber**: Номер контракта
    - **dateFrom**: Дата начала периода (YYYY-MM-DD)
    - **dateTo**: Дата окончания периода (YYYY-MM-DD)
    """
    result = beeline_soap.get_payment_list(
        contract_number=request.contractNumber,
        date_from=request.dateFrom,
        date_to=request.dateTo
    )
    return {"status": "success", "data": result}


@router.post("/getPaymentListPaged", summary="Получить список платежей (пагинация)")
def get_payment_list_paged_app(
    request: PaymentListPaged,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка платежей с пагинацией.
    """
    result = beeline_soap.get_payment_list_paged(
        contract_number=request.contractNumber,
        date_from=request.dateFrom,
        date_to=request.dateTo,
        page_number=request.pageNumber,
        page_size=request.pageSize
    )
    return {"status": "success", "data": result}


@router.post("/getUnbilledBalance", summary="Получить небиллингованный баланс")
def get_unbilled_balance_app(
    request: CTNInfoList,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение небиллингованного баланса по номеру контракта.
    """
    # Используем первый номер из списка
    contract_number = request.contractNumbers[0] if request.contractNumbers else ""
    result = beeline_soap.get_unbilled_balance(contract_number=contract_number)
    return {"status": "success", "data": result}


# ============================================================================
# Услуги и тарифы
# ============================================================================

@router.post("/addDelSOC", summary="Подключить/отключить услугу")
def add_del_soc_app(
    request: AddDelSoc,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Подключение или отключение услуг (SOC).

    - **contractNumber**: Номер контракта
    - **action**: Действие ('ADD' или 'DEL')
    - **socCode**: Код услуги
    - **params**: Параметры услуги (опционально)
    """
    result = beeline_soap.add_del_soc(
        contract_number=request.contractNumber,
        action=request.action,
        soc_code=request.socCode,
        params=request.params
    )
    return {"status": "success", "data": result}


@router.post("/changePP", summary="Сменить тарифный план")
def change_pp_app(
    request: ChangePP,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Смена тарифного плана (Price Plan).

    - **ctn**: номер ctn
    - **price_plan**: код нового тарифного плана
    - **future_date**: Индикатор производить смену тарифного плана текущей датой
    - **free_change**: Признак освобождения от платы за переход
    """
    result = beeline_soap.change_pp(
        ctn,
        price_plan=request.price_plan,
        future_date=request.future_date,
        free_change=request.free_change
    )
    return {"status": "success", "data": result}


@router.post("/getServicesList", summary="Получить список услуг")
def get_services_list_app(
    request: ServicesList,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка активных услуг абонента.
    """
    result = beeline_soap.get_services_list(contract_number=request.contractNumber)
    return {"status": "success", "data": result}


@router.post("/getServicesListPaged", summary="Получить список услуг (пагинация)")
def get_services_list_paged_app(
    request: ServicesListPaged,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка услуг с пагинацией.
    """
    result = beeline_soap.get_services_list_paged(
        contract_number=request.contractNumber,
        page_number=request.pageNumber,
        page_size=request.pageSize
    )
    return {"status": "success", "data": result}


# ============================================================================
# Блокировки
# ============================================================================

@router.post("/suspendCTN", summary="Добровольная блокировка номера")
def suspend_ctn_app(
    request: SuspendRestoreCTN,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Добровольная блокировка номера (suspend).

    - **ctn**: номер ctn
    - **reason_code**: причина блокировки
    - **actv_date**: дата блокировки
    """
    result = beeline_soap.suspend_ctn(
        ctn,
        reason_code=request.reason_code,
        actv_date=request.actv_date
    )
    return {"status": "success", "data": result}


@router.post("/restoreCTN", summary="Разблокировка номера")
def restore_ctn_app(
    request: SuspendRestoreCTN,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Разблокировка номера (restore).

    - **ctn**: номер ctn
    - **reason_code**: причина разблокировки
    - **actv_date**: дата разблокировки
    """
    result = beeline_soap.restore_ctn(
        ctn,
        reason_code=request.reason_code,
        actv_date=request.actv_date
    )
    return {"status": "success", "data": result}


# ============================================================================
# SIM-карты
# ============================================================================

@router.post("/replaceSIM", summary="Замена SIM-карты")
def replace_sim_app(
    request: ReplaceSim,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Замена SIM-карты.

    - **ctn**: номер ctn
    - **serial_number**: Новый ICCID SIM-карты
    """
    result = beeline_soap.replace_sim(
        ctn,
        serial_number=request.serial_number,
    )
    return {"status": "success", "data": result}


@router.post("/getSIMList", summary="Получить список SIM-карт")
def get_sim_list_app(
    request: SIMList,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка SIM-карт абонента.
    """
    result = beeline_soap.get_sim_list(contract_number=request.contractNumber)
    return {"status": "success", "data": result}


@router.post("/getSIMListPaged", summary="Получить список SIM-карт (пагинация)")
def get_sim_list_paged_app(
    request: SIMListPaged,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка SIM-карт с пагинацией.
    """
    result = beeline_soap.get_sim_list_paged(
        contract_number=request.contractNumber,
        page_number=request.pageNumber,
        page_size=request.pageSize
    )
    return {"status": "success", "data": result}


# ============================================================================
# Детализация звонков
# ============================================================================

@router.post("/getDetails", summary="Получить детализацию звонков")
def get_details_app(
    request: Details,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение детализации звонков за период.

    - **contractNumber**: Номер контракта
    - **month**: Месяц в формате YYYY-MM
    """
    result = beeline_soap.get_details(
        contract_number=request.contractNumber,
        month=request.month
    )
    return {"status": "success", "data": result}


@router.post("/getRequestList", summary="Получить список запросов")
def get_request_list_app(
    request: RequestList,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка запросов на детализацию.
    """
    result = beeline_soap.get_request_list(contract_number=request.contractNumber)
    return {"status": "success", "data": result}


@router.post("/getBillCalls", summary="Получить биллинг звонков")
def get_bill_calls_app(
    request: GetBillCalls,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение биллинга звонков за период.
    """
    result = beeline_soap.get_bill_calls(
        contract_number=request.contractNumber,
        date_from=request.dateFrom,
        date_to=request.dateTo
    )
    return {"status": "success", "data": result}


@router.post("/getBillCallsPaged", summary="Получить биллинг звонков (пагинация)")
def get_bill_calls_paged_app(
    request: GetBillCallsPaged,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение биллинга звонков с пагинацией.
    """
    result = beeline_soap.get_bill_calls_paged(
        contract_number=request.contractNumber,
        date_from=request.dateFrom,
        date_to=request.dateTo,
        page_number=request.pageNumber,
        page_size=request.pageSize
    )
    return {"status": "success", "data": result}


@router.post("/getBillCharges", summary="Получить биллинг списаний")
def get_bill_charges_app(
    request: GetBillCharges,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение биллинга списаний за период.
    """
    result = beeline_soap.get_bill_charges(
        contract_number=request.contractNumber,
        date_from=request.dateFrom,
        date_to=request.dateTo
    )
    return {"status": "success", "data": result}


@router.post("/getBillChargesPaged", summary="Получить биллинг списаний (пагинация)")
def get_bill_charges_paged_app(
    request: GetBillChargesPaged,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение биллинга списаний с пагинацией.
    """
    result = beeline_soap.get_bill_charges_paged(
        contract_number=request.contractNumber,
        date_from=request.dateFrom,
        date_to=request.dateTo,
        page_number=request.pageNumber,
        page_size=request.pageSize
    )
    return {"status": "success", "data": result}


@router.post("/getAdjustmentList", summary="Получить список корректировок")
def get_adjustment_list_app(
    request: AdjustmentList,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка корректировок за период.
    """
    result = beeline_soap.get_adjustment_list(
        contract_number=request.contractNumber,
        date_from=request.dateFrom,
        date_to=request.dateTo
    )
    return {"status": "success", "data": result}


# ============================================================================
# Общие номера (Shared Number)
# ============================================================================

@router.post("/addSharedNumberListDOL", summary="Добавить общие номера")
def add_shared_number_list_dol_app(
    request: SharedNumberListDOL,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Добавление списка общих номеров (DoL).
    """
    result = beeline_soap.add_shared_number_list_dol(
        contract_number=request.contractNumber,
        shared_numbers=request.sharedNumbers
    )
    return {"status": "success", "data": result}


@router.post("/deleteSharedNumberListDOL", summary="Удалить общие номера")
def delete_shared_number_list_dol_app(
    request: SharedNumberDeleteDOL,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Удаление списка общих номеров (DoL).
    """
    result = beeline_soap.delete_shared_number_list_dol(
        contract_number=request.contractNumber,
        shared_numbers=request.sharedNumbers
    )
    return {"status": "success", "data": result}


# ============================================================================
# Персональные данные
# ============================================================================

@router.post("/personalDataUpdate", summary="Обновить персональные данные")
def personal_data_update_app(
    request: PersonalDataUpdate,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Обновление персональных данных абонента.
    """
    result = beeline_soap.personal_data_update(
        contract_number=request.contractNumber,
        data=request.data
    )
    return {"status": "success", "data": result}


@router.post("/personalDataResult", summary="Получить результат обновления данных")
def personal_data_result_app(
    request: PersonalDataResultRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение результата обновления персональных данных.
    """
    result = beeline_soap.personal_data_result(request_id=request.requestId)
    return {"status": "success", "data": result}


@router.post("/getDataReport", summary="Получить отчет по данным")
def get_data_report_app(
    request: GetDataReportRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение отчета по данным.
    """
    result = beeline_soap.get_data_report(report_id=request.reportId)
    return {"status": "success", "data": result}


# ============================================================================
# BAN (Business Account Number)
# ============================================================================

@router.post("/getBANInfoListPaged", summary="Получить информацию о BAN (пагинация)")
def get_ban_info_list_paged_app(
    request: GetBANInfoListPagedRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение информации о BAN с пагинацией.
    """
    result = beeline_soap.get_ban_info_list_paged(
        ban=request.ban,
        page_number=request.pageNumber,
        page_size=request.pageSize
    )
    return {"status": "success", "data": result}


# ============================================================================
# Биллинг (создание счетов)
# ============================================================================

@router.post("/createBill", summary="Создать счет")
def create_bill_app(
    request: CreateBillRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Создание счета для абонента.
    """
    result = beeline_soap.create_bill(
        contract_number=request.contractNumber,
        amount=request.amount,
        description=request.description
    )
    return {"status": "success", "data": result}


@router.post("/createDetails", summary="Создать запрос на детализацию")
def create_details_app(
    request: CreateDetailsRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Создание запроса на выгрузку детализации.
    """
    result = beeline_soap.create_details(
        contract_number=request.contractNumber,
        month=request.month,
        format=request.format
    )
    return {"status": "success", "data": result}


@router.post("/getData", summary="Получить данные")
def get_data_app(
    request: GetDataRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение данных по запросу.
    """
    result = beeline_soap.get_data(request_id=request.requestId)
    return {"status": "success", "data": result}


# ============================================================================
# Вспомогательные модели
# ============================================================================

class ContractNumberRequest(BaseModel):
    """Базовый запрос с номером контракта"""
    contractNumber: str = Field(..., description="Номер контракта", example="79001234567")
