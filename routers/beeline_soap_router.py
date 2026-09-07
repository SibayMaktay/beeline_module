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
from services.pydantic_models import *

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



@router.post("/suspendCTN", summary="Добровольная блокировка номера")
def suspend_ctn_app(
    request: SuspendRestoreCTN,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Добровольная блокировка номера (suspendCTN).

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



@router.post("/replaceSIM", summary="Замена SIM-карты")
def replace_sim_app(
    request: ReplaceSIM,
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

@router.post("/addDelSOC", summary="Подключить/отключить услугу")
def add_del_soc_app(
    request: AddDelSOC,
    ctn: str,
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
        ctn,
        soc=request.soc,
        inclusion_type=request.inclusion_type,
        eff_date=request.eff_date,
        exp_date=request.exp_date
    )
    return {"status": "success", "data": result}



@router.post("/getSIMList", summary="Получить список SIM-карт")
def get_sim_list_app(
    request: GetSIMList,
    ctn: str = None,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка SIM-карт абонента.
    """
    result = beeline_soap.get_sim_list(
        ctn=ctn,
        ban=request.ban
    )
    return {"status": "success", "data": result}

@router.post("/getSIMListPaged", summary="Получить список SIM-карт (пагинация)")
def get_sim_list_paged_app(
    request: GetSIMListPaged,
    ctn: str = None,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка SIM-карт с пагинацией.
    """
    result = beeline_soap.get_sim_list_paged(
        ctn=ctn,
        ban=request.ban,
        page=request.page,
        records_per_page=request.records_per_page
    )
    return {"status": "success", "data": result}



@router.post("/getRequestList", summary="Получить список запросов")
def get_request_list_app(
    request: GetRequestList,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка запросов на детализацию.
    """
    result = beeline_soap.get_request_list(
        start_date=request.start_date,
        end_date=request.end_date,
        request_id=request.request_id,
        page=request.page,
        records_per_page=request.records_per_page
    )
    return {"status": "success", "data": result}



@router.post("/getServicesList", summary="Получить список услуг")
def get_services_list_app(
    request: GetServicesList,
    ctn: str = None,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка активных услуг абонента.
    """
    result = beeline_soap.get_services_list(
        ctn=ctn,
        ban=request.ban
    )
    return {"status": "success", "data": result}

@router.post("/getServicesListPaged", summary="Получить список услуг (пагинация)")
def get_services_list_paged_app(
    request: GetServicesListPaged,
    ctn: str = None,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка услуг с пагинацией.
    """
    result = beeline_soap.get_services_list_paged(
        ctn=ctn,
        ban=request,
        page=request.page,
        ctn_amount_per_page=request.ctn_amount_per_page
    )
    return {"status": "success", "data": result}



@router.post("/getCTNInfoList", summary="Получить информацию об абонентах")
def get_ctn_info_list_app(
    request: GetCTNInfoList,
    ctn: str = None,
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
    request: GetCTNInfoListPaged,
    ctn: str = None,
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



@router.post("/getPaymentList", summary="Получить список платежей")
def get_payment_list_app(
    request: GetPaymentList,
    ctn: str = None,
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
        ctn=ctn,
        ban=request.ban,
        start_date=request.start_date,
        end_date=request.end_date
    )
    return {"status": "success", "data": result}

@router.post("/getPaymentListPaged", summary="Получить список платежей (пагинация)")
def get_payment_list_paged_app(
    request: GetPaymentListPaged,
    ctn: str = None,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка платежей с пагинацией.
    """
    result = beeline_soap.get_payment_list_paged(
        ctn=ctn,
        ban=request.ban,
        start_date=request.start_date,
        end_date=request.end_date,
        page=request.page,
        records_per_page=request.records_per_page
    )
    return {"status": "success", "data": result}

@router.post("/getUnbilledBalance", summary="Получить небиллингованный баланс")
def get_unbilled_balance_app(
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение небиллингованного баланса по номеру контракта.
    """
    result = beeline_soap.get_unbilled_balance(
        ctn=ctn
    )
    return {"status": "success", "data": result}

@router.post("/getUnbilledCallsList", summary="Получения информации о необилленных звонках абонента")
def get_unbilled_calls_list_app(
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение небиллингованного баланса по номеру контракта.
    """
    result = beeline_soap.get_unbilled_balance(
        ctn=ctn
    )
    return {"status": "success", "data": result}



@router.post("/getAdjustmentList", summary="Получить список корректировок")
def get_adjustment_list_app(
    request: GetAdjustmentList,
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



@router.post("/createBillCallsRequest", summary="Создать счет")
def create_bill_calls_request_app(
    request: CreateBillCallsChargesRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Создание счета для абонента.
    """
    result = beeline_soap.create_bill_calls_request(
        contract_number=request.contractNumber,
        amount=request.amount,
        description=request.description
    )
    return {"status": "success", "data": result}

@router.post("/createBillChargesRequest", summary="Создать счет")
def create_bill_charges_request_app(
    request: CreateBillCallsChargesRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Создание счета для абонента.
    """
    result = beeline_soap.create_bill_charges_request(
        contract_number=request.contractNumber,
        amount=request.amount,
        description=request.description
    )
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



@router.post("/getBANInfoList", summary="Получить информацию о BAN")
def get_ban_info_list_app(
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение информации о BAN.
    """
    result = beeline_soap.get_ban_info_list()
    return {"status": "success", "data": result}

@router.post("/getBANInfoListPaged", summary="Получить информацию о BAN (пагинация)")
def get_ban_info_list_paged_app(
    request: GetBANInfoListPaged,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение информации о BAN с пагинацией.
    """
    result = beeline_soap.get_ban_info_list_paged(
        page=request.page,
        records_per_page=request.records_per_page
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



@router.post("/getDetails", summary="Получить детализацию звонков")
def get_details_app(
    request: GetDetails,
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



@router.post("/addSharedNumberDOL", summary="Добавить общие номера")
def add_shared_number_dol_app(
    request: AddSharedNumberDOL,
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

@router.post("/addSharedNumberListDOL", summary="Добавить общие номера")
def add_shared_number_list_dol_app(
    request: AddSharedNumberListDOL,
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
    request: DeleteSharedNumberListDOL,
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
    request: PersonalDataResult,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение результата обновления персональных данных.
    """
    result = beeline_soap.personal_data_result(request_id=request.requestId)
    return {"status": "success", "data": result}



@router.post("/getData", summary="Получить данные")
def get_data_app(
    request: GetData,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение данных по запросу.
    """
    result = beeline_soap.get_data(request_id=request.requestId)
    return {"status": "success", "data": result}



@router.post("/getDataReport", summary="Получить отчет по данным")
def get_data_report_app(
    request: GetDataReport,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение отчета по данным.
    """
    result = beeline_soap.get_data_report(report_id=request.reportId)
    return {"status": "success", "data": result}