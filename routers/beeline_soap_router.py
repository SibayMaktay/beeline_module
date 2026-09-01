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
    from config.config import api_key
    if x_api_key != api_key:
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
def get_ctn_info_list(
    request: CTNInfoList,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение информации об абонентах по списку номеров (CTN).

    - **contractNumbers**: Список номеров контрактов
    """
    result = client.get_ctn_info_list(contract_numbers=request.contractNumbers)
    return {"status": "success", "data": result}


@router.post("/getCTNInfoListPaged", summary="Получить информацию об абонентах (пагинация)")
def get_ctn_info_list_paged(
    request: CTNInfoListPaged,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение информации об абонентах с пагинацией.

    - **contractNumbers**: Список номеров контрактов
    - **pageNumber**: Номер страницы
    - **pageSize**: Размер страницы
    """
    result = client.get_ctn_info_list_paged(
        contract_numbers=request.contractNumbers,
        page_number=request.pageNumber,
        page_size=request.pageSize
    )
    return {"status": "success", "data": result}


# ============================================================================
# Платежи и балансы
# ============================================================================

@router.post("/getPaymentList", summary="Получить список платежей")
def get_payment_list(
    request: PaymentList,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение списка платежей за указанный период.

    - **contractNumber**: Номер контракта
    - **dateFrom**: Дата начала периода (YYYY-MM-DD)
    - **dateTo**: Дата окончания периода (YYYY-MM-DD)
    """
    result = client.get_payment_list(
        contract_number=request.contractNumber,
        date_from=request.dateFrom,
        date_to=request.dateTo
    )
    return {"status": "success", "data": result}


@router.post("/getPaymentListPaged", summary="Получить список платежей (пагинация)")
def get_payment_list_paged(
    request: PaymentListPaged,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение списка платежей с пагинацией.
    """
    result = client.get_payment_list_paged(
        contract_number=request.contractNumber,
        date_from=request.dateFrom,
        date_to=request.dateTo,
        page_number=request.pageNumber,
        page_size=request.pageSize
    )
    return {"status": "success", "data": result}


@router.post("/getUnbilledBalance", summary="Получить небиллингованный баланс")
def get_unbilled_balance(
    request: CTNInfoList,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение небиллингованного баланса по номеру контракта.
    """
    # Используем первый номер из списка
    contract_number = request.contractNumbers[0] if request.contractNumbers else ""
    result = client.get_unbilled_balance(contract_number=contract_number)
    return {"status": "success", "data": result}


# ============================================================================
# Услуги и тарифы
# ============================================================================

@router.post("/addDelSOC", summary="Подключить/отключить услугу")
def add_del_soc(
    request: AddDelSoc,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Подключение или отключение услуг (SOC).

    - **contractNumber**: Номер контракта
    - **action**: Действие ('ADD' или 'DEL')
    - **socCode**: Код услуги
    - **params**: Параметры услуги (опционально)
    """
    result = client.add_del_soc(
        contract_number=request.contractNumber,
        action=request.action,
        soc_code=request.socCode,
        params=request.params
    )
    return {"status": "success", "data": result}


@router.post("/changePP", summary="Сменить тарифный план")
def change_pp(
    request: ChangePP,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Смена тарифного плана (Price Plan).

    - **contractNumber**: Номер контракта
    - **newPPCode**: Код нового тарифа
    """
    result = client.change_pp(
        contract_number=request.contractNumber,
        new_pp_code=request.newPPCode
    )
    return {"status": "success", "data": result}


@router.post("/getServicesList", summary="Получить список услуг")
def get_services_list(
    request: ServicesList,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение списка активных услуг абонента.
    """
    result = client.get_services_list(contract_number=request.contractNumber)
    return {"status": "success", "data": result}


@router.post("/getServicesListPaged", summary="Получить список услуг (пагинация)")
def get_services_list_paged(
    request: ServicesListPaged,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение списка услуг с пагинацией.
    """
    result = client.get_services_list_paged(
        contract_number=request.contractNumber,
        page_number=request.pageNumber,
        page_size=request.pageSize
    )
    return {"status": "success", "data": result}


# ============================================================================
# Блокировки
# ============================================================================

@router.post("/suspendCTN", summary="Добровольная блокировка номера")
def suspend_ctn(
    request: SuspendRestoreCTN,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Добровольная блокировка номера (suspend).

    - **contractNumber**: Номер контракта
    - **comment**: Комментарий к блокировке
    """
    result = client.suspend_ctn(
        contract_number=request.contractNumber,
        comment=request.comment
    )
    return {"status": "success", "data": result}


@router.post("/restoreCTN", summary="Разблокировка номера")
def restore_ctn(
    request: SuspendRestoreCTN,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Разблокировка номера (restore).

    - **contractNumber**: Номер контракта
    - **comment**: Комментарий к разблокировке
    """
    result = client.restore_ctn(
        contract_number=request.contractNumber,
        comment=request.comment
    )
    return {"status": "success", "data": result}


# ============================================================================
# SIM-карты
# ============================================================================

@router.post("/replaceSIM", summary="Замена SIM-карты")
def replace_sim(
    request: ReplaceSim,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Замена SIM-карты.

    - **contractNumber**: Номер контракта
    - **newICCID**: Новый ICCID SIM-карты
    """
    result = client.replace_sim(
        contract_number=request.contractNumber,
        new_iccid=request.newICCID
    )
    return {"status": "success", "data": result}


@router.post("/getSIMList", summary="Получить список SIM-карт")
def get_sim_list(
    request: SIMList,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение списка SIM-карт абонента.
    """
    result = client.get_sim_list(contract_number=request.contractNumber)
    return {"status": "success", "data": result}


@router.post("/getSIMListPaged", summary="Получить список SIM-карт (пагинация)")
def get_sim_list_paged(
    request: SIMListPaged,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение списка SIM-карт с пагинацией.
    """
    result = client.get_sim_list_paged(
        contract_number=request.contractNumber,
        page_number=request.pageNumber,
        page_size=request.pageSize
    )
    return {"status": "success", "data": result}


# ============================================================================
# Детализация звонков
# ============================================================================

@router.post("/getDetails", summary="Получить детализацию звонков")
def get_details(
    request: Details,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение детализации звонков за период.

    - **contractNumber**: Номер контракта
    - **month**: Месяц в формате YYYY-MM
    """
    result = client.get_details(
        contract_number=request.contractNumber,
        month=request.month
    )
    return {"status": "success", "data": result}


@router.post("/getRequestList", summary="Получить список запросов")
def get_request_list(
    request: RequestList,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение списка запросов на детализацию.
    """
    result = client.get_request_list(contract_number=request.contractNumber)
    return {"status": "success", "data": result}


@router.post("/getBillCalls", summary="Получить биллинг звонков")
def get_bill_calls(
    request: GetBillCalls,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение биллинга звонков за период.
    """
    result = client.get_bill_calls(
        contract_number=request.contractNumber,
        date_from=request.dateFrom,
        date_to=request.dateTo
    )
    return {"status": "success", "data": result}


@router.post("/getBillCallsPaged", summary="Получить биллинг звонков (пагинация)")
def get_bill_calls_paged(
    request: GetBillCallsPaged,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение биллинга звонков с пагинацией.
    """
    result = client.get_bill_calls_paged(
        contract_number=request.contractNumber,
        date_from=request.dateFrom,
        date_to=request.dateTo,
        page_number=request.pageNumber,
        page_size=request.pageSize
    )
    return {"status": "success", "data": result}


@router.post("/getBillCharges", summary="Получить биллинг списаний")
def get_bill_charges(
    request: GetBillCharges,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение биллинга списаний за период.
    """
    result = client.get_bill_charges(
        contract_number=request.contractNumber,
        date_from=request.dateFrom,
        date_to=request.dateTo
    )
    return {"status": "success", "data": result}


@router.post("/getBillChargesPaged", summary="Получить биллинг списаний (пагинация)")
def get_bill_charges_paged(
    request: GetBillChargesPaged,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение биллинга списаний с пагинацией.
    """
    result = client.get_bill_charges_paged(
        contract_number=request.contractNumber,
        date_from=request.dateFrom,
        date_to=request.dateTo,
        page_number=request.pageNumber,
        page_size=request.pageSize
    )
    return {"status": "success", "data": result}


@router.post("/getAdjustmentList", summary="Получить список корректировок")
def get_adjustment_list(
    request: AdjustmentList,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение списка корректировок за период.
    """
    result = client.get_adjustment_list(
        contract_number=request.contractNumber,
        date_from=request.dateFrom,
        date_to=request.dateTo
    )
    return {"status": "success", "data": result}


# ============================================================================
# Общие номера (Shared Number)
# ============================================================================

@router.post("/addSharedNumberListDOL", summary="Добавить общие номера")
def add_shared_number_list_dol(
    request: SharedNumberListDOL,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Добавление списка общих номеров (DoL).
    """
    result = client.add_shared_number_list_dol(
        contract_number=request.contractNumber,
        shared_numbers=request.sharedNumbers
    )
    return {"status": "success", "data": result}


@router.post("/deleteSharedNumberListDOL", summary="Удалить общие номера")
def delete_shared_number_list_dol(
    request: SharedNumberDeleteDOL,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Удаление списка общих номеров (DoL).
    """
    result = client.delete_shared_number_list_dol(
        contract_number=request.contractNumber,
        shared_numbers=request.sharedNumbers
    )
    return {"status": "success", "data": result}


# ============================================================================
# Персональные данные
# ============================================================================

@router.post("/personalDataUpdate", summary="Обновить персональные данные")
def personal_data_update(
    request: PersonalDataUpdate,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Обновление персональных данных абонента.
    """
    result = client.personal_data_update(
        contract_number=request.contractNumber,
        data=request.data
    )
    return {"status": "success", "data": result}


@router.post("/personalDataResult", summary="Получить результат обновления данных")
def personal_data_result(
    request: PersonalDataResultRequest,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение результата обновления персональных данных.
    """
    result = client.personal_data_result(request_id=request.requestId)
    return {"status": "success", "data": result}


@router.post("/getDataReport", summary="Получить отчет по данным")
def get_data_report(
    request: GetDataReportRequest,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение отчета по данным.
    """
    result = client.get_data_report(report_id=request.reportId)
    return {"status": "success", "data": result}


# ============================================================================
# BAN (Business Account Number)
# ============================================================================

@router.post("/getBANInfoListPaged", summary="Получить информацию о BAN (пагинация)")
def get_ban_info_list_paged(
    request: GetBANInfoListPagedRequest,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение информации о BAN с пагинацией.
    """
    result = client.get_ban_info_list_paged(
        ban=request.ban,
        page_number=request.pageNumber,
        page_size=request.pageSize
    )
    return {"status": "success", "data": result}


# ============================================================================
# Биллинг (создание счетов)
# ============================================================================

@router.post("/createBill", summary="Создать счет")
def create_bill(
    request: CreateBillRequest,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Создание счета для абонента.
    """
    result = client.create_bill(
        contract_number=request.contractNumber,
        amount=request.amount,
        description=request.description
    )
    return {"status": "success", "data": result}


@router.post("/createDetails", summary="Создать запрос на детализацию")
def create_details(
    request: CreateDetailsRequest,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Создание запроса на выгрузку детализации.
    """
    result = client.create_details(
        contract_number=request.contractNumber,
        month=request.month,
        format=request.format
    )
    return {"status": "success", "data": result}


@router.post("/getData", summary="Получить данные")
def get_data(
    request: GetDataRequest,
    client: BeelineSoapClient = Depends(get_soap_client),
    api_key: str = Depends(verify_api_key)
):
    """
    Получение данных по запросу.
    """
    result = client.get_data(request_id=request.requestId)
    return {"status": "success", "data": result}


# ============================================================================
# Вспомогательные модели
# ============================================================================

class ContractNumberRequest(BaseModel):
    """Базовый запрос с номером контракта"""
    contractNumber: str = Field(..., description="Номер контракта", example="79001234567")
