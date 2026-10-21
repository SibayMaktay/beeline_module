"""
Роутер для SOAP API Beeline (WSAPI)
Все методы WSAPI Beeline доступны через этот роутер
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Header, Query
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


def ctn_10_validator(ctn: str = Query(..., description="Номер **ctn** (ровно 10-11 цифр)")) -> str:
    if not re.fullmatch(r'\d{10,11}', ctn):
        raise HTTPException(status_code=422, detail="ctn должен содержать ровно 10 цифр")
    return ctn



@router.post("/suspendCTN", summary="Добровольная блокировка номера")
def suspend_ctn_app(
    request: SuspendRestoreCTN,
    ctn: str = Depends(ctn_10_validator),
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Добровольная блокировка номера (suspendCTN).

    - **ctn**: номер ctn
    - **reason_code**: причина блокировки:
        - **WIB** – по желанию (полная);
        - **WIO** – по желанию на исх. связь;
        - **STB** – по утере/краже (полная);
        - **STO** – по утере/краже на исх. связь;
        - **S1B** – сохранение (полная);
        - **BRB** – блокировка по бронированию.
    - **actv_date**: дата блокировки
    """
    data = beeline_soap.suspend_ctn(
        ctn=ctn,
        reason_code=request.reason_code,
        actv_date=request.actv_date
    )
    return {"status": "success", "data": data}

