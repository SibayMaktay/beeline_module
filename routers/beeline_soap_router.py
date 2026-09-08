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
    ctn: str,
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
    ctn: str,
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
    ctn: str,
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
    ctn: str,
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
        ban=request,
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
    ctn: str,
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
    ctn: str,
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
    request: GetBillCalls,
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
    request: GetBillCallsPaged,
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
    request: GetBillCharges,
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
    request: GetBillChargesPaged,
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
    ctn: str,
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

    - **ban**: Лицевой счёт
    - **statusBan**: Статус BAN
    - **ctn**: Номер телефона
    - **marketCode**: Код рынка
    - **docName**: Название документа
    - **changeDate**: Дата изменения
    - **startServiceDate**: Дата начала обслуживания
    - **confDate**: Дата подтверждения
    - **statusPdn**: Статус PDN
    - **blockDate**: Дата блокировки
    - **accessClientPdn**: Доступ клиента к PDN
    - **introPdn**: Ввод PDN
    - **citizenship**: Гражданство
    - **docNo**: Номер документа
    - **docType**: Тип документа
    - **docIssueDate**: Дата выдачи документа
    - **docIssuer**: Орган выдачи документа
    - **docIssuerCode**: Код органа выдачи
    - **docExpirationDate**: Дата истечения документа
    - **birthdate**: Дата рождения
    - **frnMigcard**: FRN миг карты
    - **frnMigcardEffDate**: Дата начала FRN миг карты
    - **frnMigcardExpDate**: Дата истечения FRN миг карты
    - **frnDoc**: FRN документа
    - **firstName**: Имя
    - **lastName**: Фамилия
    - **surName**: Отчество
    - **birthplace**: Место рождения
    - **gender**: Пол
    - **taxNumber**: ИНН
    - **snils**: СНИЛС
    - **legalPostcode**: АдрРег Индекс
    - **legalCountryCode**: АдрРег Код страны
    - **legalRegion**: АдрРег Регион
    - **legalArea**: АдрРег Район
    - **legalPlaceType**: АдрРег Тип НП
    - **legalPlace**: АдрРег Населенный пункт
    - **legalStreetType**: АдрРег Тип улицы
    - **legalStreetName**: АдрРег Улица
    - **legalHouseNo**: АдрРег Номер дома
    - **legalBuildingType**: АдрРег Тип строения
    - **legalBuildingNo**: АдрРег Номер строения
    - **legalApartmentType**: АдрРег Тип помещения
    - **legalApartmentNo**: АдрРег Номер помещения
    - **legalAddrComment**: АдрРег Комментарий
    - **legalFiasId**: АдрРег ФИАС ИД
    - **actualPostcode**: АдрПрож Индекс
    - **actualCountryCode**: АдрПрож Код страны
    - **actualRegion**: АдрПрож Регион
    - **actualArea**: АдрПрож Район
    - **actualPlaceType**: АдрПрож Тип НП
    - **actualPlace**: АдрПрож Населенный пункт
    - **actualStreetType**: АдрПрож Тип улицы
    - **actualStreetName**: АдрПрож Улица
    - **actualHouseNo**: АдрПрож Номер дома
    - **actualBuildingType**: АдрПрож Тип строения
    - **actualBuildingNo**: АдрПрож Номер строения
    - **actualApartmentType**: АдрПрож Тип помещения
    - **actualApartmentNo**: АдрПрож Номер помещения
    - **actualAddrComment**: АдрПрож Комментарий
    - **actualFiasId**: АдрПрож ФИАС ИД
    """
    data = beeline_soap.personal_data_update(
        data=request.data
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