@router.post("/restoreCTN", summary="Разблокировка номера")
def restore_ctn_app(
    request: SuspendRestoreCTN,
    ctn: str = Depends(ctn_10_validator),
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Разблокировка номера (restoreCTN).

    - **ctn**: номер ctn
    - **reason_code**: причина разблокировки:
        - **RSBO** – по желанию (полная) – может разблокировать причины блокировок **WIB**, **WIO**, **STB**, **STO**;
        - **RS1B** – по сохранению (полная) – может разблокировать **S1B**;
        - **OBRB** – по бронированию – может разблокировать только **BRB**.
    - **actv_date**: дата разблокировки
    """
    data = beeline_soap.restore_ctn(
        ctn=ctn,
        reason_code=request.reason_code,
        actv_date=request.actv_date
    )
    return {"status": "success", "data": data}



@router.post("/replaceSIM", summary="Замена SIM-карты")
def replace_sim_app(
    request: ReplaceSIM,
    ctn: str = Depends(ctn_10_validator),
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Замена SIM-карты.

    - **ctn**: номер ctn
    - **serial_number**: номер SIM-карты
    """
    data = beeline_soap.replace_sim(
        ctn=ctn,
        serial_number=request.serial_number,
    )
    return {"status": "success", "data": data}



@router.post("/changePP", summary="Сменить тарифный план")
def change_pp_app(
    request: ChangePP,
    ctn: str = Depends(ctn_10_validator),
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Смена тарифного плана (Price Plan).

    - **ctn**: номер ctn
    - **price_plan**: код нового тарифного плана
    - **future_date**: Индикатор производить смену тарифного плана текущей датой:
        - **Y** – смена будет произведена с начала нового периода (только для postpaid, для prepaid смена всегда текущей датой);
        - **N** (или поле незаполнено) – смена тарифного плана будет произведена текущей датой.
    - **free_change**: Признак освобождения от платы за переход:
        - **false** - (смена тарифа платная);
        - **true** - (смена тарифа бесплатна);
        - значение по умолчанию **false**.
    """
    data = beeline_soap.change_pp(
        ctn=ctn,
        price_plan=request.price_plan,
        future_date=request.future_date,
        free_change=request.free_change
    )
    return {"status": "success", "data": data}



@router.post("/addDelSOC", summary="Подключить/отключить услугу")
def add_del_soc_app(
    request: AddDelSOC,
    ctn: str = Depends(ctn_10_validator),
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Подключение или отключение услуг (SOC).

    - **ctn**: номер ctn
    - **soc**: код услуги
    - **inclusion_type**: индикатор подключения/отключения услуги: 
        - **A** – подключение услуги;
        - **D** – отключение услуги.
    - **eff_date**: дата фактического подключения/отключения услуги
    - **exp_date**: дата автоматического отключения услуги
    """
    data = beeline_soap.add_del_soc(
        ctn=ctn,
        soc=request.soc,
        inclusion_type=request.inclusion_type,
        eff_date=request.eff_date,
        exp_date=request.exp_date
    )
    return {"status": "success", "data": data}



@router.post("/getSIMList", summary="Получить список SIM-карт")
def get_sim_list_app(
    request: GetSIMList,
    ctn: str = None,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка SIM-карт абонента.

    - **ctn**: номер ctn
    - **ban**: номер ban
    """
    data = beeline_soap.get_sim_list(
        ctn=ctn,
        ban=request.ban
    )
    return {"status": "success", "data": data}

@router.post("/getSIMListPaged", summary="Получить список SIM-карт (пагинация)")
def get_sim_list_paged_app(
    request: GetSIMListPaged,
    ctn: str = None,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка SIM-карт с пагинацией.

    - **ctn**: номер ctn
    - **ban**: номер ban
    - **page**: номер страницы выдачи
    - **records_per_page**: количество записей на странице выдачи
    """
    data = beeline_soap.get_sim_list_paged(
        ctn=ctn,
        ban=request.ban,
        page=request.page,
        records_per_page=request.records_per_page
    )
    return {"status": "success", "data": data}



@router.post("/getRequestList", summary="Получить список запросов")
def get_request_list_app(
    request: GetRequestList,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка запросов на детализацию.

    - **start_date**: дата начала периода для получения списка запросов
    - **end_date**: дата конца периода для получения списка запросов
    - **request_id**: номер запроса
    - **page**: номер страницы выдачи
    - **records_per_page**: количество записей на странице выдачи
    """
    data = beeline_soap.get_request_list(
        start_date=request.start_date,
        end_date=request.end_date,
        request_id=request.request_id,
        page=request.page,
        records_per_page=request.records_per_page
    )
    return {"status": "success", "data": data}



@router.post("/getServicesList", summary="Получить список услуг")
def get_services_list_app(
    request: GetServicesList,
    ctn: str = None,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка активных услуг абонента.

    - **ctn**: номер ctn
    - **ban**: номер ban
    """
    data = beeline_soap.get_services_list(
        ctn=ctn,
        ban=request.ban
    )
    return {"status": "success", "data": data}

@router.post("/getServicesListPaged", summary="Получить список услуг (пагинация)")
def get_services_list_paged_app(
    request: GetServicesListPaged,
    ctn: str = None,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка услуг с пагинацией.

    - **ctn**: номер ctn
    - **ban**: номер ban
    - **page**: номер страницы выдачи
    - **ctn_amount_per_page**: количество CTN со списком услуг на странице выдачи
    """
    data = beeline_soap.get_services_list_paged(
        ctn=ctn,
        ban=request.ban,
        page=request.page,
        ctn_amount_per_page=request.ctn_amount_per_page
    )
    return {"status": "success", "data": data}



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
    data = beeline_soap.get_ctn_info_list(
        ctn=ctn,
        ban=request.ban
    )
    return {"status": "success", "data": data}

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
    - **page**: номер страницы выдачи
    - **records_per_page**: количество записей на странице выдачи
    """
    data = beeline_soap.get_ctn_info_list_paged(
        ctn=ctn,
        ban=request.ban,
        page=request.page,
        records_per_page=request.records_per_page
    )
    return {"status": "success", "data": data}



@router.post("/getPaymentList", summary="Получить список платежей")
def get_payment_list_app(
    request: GetPaymentList,
    ctn: str = None,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка платежей за указанный период.

    - **ctn**: номер ctn
    - **ban**: номер ban
    - **start_date**: дата начала периода для получения платежей
    - **end_date**: дата конца периода для получения платежей
    """
    data = beeline_soap.get_payment_list(
        ctn=ctn,
        ban=request.ban,
        start_date=request.start_date,
        end_date=request.end_date
    )
    return {"status": "success", "data": data}

@router.post("/getPaymentListPaged", summary="Получить список платежей (пагинация)")
def get_payment_list_paged_app(
    request: GetPaymentListPaged,
    ctn: str = None,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка платежей с пагинацией.

    - **ctn**: номер ctn
    - **ban**: номер ban
    - **start_date**: дата начала периода для получения платежей
    - **end_date**: дата конца периода для получения платежей
    - **page**: номер страницы выдачи
    - **records_per_page**: количество записей на странице выдачи
    """
    data = beeline_soap.get_payment_list_paged(
        ctn=ctn,
        ban=request.ban,
        start_date=request.start_date,
        end_date=request.end_date,
        page=request.page,
        records_per_page=request.records_per_page
    )
    return {"status": "success", "data": data}

@router.post("/getUnbilledBalance", summary="Получить небиллингованный баланс")
def get_unbilled_balance_app(
    ctn: str = Depends(ctn_10_validator),
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение небиллингованного баланса по номеру контракта.

    - **ctn**: номер ctn
    """
    data = beeline_soap.get_unbilled_balance(
        ctn=ctn
    )
    return {"status": "success", "data": data}

@router.post("/getUnbilledCallsList", summary="Получения информации о необилленных звонках абонента")
def get_unbilled_calls_list_app(
    ctn: str = Depends(ctn_10_validator),
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение небиллингованного баланса по номеру контракта.

    - **ctn**: номер ctn
    """
    data = beeline_soap.get_unbilled_calls_list(
        ctn=ctn
    )
    return {"status": "success", "data": data}



@router.post("/getAdjustmentList", summary="Получить список корректировок")
def get_adjustment_list_app(
    request: GetAdjustmentList,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение списка корректировок за период.

    - **ban**: номер ban
    - **start_date**: дата начала периода для получения корректировок
    - **end_date**: дата конца периода для получения корректировок
    """
    data = beeline_soap.get_adjustment_list(
        ban=request.ban,
        start_date=request.start_date,
        end_date=request.end_date
    )
    return {"status": "success", "data": data}



@router.post("/createBillCallsRequest", summary="Создать счет")
def create_bill_calls_request_app(
    request: CreateBillCallsChargesRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Создание счета для абонента.

    - **ban**: номер ban
    - **bill_date**: дата выставления счета (время всегда принимает значение 00:00:00.000)
    - **ctn_list**: список абонентов
    """
    data = beeline_soap.create_bill_calls_request(
        ban=request.ban,
        bill_date=request.bill_date,
        ctn_list=request.ctn_list
    )
    return {"status": "success", "data": data}

@router.post("/createBillChargesRequest", summary="Создать счет")
def create_bill_charges_request_app(
    request: CreateBillCallsChargesRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Создание счета для абонента.

    - **ban**: номер ban
    - **bill_date**: дата выставления счета (время всегда принимает значение 00:00:00.000)
    - **ctn_list**: список абонентов
    """
    data = beeline_soap.create_bill_charges_request(
        ban=request.ban,
        bill_date=request.bill_date,
        ctn_list=request.ctn_list
    )
    return {"status": "success", "data": data}



@router.post("/getBillCalls", summary="Получить биллинг звонков")
def get_bill_calls_app(
    request: GetBillCallsCharges,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение биллинга звонков за период.

    - **request_id**: номер запроса на отчет
    """
    data = beeline_soap.get_bill_calls(
        request_id=request.request_id
    )
    return {"status": "success", "data": data}

@router.post("/getBillCallsPaged", summary="Получить биллинг звонков (пагинация)")
def get_bill_calls_paged_app(
    request: GetBillCallsChargesPaged,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение биллинга звонков с пагинацией.

    - **request_id**: номер запроса на отчет
    - **page**: номер страницы выдачи
    - **records_per_page**: количество записей на странице выдачи
    """
    data = beeline_soap.get_bill_calls_paged(
        request_id=request.request_id,
        page=request.page,
        records_per_page=request.records_per_page
    )
    return {"status": "success", "data": data}



@router.post("/getBillCharges", summary="Получить биллинг списаний")
def get_bill_charges_app(
    request: GetBillCallsCharges,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение биллинга списаний за период.

    - **request_id**: номер запроса на отчет
    """
    data = beeline_soap.get_bill_charges(
        request_id=request.request_id
    )
    return {"status": "success", "data": data}

@router.post("/getBillChargesPaged", summary="Получить биллинг списаний (пагинация)")
def get_bill_charges_paged_app(
    request: GetBillCallsChargesPaged,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение биллинга списаний с пагинацией.

    - **request_id**: номер запроса на отчет
    - **page**: номер страницы выдачи
    - **records_per_page**: количество записей на странице выдачи
    """
    data = beeline_soap.get_bill_charges_paged(
        request_id=request.request_id,
        page=request.page,
        records_per_page=request.records_per_page
    )
    return {"status": "success", "data": data}



@router.post("/getBANInfoList", summary="Получить информацию о BAN")
def get_ban_info_list_app(
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение информации о BAN.
    """
    data = beeline_soap.get_ban_info_list()
    return {"status": "success", "data": data}

@router.post("/getBANInfoListPaged", summary="Получить информацию о BAN (пагинация)")
def get_ban_info_list_paged_app(
    request: GetBANInfoListPaged,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение информации о BAN с пагинацией.

    - **page**: номер страницы выдачи
    - **records_per_page**: количество записей на странице выдачи
    """
    data = beeline_soap.get_ban_info_list_paged(
        page=request.page,
        records_per_page=request.records_per_page
    )
    return {"status": "success", "data": data}



@router.post("/createDetails", summary="Создать запрос на детализацию")
def create_details_app(
    request: CreateDetailsRequest,
    ctn: str = Depends(ctn_10_validator),
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Создание запроса на выгрузку детализации.

    - **ctn**: номер ctn
    - **period_start**: дата начала периода
    - **period_end**: дата конца периода
    - **format_**: формат файла
    - **channel**: канал отправки файла
    - **email**: email адрес
    """
    data = beeline_soap.create_details_request(
        ctn=ctn,
        period_start=request.period_start,
        period_end=request.period_end,
        format_=request.format_,
        channel=request.channel,
        email=request.email
    )
    return {"status": "success", "data": data}



@router.post("/getDetails", summary="Получить детализацию звонков")
def get_details_app(
    request: GetDetails,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение детализации звонков за период.

    - **request_id**: номер запроса на отчет
    """
    data = beeline_soap.get_details(
        request_id=request.request_id
    )
    return {"status": "success", "data": data}



@router.post("/addSharedNumberDOL", summary="Добавить общие номера")
def add_shared_number_dol_app(
    request: AddSharedNumberDOL,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Добавление списка общих номеров (DoL).

    - **ctn_from**: основной номер
    - **ctn_to**: дополнительный номер
    - **ctn_type**: тип расшаривания:
        - **E** - everything;
        - **D** - data;
        - по умолчанию **D**.
    - **soc**: код услуги владельца из Ensemble
    - **prepaid_state_chk_cancel**: параметр означает, делать ли проверку статуса основного и дополнительного номера/номеров на Comverse. (значение по умолчанию **false**, если не передан)
    - **check_add_number_registration**: параметр означает, делать ли проверку на наличие зарегистрированного договора в Ансамбле для допномера:
        - **true** – выполнять проверку наличия регистрации;
        - **false** – не выполнять проверку наличия регистрации.
        - Значение по умолчанию **false**, если не передан.
    """
    data = beeline_soap.add_shared_number_dol(
        ctn_from=request.ctn_from,
        ctn_to=request.ctn_to,
        ctn_type=request.ctn_type,
        soc=request.soc,
        prepaid_state_chk_cancel=request.prepaid_state_chk_cancel,
        check_add_number_registration=request.check_add_number_registration
    )
    return {"status": "success", "data": data}

@router.post("/addSharedNumberListDOL", summary="Добавить общие номера")
def add_shared_number_list_dol_app(
    request: AddSharedNumberListDOL,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Добавление списка общих номеров (DoL).

    - **ctn_from**: основной номер
    - **ctn_type**: список дополнительных номеров
    - **ctn_to**: дополнительный номер
    - **soc**: код услуги владельца из Ensemble
    - **prepaid_state_chk_cancel**: параметр означает, делать ли проверку статуса основного и дополнительного номера/номеров на Comverse. (значение по умолчанию **false**, если не передан)
    - **check_add_number_registration**: параметр означает, делать ли проверку на наличие зарегистрированного договора в Ансамбле для допномера:
        - **true** – выполнять проверку наличия регистрации;
        - **false** – не выполнять проверку наличия регистрации.
        - Значение по умолчанию **false**, если не передан.
    """
    data = beeline_soap.add_shared_number_list_dol(
        ctn_from=request.ctn_from,
        ctn_to_list=request.ctn_to_list,
        ctn_to=request.ctn_to,
        soc=request.soc,
        prepaid_state_chk_cancel=request.prepaid_state_chk_cancel,
        check_add_number_registration=request.check_add_number_registration
    )
    return {"status": "success", "data": data}

@router.post("/deleteSharedNumberListDOL", summary="Удалить общие номера")
def delete_shared_number_list_dol_app(
    request: DeleteSharedNumberListDOL,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Удаление списка общих номеров (DoL).

    - **ctn_from**: основной номер
    - **ctn_to_list**: список дополнительных номеров
    - **ctn_to**: дополнительный номер
    """
    data = beeline_soap.delete_shared_number_list_dol(
        ctn_from=request.ctn_from,
        ctn_to_list=request.ctn_to_list,
        ctn_to=request.ctn_to
    )
    return {"status": "success", "data": data}



@router.post("/personalDataUpdate", summary="Обновить персональные данные")
def personal_data_update_app(
    request: PersonalDataUpdate,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Обновление персональных данных абонента.

    | name (Название) | description (Описание) | value (Значение) | obligatoriness (Обязательность) | comment (Комментарий) |
    | :--- | :--- | :--- | :--- | :--- |
    | **ban** | **Лицевой счёт** - это номер договора, на который оформлен телефонный номер | ***string*** | **true** (***обязательное***)* | 9 цифр |
    | **ctn** | **Номер телефона** - это номер мобильного телефона абонента, их может быть несколько из-за этого введите через запятую, например (960802xxx1,960802xxx2,960802xxx3) | ***string*** | **true** (***обязательное***)* | 10 цифр (без знаков +7, 7, 8) |
    | **citizenship** | **Гражданство** (Код гражданства показана таблицей ниже) | ***string*** | **false** (***необязательное***) | Оставьте пустым если значение равен **RUS** |
    | **docNo** | **Номер документа** | ***string*** | **true** (***обязательное***)* | 10 цифр. Номер и серия слитно без пробелов. |
    | **docType** | **Тип документа** | ***string*** | **false** (***необязательное***) | Оставьте пустым если значение равен **1** |
    | **docIssueDate** | **Дата выдачи** | ***string*** | **true** (***обязательное***)* | дд.мм.гггг |
    | **docIssuer** | **Кем выдан** | ***string*** | **false** (***необязательное***) |
    | **docIssuerCode** | **Код подразделения выдавшего документ** | ***string*** | **false** (***необязательное***) | 6 цифр (например, 123456) |
    | **docExpirationDate** | **Документ действителен до** | ***string*** | **false** (***необязательное***) | дд.мм.гггг |
    | **birthdate** | **Дата рождения** | ***string*** | **true** (***обязательное***)* | дд.мм.гггг |
    | **frnMigcard** | **Номер миграционной карты** | ***string*** | **false** (***необязательное***) |
    | **frnMigcardEffDate** | **Дата выдачи миграционной карты** | ***string*** | **false** (***необязательное***) | дд.мм.гггг |
    | **frnMigcardExpDate** | **Срок действия миграционной карты** | ***string*** | **false** (***необязательное***) | дд.мм.гггг |
    | **frnDoc** | **Документ нерезидента** | ***string*** | **false** (***необязательное***) |
    | **firstName** | **Имя** | ***string*** | **true** (***обязательное***)* |
    | **surName** | **Отчество** | ***string*** | **false** (***необязательное***) | Отчество при наличии |
    | **lastName** | **Фамилия** | ***string*** | **true** (***обязательное***)* |
    | **birthplace** | **Место рождения** | ***string*** | **false** (***необязательное***) |
    | **gender** | **Пол** | ***string*** | **true** (***обязательное***)* | **F** - женский, **M** - мужской |
    | **taxNumber** | **ИНН** | ***string*** | **false** (***необязательное***) |
    | **snils** | **СНИЛС** | ***string*** | **false** (***необязательное***) |
    | **legalPostcode** | **Адрес Регистрации** - Индекс | ***string*** | **false** (***необязательное***) |
    | **legalCountryCode** | **Адрес Регистрации** - Код страны (Код страны показана таблицей ниже) | ***string*** | **false** (***необязательное***) | Оставьте пустым если значение равен **RUS** |
    | **legalRegion** | **Адрес Регистрации** - Регион | ***string*** | **false** (***необязательное***) |
    | **legalArea** | **Адрес Регистрации** - Район | ***string*** | **false** (***необязательное***) |
    | **legalPlaceType** | **Адрес Регистрации** - Тип Населенного пункта | ***string*** | **true** (***обязательное***)* | **.**, **стан.**, **хут.**, **аул**, **пгт.**, **мкр.**, **район**, **п/р**, **рп.**, **г.**, **пос.**, **дер.**, **с.** Выбрать из списка. Если в преднастроенном списке тип отсутствует, то выбрать "**.**" и тип населенного пункта внести в наименование населенного пункта. |
    | **legalPlace** | **Адрес Регистрации** - Населенный пункт | ***string*** | **true** (***обязательное***)* |
    | **legalStreetType** | **Адрес Регистрации** - Тип улицы | ***string*** | **false** (***необязательное***) | **алл.**, **вал**, **ск-р**, **мкр**, **км**, **тр-т**, **лн.**, **ул.**, **пр-т**, **пер.**, **ш.**, **туп.**, **пр-д**, **пл.**, **б-р**, **наб.**, **кв-л** Выбрать из списка. |
    | **legalStreetName** | **Адрес Регистрации** - Улица | ***string*** | **false** (***необязательное***) |
    | **legalHouseType** | **Адрес Регистрации** - Тип дома | ***string*** | **false** (***необязательное***) | **вл.**, **д.**, **двл.**, **уч.**, **зд.**, **стр.** Выбрать из списка. |
    | **legalHouseNo** | **Адрес Регистрации** - Номер дома | ***string*** | **false** (***необязательное***) |
    | **legalBuildingType** | **Адрес Регистрации** - Тип строения | ***string*** | **false** (***необязательное***) | **влад.**, **зд.**, **пом.**, **лит.**, **Стр.**, **Корп.** Выбрать из списка. |
    | **legalBuildingNo** | **Адрес Регистрации** - Номер строения | ***string*** | **false** (***необязательное***) |
    | **legalApartmentType** | **Адрес Регистрации** - Тип помещения | ***string*** | **false** (***необязательное***) | **кв.**, **Ком.** Выбрать из списка. |
    | **legalApartmentNo** | **Адрес Регистрации** - Номер помещения | ***string*** | **false** (***необязательное***) |
    | **legalAddrComment** | **Адрес Регистрации** - Комментарий | ***string*** | **false** (***необязательное***) |
    | **legalFiasId** | **Адрес Регистрации** - ФИАС ИД | ***string*** | **false** (***необязательное***) |
    | **actualPostcode** | **Адрес Проживания** - Индекс | ***string*** | **false** (***необязательное***) |
    | **actualCountryCode** | **Адрес Проживания** - Код страны (Код страны показана таблицей ниже) | ***string*** | **false** (***необязательное***) | Оставьте пустым если значение равен **RUS** |
    | **actualRegion** | **Адрес Проживания** - Регион | ***string*** | **false** (***необязательное***) |
    | **actualArea** | **Адрес Проживания** - Район | ***string*** | **false** (***необязательное***) |
    | **actualPlaceType** | **Адрес Проживания** - Тип Населенного пункта | ***string*** | **true** (***обязательное***)* | **.**, **стан.**, **хут.**, **аул**, **пгт.**, **мкр.**, **район**, **п/р**, **рп.**, **г.**, **пос.**, **дер.**, **с.** Выбрать из списка. Если в преднастроенном списке тип отсутствует, то выбрать "**.**" и тип населенного пункта внести в наименование населенного пункта. |
    | **actualPlace** | **Адрес Проживания** - Населенный пункт | ***string*** | **true** (***обязательное***)* |
    | **actualStreetType** | **Адрес Проживания** - Тип улицы | ***string*** | **false** (***необязательное***) | **алл.**, **вал**, **ск-р**, **мкр**, **км**, **тр-т**, **лн.**, **ул.**, **пр-т**, **пер.**, **ш.**, **туп.**, **пр-д**, **пл.**, **б-р**, **наб.**, **кв-л** Выбрать из списка. |
    | **actualStreetName** | **Адрес Проживания** - Улица | ***string*** | **false** (***необязательное***) |
    | **actualHouseType** | **Адрес Проживания** - Тип дома | ***string*** | **false** (***необязательное***) | **вл.**, **д.**, **двл.**, **уч.**, **зд.**, **стр.** Выбрать из списка. |
    | **actualHouseNo** | **Адрес Проживания** - Номер дома | ***string*** | **false** (***необязательное***) |
    | **actualBuildingType** | **Адрес Проживания** - Тип строения | ***string*** | **false** (***необязательное***) | **влад.**, **зд.**, **пом.**, **лит.**, **Стр.**, **Корп.** Выбрать из списка. |
    | **actualBuildingNo** | **Адрес Проживания** - Номер строения | ***string*** | **false** (***необязательное***) |
    | **actualApartmentType** | **Адрес Проживания** - Тип помещения | ***string*** | **false** (***необязательное***) | **кв.**, **Ком.** Выбрать из списка. |
    | **actualApartmentNo** | **Адрес Проживания** - Номер помещения | ***string*** | **false** (***необязательное***) |
    | **actualAddrComment** | **Адрес Проживания** - Комментарий | ***string*** | **false** (***необязательное***) |
    | **actualFiasId** | **Адрес Проживания** - ФИАС ИД | ***string*** | **false** (***необязательное***) |
    **Примечание**: Поля, помеченные *обязательными*, должны быть заполнены в случае, если они присутствуют в запросе. Если поле не передано в запросе, оно не будет обновлено.

    **Код гражданства**: Для корректного обновления гражданства абонента необходимо использовать код страны, соответствующий гражданству. Ниже приведена таблица с кодами гражданства:
    | Страна | Код Гражданства |
    | :--- | :--- |
    | РОССИЯ | **RUS** |
    | АБХАЗИЯ | **ABH** |
    | АВСТРАЛИЯ | **AUS** |
    | АВСТРИЯ | **AUT** |
    | АЗЕРБАЙДЖАН | **AZE** |
    | АЛБАНИЯ | **ALB** |
    | АЛЖИР | **DZA** |
    | АМЕРИКАНСКОЕ САМОА | **ASM** |
    | АНГИЛЬЯ | **AIA** |
    | АНГОЛА | **AGO** |
    | АНДОРРА | **AND** |
    | АНТАРКТИДА | **ATA** |
    | АНТИГУА И БАРБУДА | **ATG** |
    | АРГЕНТИНА | **ARG** |
    | АРМЕНИЯ | **ARM** |
    | АРУБА | **ABW** |
    | АФГАНИСТАН | **AFG** |
    | БАГАМЫ | **BHS** |
    | БАНГЛАДЕШ | **BGD** |
    | БАРБАДОС | **BRB** |
    | БАХРЕЙН | **BHR** |
    | БЕЛАРУСЬ | **BLR** |
    | БЕЛИЗ | **BLZ** |
    | БЕЛЬГИЯ | **BEL** |
    | БЕНИН | **BEN** |
    | БЕРМУДЫ | **BMU** |
    | БОЛГАРИЯ | **BGR** |
    | БОЛИВИЯ, МНОГОНАЦИОНАЛЬНОЕ ГОСУДАРСТВО | **BOL** |
    | БОНЭЙР, СИНТ-ЭСТАТИУС И САБА | **BES** |
    | БОСНИЯ И ГЕРЦЕГОВИНА | **BIH** |
    | БОТСВАНА | **BWA** |
    | БРАЗИЛИЯ | **BRA** |
    | БРИТАНСКАЯ ТЕРРИТОРИЯ В ИНДИЙСКОМ ОКЕАНЕ | **IOT** |
    | БРУНЕЙ-ДАРУССАЛАМ | **BRN** |
    | БУРКИНА-ФАСО | **BFA** |
    | БУРУНДИ | **BDI** |
    | БУТАН | **BTN** |
    | ВАНУАТУ | **VUT** |
    | ВЕНГРИЯ | **HUN** |
    | ВЕНЕСУЭЛА БОЛИВАРИАНСКАЯ РЕСПУБЛИКА | **VEN** |
    | ВИРГИНСКИЕ ОСТРОВА, БРИТАНСКИЕ | **VGB** |
    | ВИРГИНСКИЕ ОСТРОВА, США | **VIR** |
    | ВЬЕТНАМ | **VNM** |
    | ГАБОН | **GAB** |
    | ГАЙАНА | **GUY** |
    | ГАИТИ | **HTI** |
    | ГАМБИЯ | **GMB** |
    | ГАНА | **GHA** |
    | ГВАДЕЛУПА | **GLP** |
    | ГВАТЕМАЛА | **GTM** |
    | ГВИНЕЯ | **GIN** |
    | ГВИНЕЯ-БИСАУ | **GNB** |
    | ГЕРМАНИЯ | **DEU** |
    | ГЕРНСИ | **GGY** |
    | ГИБРАЛТАР | **GIB** |
    | ГОНДУРАС | **HND** |
    | ГОНКОНГ | **HKG** |
    | ГРЕНАДА | **GRD** |
    | ГРЕНЛАНДИЯ | **GRL** |
    | ГРЕЦИЯ | **GRC** |
    | ГРУЗИЯ | **GEO** |
    | ГУАМ | **GUM** |
    | ДАНИЯ | **DNK** |
    | ДЖЕРСИ | **JEY** |
    | ДЖИБУТИ | **DJI** |
    | ДОМИНИКА | **DMA** |
    | ДОМИНИКАНСКАЯ РЕСПУБЛИКА | **DOM** |
    | ЕГИПЕТ | **EGY** |
    | ЗАМБИЯ | **ZMB** |
    | ЗАПАДНАЯ САХАРА | **ESH** |
    | ЗИМБАБВЕ | **ZWE** |
    | ЙЕМЕН | **YEM** |
    | ИЗРАИЛЬ | **ISR** |
    | ИНДИЯ | **IND** |
    | ИНДОНЕЗИЯ | **IDN** |
    | ИОРДАНИЯ | **JOR** |
    | ИРАК | **IRQ** |
    | ИРАН, ИСЛАМСКАЯ РЕСПУБЛИКА | **IRN** |
    | ИРЛАНДИЯ | **IRL** |
    | ИСЛАНДИЯ | **ISL** |
    | ИСПАНИЯ | **ESP** |
    | ИТАЛИЯ | **ITA** |
    | КАБО-ВЕРДЕ | **CPV** |
    | КАЗАХСТАН | **KAZ** |
    | КАМБОДЖА | **KHM** |
    | КАМЕРУН | **CMR** |
    | КАНАДА | **CAN** |
    | КАТАР | **QAT** |
    | КЕНИЯ | **KEN** |
    | КИПР | **CYP** |
    | КИРГИЗИЯ | **KGZ** |
    | КИРИБАТИ | **KIR** |
    | КИТАЙ | **CHN** |
    | КОКОСОВЫЕ (КИЛИНГ) ОСТРОВА | **CCK** |
    | КОЛУМБИЯ | **COL** |
    | КОМОРЫ | **COM** |
    | КОНГО | **COG** |
    | КОНГО, ДЕМОКРАТИЧЕСКАЯ РЕСПУБЛИКА | **COD** |
    | КОРЕЯ, НАРОДНО-ДЕМОКРАТИЧЕСКАЯ РЕСПУБЛИКА | **PRK** |
    | КОРЕЯ, РЕСПУБЛИКА | **KOR** |
    | КОСТА-РИКА | **CRI** |
    | КОТ Д'ИВУАР | **CIV** |
    | КУБА | **CUB** |
    | КУВЕЙТ | **KWT** |
    | КЮРАСАО | **CUW** |
    | ЛАОССКАЯ НАРОДНО-ДЕМОКРАТИЧЕСКАЯ РЕСПУБЛИКА | **LAO** |
    | ЛАТВИЯ | **LVA** |
    | ЛЕСОТО | **LSO** |
    | ЛИБЕРИЯ | **LBR** |
    | ЛИВАН | **LBN** |
    | ЛИВИЯ | **LBY** |
    | ЛИТВА | **LTU** |
    | ЛИХТЕНШТЕЙН | **LIE** |
    | ЛЮКСЕМБУРГ | **LUX** |
    | МАВРИКИЙ | **MUS** |
    | МАВРИТАНИЯ | **MRT** |
    | МАДАГАСКАР | **MDG** |
    | МАЙОТТА | **MYT** |
    | МАКАО | **MAC** |
    | МАЛАВИ | **MWI** |
    | МАЛАЙЗИЯ | **MYS** |
    | МАЛИ | **MLI** |
    | МАЛЫЕ ТИХООКЕАНСКИЕ ОТДАЛЕННЫЕ ОСТРОВА СОЕДИНЕННЫХ ШТАТОВ | **UMI** |
    | МАЛЬДИВЫ | **MDV** |
    | МАЛЬТА | **MLT** |
    | МАРОККО | **MAR** |
    | МАРТИНИКА | **MTQ** |
    | МАРШАЛЛОВЫ ОСТРОВА | **MHL** |
    | МЕКСИКА | **MEX** |
    | МИКРОНЕЗИЯ, ФЕДЕРАТИВНЫЕ ШТАТЫ | **FSM** |
    | МОЗАМБИК | **MOZ** |
    | МОЛДОВА, РЕСПУБЛИКА | **MDA** |
    | МОНАКО | **MCO** |
    | МОНГОЛИЯ | **MNG** |
    | МОНТСЕРРАТ | **MSR** |
    | МЬЯНМА | **MMR** |
    | НАМИБИЯ | **NAM** |
    | НАУРУ | **NRU** |
    | НЕПАЛ | **NPL** |
    | НИГЕР | **NER** |
    | НИГЕРИЯ | **NGA** |
    | НИДЕРЛАНДЫ | **NLD** |
    | НИКАРАГУА | **NIC** |
    | НИУЭ | **NIU** |
    | НОВАЯ ЗЕЛАНДИЯ | **NZL** |
    | НОВАЯ КАЛЕДОНИЯ | **NCL** |
    | НОРВЕГИЯ | **NOR** |
    | ОБЪЕДИНЕННЫЕ АРАБСКИЕ ЭМИРАТЫ | **ARE** |
    | ОМАН | **OMN** |
    | ОСТРОВ БУВЕ | **BVT** |
    | ОСТРОВ МЭН | **IMN** |
    | ОСТРОВ НОРФОЛК | **NFK** |
    | ОСТРОВ РОЖДЕСТВА | **CXR** |
    | ОСТРОВ ХЕРД И ОСТРОВА МАКДОНАЛЬД | **HMD** |
    | ОСТРОВА КАЙМАН | **CYM** |
    | ОСТРОВА КУКА | **COK** |
    | ОСТРОВА ТЕРКС И КАЙКОС | **TCA** |
    | ПАКИСТАН | **PAK** |
    | ПАЛАУ | **PLW** |
    | ПАЛЕСТИНА, ГОСУДАРСТВО | **PSE** |
    | ПАНАМА | **PAN** |
    | ПАПСКИЙ ПРЕСТОЛ (ГОСУДАРСТВО  -   ГОРОД ВАТИКАН) | **VAT** |
    | ПАПУА НОВАЯ ГВИНЕЯ | **PNG** |
    | ПАРАГВАЙ | **PRY** |
    | ПЕРУ | **PER** |
    | ПИТКЕРН | **PCN** |
    | ПОЛЬША | **POL** |
    | ПОРТУГАЛИЯ | **PRT** |
    | ПУЭРТО-РИКО | **PRI** |
    | РЕСПУБЛИКА МАКЕДОНИЯ | **MKD** |
    | РЕЮНЬОН | **REU** |
    | РУАНДА | **RWA** |
    | РУМЫНИЯ | **ROU** |
    | САМОА | **WSM** |
    | САН-МАРИНО | **SMR** |
    | САН-ТОМЕ И ПРИНСИПИ | **STP** |
    | САУДОВСКАЯ АРАВИЯ | **SAU** |
    | СВАЗИЛЕНД | **SWZ** |
    | СВЯТАЯ ЕЛЕНА, ОСТРОВ ВОЗНЕСЕНИЯ, ТРИСТАН-ДА-КУНЬЯ | **SHN** |
    | СЕВЕРНЫЕ МАРИАНСКИЕ ОСТРОВА | **MNP** |
    | СЕЙШЕЛЫ | **SYC** |
    | СЕН-БАРТЕЛЕМИ | **BLM** |
    | СЕНЕГАЛ | **SEN** |
    | СЕН-МАРТЕН | **MAF** |
    | СЕН-МАРТЕН (нидерландская часть) | **SXM** |
    | СЕН-ПЬЕР И МИКЕЛОН | **SPM** |
    | СЕНТ-ВИНСЕНТ И ГРЕНАДИНЫ | **VCT** |
    | СЕНТ-КИТС И НЕВИС | **KNA** |
    | СЕНТ-ЛЮСИЯ | **LCA** |
    | СЕРБИЯ | **SRB** |
    | СИНГАПУР | **SGP** |
    | СИРИЙСКАЯ АРАБСКАЯ РЕСПУБЛИКА | **SYR** |
    | СЛОВАКИЯ | **SVK** |
    | СЛОВЕНИЯ | **SVN** |
    | СОЕДИНЕННОЕ КОРОЛЕВСТВО | **GBR** |
    | СОЕДИНЕННЫЕ ШТАТЫ | **USA** |
    | СОЛОМОНОВЫ ОСТРОВА | **SLB** |
    | СОМАЛИ | **SOM** |
    | СУДАН | **SDN** |
    | СУРИНАМ | **SUR** |
    | СЬЕРРА-ЛЕОНЕ | **SLE** |
    | ТАДЖИКИСТАН | **TJK** |
    | ТАЙВАНЬ (КИТАЙ) | **TWN** |
    | ТАИЛАНД | **THA** |
    | ТАНЗАНИЯ, ОБЪЕДИНЕННАЯ РЕСПУБЛИКА | **TZA** |
    | ТИМОР-ЛЕСТЕ | **TLS** |
    | ТОГО | **TGO** |
    | ТОКЕЛАУ | **TKL** |
    | ТОНГА | **TON** |
    | ТРИНИДАД И ТОБАГО | **TTO** |
    | ТУВАЛУ | **TUV** |
    | ТУНИС | **TUN** |
    | ТУРКМЕНИЯ | **TKM** |
    | ТУРЦИЯ | **TUR** |
    | УГАНДА | **UGA** |
    | УЗБЕКИСТАН | **UZB** |
    | УКРАИНА | **UKR** |
    | УОЛЛИС И ФУТУНА | **WLF** |
    | УРУГВАЙ | **URY** |
    | ФАРЕРСКИЕ ОСТРОВА | **FRO** |
    | ФИДЖИ | **FJI** |
    | ФИЛИППИНЫ | **PHL** |
    | ФИНЛЯНДИЯ | **FIN** |
    | ФОЛКЛЕНДСКИЕ ОСТРОВА (МАЛЬВИНСКИЕ) | **FLK** |
    | ФРАНЦИЯ | **FRA** |
    | ФРАНЦУЗСКАЯ ГВИАНА | **GUF** |
    | ФРАНЦУЗСКАЯ ПОЛИНЕЗИЯ | **PYF** |
    | ФРАНЦУЗСКИЕ ЮЖНЫЕ ТЕРРИТОРИИ | **ATF** |
    | ХОРВАТИЯ | **HRV** |
    | ЦЕНТРАЛЬНО-АФРИКАНСКАЯ РЕСПУБЛИКА | **CAF** |
    | ЧАД | **TCD** |
    | ЧЕРНОГОРИЯ | **MNE** |
    | ЧЕХИЯ | **CZE** |
    | ЧИЛИ | **CHL** |
    | ШВЕЙЦАРИЯ | **CHE** |
    | ШВЕЦИЯ | **SWE** |
    | ШПИЦБЕРГЕН И ЯН МАЙЕН | **SJM** |
    | ШРИ-ЛАНКА | **LKA** |
    | ЭКВАДОР | **ECU** |
    | ЭКВАТОРИАЛЬНАЯ ГВИНЕЯ | **GNQ** |
    | ЭЛАНДСКИЕ ОСТРОВА | **ALA** |
    | ЭЛЬ-САЛЬВАДОР | **SLV** |
    | ЭРИТРЕЯ | **ERI** |
    | ЭСТОНИЯ | **EST** |
    | ЭФИОПИЯ | **ETH** |
    | ЮЖНАЯ АФРИКА | **ZAF** |
    | ЮЖНАЯ ДЖОРДЖИЯ И ЮЖНЫЕ САНДВИЧЕВЫ ОСТРОВА | **SGS** |
    | ЮЖНАЯ ОСЕТИЯ | **OST** |
    | ЮЖНЫЙ СУДАН | **SSD** |
    | ЯМАЙКА | **JAM** |
    | ЯПОНИЯ | **JPN** |
    | Иное (без гражданства) | **000** |

    **Код документа**: Для корректного обновления типа документа абонента необходимо использовать код документа, соответствующий типу документа. Ниже приведена таблица с кодами документов:
    | Код типа документа | Тип документа |
    | :--- | :--- |
    | **1** | Паспорт |
    | **2** | Военный билет |
    | **3** | Удостоверение личности |
    | **4** | Паспорт иностранного гражданина |
    | **5** | Паспорт СССР |
    | **6** | Загранпаспорт РФ |
    | **7** | Вид на жительство |
    | **8** | Разрешение на временное проживание для лиц без гражданства |"""
    data = beeline_soap.personal_data_update(
        data=request.dict()
    )
    return {"status": "success", "data": data}

@router.post("/personalDataResult", summary="Получить результат обновления данных")
def personal_data_result_app(
    request: PersonalDataResult,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение результата обновления персональных данных.

    - **request_id**: идентификатор запроса (созданного методом **/personalDataUpdate**)
    """
    data = beeline_soap.personal_data_result(
        request_id=request.request_id
    )
    return {"status": "success", "data": data}



@router.post("/getData", summary="Получить данные")
def get_data_app(
    request: GetData,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение данных по запросу.

    - **ban**: номер ban
    - **hierarchy_id**: идентификатор иерархии (корпорации)
    - **subscriber_no**: номер абонента
    """
    data = beeline_soap.get_data(
        ban=request.ban,
        hierarchy_id=request.hierarchy_id,
        subscriber_no=request.subscriber_no
    )
    return {"status": "success", "data": data}

@router.post("/getDataReport", summary="Получить отчет по данным")
def get_data_report_app(
    request: GetDataReport,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_soap_client),
):
    """
    Получение отчета по данным.

    - **request_id**: Номер запроса (созданного методом **/getData**)
    - **page**: номер страницы выдачи
    - **records_per_page**: количество записей на странице выдачи
    """
    data = beeline_soap.get_data_report(
        request_id=request.request_id,
        page=request.page,
        records_per_page=request.records_per_page
    )
    return {"status": "success", "data": data}