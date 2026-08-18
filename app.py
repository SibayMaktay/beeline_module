import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, Any, List
import config.config as config

from client.beeline_soap_client import BeelineSoapClient
from client.beeline_rest_client import BeelineRestClient
from client.utm5_rest_client import UTM5RestClient
from token_api.token_beeline import get_beeline_token, invalidate_token
from token_api.token_utm5 import get_utm5_token

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Модели данных ---
class PaymentSyncRequest(BaseModel):
    ctn: str
    ban: str
    start_date: str
    end_date: str
    page: int = None
    records_per_page: str = None

class TariffChangeRequest(BaseModel):
    ctn: str
    price_plan: str
    utm5_user_id: int
    future_date: str = None
    free_change: str = None

TARIFF_MAPPING = {
    "BEELINE_TARIFF_1": "EXCLH11",
    "BEELINE_TARIFF_2": "EXCLH12",
    "BEELINE_TARIFF_3": "EXCLH13",
}

# --- Зависимости и DI-фабрики ---
def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != config.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key

def get_utm5_rest_client():
    return UTM5RestClient(
        base_url=config.utm5_api_url,
        api_key=config.utm5_api_key
    )

def get_beeline_rest_client():
    token = get_beeline_token()
    client = BeelineRestClient(
        base_url=config.beeline_url_base,
        signature=config.beeline_rest_signature
    )
    client.set_token(token)
    return client

def get_beeline_soap_client():
    # СВОЙ BeelineSoapClient реализуй! (или импортируй актуальный)
    return BeelineSoapClient(
        token_provider=get_beeline_token()
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Старт интеграции...")
    try:
        get_utm5_token()
    except Exception as e:
        logger.warning(f"UTM5 аутентификация не удалась на старте: {e}")
    try:
        get_beeline_token()
    except Exception as e:
        logger.warning(f"Beeline аутентификация не удалась на старте: {e}")
    yield
    logger.info("Завершение работы интеграционной службы...")

app = FastAPI(title="BeeLine-UTM5 Integration Module", version="1.0.0", lifespan=lifespan)

@app.get("/health", summary="Проверка работоспособности модуля")
async def health_check(
    utm5_client: UTM5RestClient = Depends(get_utm5_rest_client)
):
    is_utm5_ready = utm5_client is not None and hasattr(utm5_client, "session_id") and utm5_client.session_id is not None
    return {
        "status": "healthy",
        "service": "beeline-utm5-integration",
        "utm5_authenticated": is_utm5_ready,
    }

# --- REST Beeline (USSS) ---
@app.get("/rests/{ctn}", summary="Остатки пакетов абонента (REST)", tags=["REST Beeline"])
async def get_rests_app(
    ctn: str,
    client: Optional[str] = None,
    beeline_rest: BeelineRestClient = Depends(get_beeline_rest_client)
):
    data = beeline_rest.get_rests(
        ctn,
        client,
    )
    if data is None:
        raise HTTPException(status_code=502, detail="Beeline REST error")
    return {"status": "success", "data": data}

@app.get("/subscriptions/{ctn}", summary="Активные подписки абонента (REST)", tags=["REST Beeline"])
async def get_subscriptions(
    ctn: str,
    client: Optional[str] = None,
    beeline_rest: BeelineRestClient = Depends(get_beeline_rest_client)
):
    data = beeline_rest.get_subscriptions(
        ctn,
        client,
    )
    if data is None:
        raise HTTPException(status_code=502, detail="Beeline REST error")
    return {"status": "success", "data": data}

@app.get("/subscriptions/remove/{ctn}", summary="отключение подписки абонента (REST)", tags=["REST Beeline"])
async def remove_subscription_app(
    ctn: str,
    subscription_id: str = None,
    type: str = None,
    client: Optional[str] = None,
    beeline_rest: BeelineRestClient = Depends(get_beeline_rest_client)
):
    data = beeline_rest.remove_subscription(
        ctn,
        client,
        subscription_id,
        type,
    )
    if data is None:
        raise HTTPException(status_code=502, detail="Beeline REST error")
    return {"status": "success", "data": data}

@app.get("/callforward/request/{ctn}", summary="Создать запрос на получение параметров переадресации (REST, шаг 1)", tags=["REST Beeline"])
async def request_call_forward_app(
    ctn: str,
    client: Optional[str] = None,
    beeline_rest: BeelineRestClient = Depends(get_beeline_rest_client)
):
    data = beeline_rest.request_call_forward(
        ctn,
        client,
    )
    if data is None:
        raise HTTPException(status_code=502, detail="Beeline REST error /callForward request")
    return {"status": "success", "requestId": data.get("requestId"), "data": data}

@app.get("/callforward/info/{request_id}", summary="Получение параметров переадресации по requestId (REST, шаг 2)", tags=["REST Beeline"])
async def get_call_forward_by_request_app(
    request_id: int,
    client: Optional[str] = None,
    beeline_rest: BeelineRestClient = Depends(get_beeline_rest_client)
):
    data = beeline_rest.get_call_forward_by_request(
        request_id,
        client,
    )
    if data is None:
        raise HTTPException(status_code=502, detail="Beeline REST error /callForward info")
    return {"status": "success", "data": data}

class CallForwardData(BaseModel):
    cfType: Optional[str]
    cfCtn: Optional[str]
class PutCallForwardRequest(BaseModel):
    ctn: str
    call_forward_list: List[CallForwardData]
    client: Optional[str] = None

@app.put("/callforward/edit", summary="Установка параметров переадресации (REST, шаг 3)", tags=["REST Beeline"])
async def edit_call_forward_app(
    request: PutCallForwardRequest,
    beeline_rest: BeelineRestClient = Depends(get_beeline_rest_client)
):
    cf_list = [cf.dict() for cf in request.call_forward_list]
    data = beeline_rest.edit_call_forward(
        ctn=request.ctn,
        call_forward_list=cf_list,
        client=request.client
    )
    if data is None:
        raise HTTPException(status_code=502, detail="Beeline REST error /callForward edit")
    return {"status": "success", "requestId": data.get("requestId"), "data": data}

# --- SOAP Beeline (USS WSAPI) ---
class AddDelSoc(BaseModel):
    soc: str
    inclusion_type: str = None
    eff_date: str = None
    exp_date: str = None

@app.post("/service/{ctn}", summary="Подключение/отключение услуги (addDelSOC). add=True — подключить, False — отключить.", tags=["SOAP Beeline"])
async def add_del_soc_app(
    request: AddDelSoc,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.add_del_soc(
        ctn,
        request.soc,
        request.inclusion_type,
        request.eff_date,
        request.exp_date
    )
    if not data:
        raise HTTPException(status_code=502, detail="Failed to manage service in Beeline")
    return {"status": "success", "data": data}

class SuspendRestoreCTN(BaseModel):
    reason_code: str
    actv_date: str = None

@app.post("/block/{ctn}", summary="Добровольная блокировка номера (suspendCTN)", tags=["SOAP Beeline"])
async def suspend_ctn_app(
    request: SuspendRestoreCTN,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.suspend_ctn(
        ctn,
        request.reason_code,
        request.actv_date
    )
    if not data:
        raise HTTPException(status_code=502, detail="Failed to suspend CTN")
    return {"status": "success", "data": data}

@app.post("/unblock/{ctn}", summary="Снятие блокировки номера (restoreCTN)", tags=["SOAP Beeline"])
async def unblock_ctn_app(
    request: SuspendRestoreCTN,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.restore_ctn(
        ctn,
        request.reason_code,
        request.actv_date
    )
    if not data:
        raise HTTPException(status_code=502, detail="Failed to restore CTN")
    return {"status": "success", "data": data}

class ReplaceSim(BaseModel):
    serial_number: str

@app.post("/sim/replace/{ctn}", summary="Замена SIM-карты (replaceSIM)", tags=["SOAP Beeline"])
async def replace_sim_app(
    request: ReplaceSim,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.replace_sim(
        ctn,
        request.serial_number
    )
    if not data:
        raise HTTPException(status_code=502, detail="Failed to replace SIM")
    return {"status": "success", "data": data}

class Details(BaseModel):
    request_id: str

@app.post("/details/", summary="Получение файла детализации (в формате PDF). (get_details)", tags=["SOAP Beeline"])
async def get_details_app(
    request: Details,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_details(
        request.request_id
    )
    if not data:
        raise HTTPException(status_code=502, detail="Beeline SOAP error")
    return {"status": "success", "data": data}

class CTNInfoList(BaseModel):
    ban: str

@app.post("/subscriber/{ctn}", summary="Получения информации об абонентах на уровне BAN/CTN. (getCTNInfoList)", tags=["SOAP Beeline"])
async def get_ctn_info_list_app(
    request: CTNInfoList,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_ctn_info_list(
        ctn,
        ban=request.ban,
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to get subscriber info from Beeline")
    return {"status": "success", "data": data}

class CTNInfoListPaged(CTNInfoList):
    page: int = None
    records_per_page: str = None

@app.post("/subscriber/page/{ctn}", summary="Получения информации об абонентах на уровне BAN/CTN. (getCTNInfoListPaged)", tags=["SOAP Beeline"])
async def get_ctn_info_list_page_app(
    request: CTNInfoListPaged,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_ctn_info_list_paged(
        ctn,
        ban=request.ban,
        page=request.page,
        records_per_page=request.records_per_page
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to get subscriber info paged from Beeline")
    return {"status": "success", "data": data}

class ChangePP(BaseModel):
    price_plan: str
    future_date: str = None
    free_change: str = None

@app.post("/changePP/{ctn}", summary="Создание запроса на смену тарифного плана. (changePP)", tags=["SOAP Beeline"])
async def change_pp_app(
    request: ChangePP,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.change_pp(
        ctn,
        price_plan=request.price_plan,
        future_date=request.future_date,
        free_change=request.free_change
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to change pp from Beeline")
    return {"status": "success", "data": data}

class SIMList(BaseModel):
    ban: str

@app.post("/sim/list/{ctn}", summary="Получение номера SIM-карты/IMSI для BAN/CTN. (getSIMList)", tags=["SOAP Beeline"])
async def get_sim_list_app(
    request: SIMList,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_sim_list(
        ctn,
        ban=request.ban
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to sim list from Beeline")
    return {"status": "success", "data": data}

class SIMListPaged(SIMList):
    page: int = None
    records_per_page: str = None

@app.post("/sim/list/page/{ctn}", summary="Получение номера SIM-карты/IMSI для BAN/CTN. (getSIMListPaged)", tags=["SOAP Beeline"])
async def get_sim_list_paged_app(
    request: SIMListPaged,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_sim_list_paged(
        ctn,
        ban=request.ban,
        page=request.page,
        records_per_page=request.records_per_page
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to sim list paged from Beeline")
    return {"status": "success", "data": data}

class RequestList(BaseModel):
    page: int = None
    start_date: str = None
    end_date: str = None
    request_id: str = None
    records_per_page: str = None

@app.post("/request/page/", summary="Получение списка запросов со статусами по периоду, за который сделаны запросы или по номеру запроса. (getRequestList)", tags=["SOAP Beeline"])
async def get_request_list_app(
    request: RequestList,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_request_list(
        page=request.page,
        start_date=request.start_date,
        end_date=request.end_date,
        request_id=request.request_id,
        records_per_page=request.records_per_page
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to request list from Beeline")
    return {"status": "success", "data": data}

class ServicesList(BaseModel):
    ban: str

@app.post("/services/{ctn}", summary="Получения списка подключенных услуг на уровне BAN/CTN. (getServicesList)", tags=["SOAP Beeline"])
async def get_services_list_app(
    request: ServicesList,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_services_list(
        ctn,
        ban=request.ban
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to services list from Beeline")
    return {"status": "success", "data": data}

class ServicesListPaged(ServicesList):
    page: int = None
    ctn_amount_per_page: str = None

@app.post("/services/page/{ctn}", summary="Получения списка подключенных услуг на уровне BAN/CTN. (getServicesListPaged)", tags=["SOAP Beeline"])
async def get_services_list_paged_app(
    request: ServicesListPaged,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_services_list_paged(
        ctn,
        ban=request.ban,
        page=request.page,
        ctn_amount_per_page=request.ctn_amount_per_page
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to services list paged from Beeline")
    return {"status": "success", "data": data}

class PaymentList(BaseModel):
    ban: str
    start_date: str
    end_date: str

@app.post("/payment/{ctn}", summary="Получения информации о платежах BAN. (getPaymentList)", tags=["SOAP Beeline"])
async def get_payment_list_app(
    request: PaymentList,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_payment_list(
        ctn,
        ban=request.ban,
        start_date=request.start_date,
        end_date=request.end_date,
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to payment list from Beeline")
    return {"status": "success", "data": data}

class PaymentListPaged(PaymentList):
    page: int = None
    records_per_page: str = None

@app.post("/payment/page/{ctn}", summary="Получения информации о платежах BAN. (getPaymentListPaged)", tags=["SOAP Beeline"])
async def get_payment_list_paged_app(
    request: PaymentListPaged,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_payment_list_paged(
        ctn,
        ban=request.ban,
        start_date=request.start_date,
        end_date=request.end_date,
        page=request.page,
        records_per_page=request.records_per_page
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to payment list paged  from Beeline")
    return {"status": "success", "data": data}

@app.post("/unbilled/balance/{ctn}", summary="Возвращает сумму списания за текущий период абонента (постпейд). (getUnbilledBalancesRequest)", tags=["SOAP Beeline"])
async def get_unbilled_balance_app(
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)):
    data = beeline_soap.get_unbilled_balance(
        ctn=ctn
    )
    if not data:
        raise HTTPException(status_code=502, detail="Beeline SOAP error")
    return {"status": "success", "data": data}

@app.post("/unbilled/call/{ctn}", summary="Получения информации о необилленных звонках абонента (постпейд). (getUnbilledCallsList)", tags=["SOAP Beeline"])
async def get_unbilled_calls_app(
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_unbilled_calls_list(
        ctn,
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to unbilled calls list from Beeline")
    return {"status": "success", "data": data}

class AdjustmentList(BaseModel):
    ban: str
    start_date: str
    end_date: str

@app.post("/abjustment/", summary="Получения информации о корректировках BAN. (getAdjustmentList)", tags=["SOAP Beeline"])
async def get_adjustment_list_app(
    request: AdjustmentList,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_adjustment_list(
        ban=request.ban,
        start_date=request.start_date,
        end_date=request.end_date
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to adjustment list from Beeline")
    return {"status": "success", "data": data}

class GetBillCalls(BaseModel):
    request_id: str

@app.post("/bill/calls/", summary="Просмотр результата запроса отчета по детализации счета для списка CTN. (getBillCalls)", tags=["SOAP Beeline"])
async def get_bill_calls_app(
    request: GetBillCalls,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_bill_calls(
        request_id=request.request_id
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to get bill calls from Beeline")
    return {"status": "success", "data": data}

class GetBillCallsPaged(GetBillCalls):
    page: int = None
    records_per_page: str = None

@app.post("/bill/calls/page/", summary="Просмотр результата запроса отчета по детализации счета для списка CTN. (getBillCallsPaged)", tags=["SOAP Beeline"])
async def get_bill_calls_paged_app(
    request: GetBillCallsPaged,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_bill_calls_paged(
        request_id=request.request_id,
        page=request.page,
        records_per_page=request.records_per_page
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to get bill calls paged from Beeline")
    return {"status": "success", "data": data}

class GetBillCharges(BaseModel):
    request_id: str

@app.post("/bill/charges/", summary="Биллинг-начисления по номеру (getBillCharges)", tags=["SOAP Beeline"])
async def get_bill_charges_app(
    request: GetBillCharges,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_bill_charges(
        request_id=request.request_id
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to get bill charges from Beeline")
    return {"status": "success", "data": data}

class GetBillChargesPaged(GetBillCharges):
    page: int = None
    records_per_page: str = None

@app.post("/bill/charges/page/", summary="Биллинг-начисления с пагинацией (getBillChargesPaged)", tags=["SOAP Beeline"])
async def get_bill_charges_paged_app(
    request: GetBillChargesPaged,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_bill_charges_paged(
        request_id=request.request_id,
        page=request.page,
        records_per_page=request.records_per_page
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to get bill charges paged from Beeline")
    return {"status": "success", "data": data}

class SharedNumber(BaseModel):
    ctn_from: str
    ctn_to_list: str
    ctn_to: str
    soc: str = None
    prepaid_state_chk_cancel: str = None
    check_add_number_registration: str = None

@app.post("/sharednumber/dol/add", summary="Добавить номер в DOL shared list (addSharedNumberDOL)", tags=["SOAP Beeline"])
async def add_shared_number_dol_app(
    request: SharedNumber,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.add_shared_number_dol(
        ctn_from=request.ctn_from,
        ctn_to_list=request.ctn_to_list,
        ctn_to=request.ctn_to,
        soc=request.soc,
        prepaid_state_chk_cancel=request.prepaid_state_chk_cancel,
        check_add_number_registration=request.check_add_number_registration
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to add shared number to DOL")
    return {"status": "success", "data": data}

@app.post("/sharednumber/add", summary="Добавить номер в shared list (addSharedNumberListDOL)", tags=["SOAP Beeline"])
async def add_shared_number_list_app(
    request: SharedNumber,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.add_shared_number_list_dol(
        ctn_from=request.ctn_from,
        ctn_to_list=request.ctn_to_list,
        ctn_to=request.ctn_to,
        soc=request.soc,
        prepaid_state_chk_cancel=request.prepaid_state_chk_cancel,
        check_add_number_registration=request.check_add_number_registration
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to add shared number to DOL")
    return {"status": "success", "data": data}

@app.post("/sharednumber/delete", summary="Удалить номер из shared list (deleteSharedNumberListDOL)", tags=["SOAP Beeline"])
async def delete_shared_number_list_app(
    request: SharedNumber,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.delete_shared_number_list_dol(
        ctn_from=request.ctn_from,
        ctn_to_list=request.ctn_to_list,
        ctn_to=request.ctn_to
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to delete shared number from DOL")
    return {"status": "success", "data": data}

class PersonalDataUpdate(BaseModel):
    ctn: str
    first_name: str = None
    last_name: str = None
    birth_date: str = None
    # ... любые другие требуемые поля

@app.post("/personaldata/update", summary="Обновление персональных данных (personalDataUpdate)", tags=["SOAP Beeline"])
async def personal_data_update_app(
    request: PersonalDataUpdate,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.personal_data_update(
        **request.dict()
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to update personal data")
    return {"status": "success", "data": data}

class PersonalDataResultRequest(BaseModel):
    request_id: str

@app.post("/personaldata/result", summary="Получить результат операции обновления персональных данных (personalDataResult)", tags=["SOAP Beeline"])
async def personal_data_result_app(
    request: PersonalDataResultRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.personal_data_result(
        request_id=request.request_id
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to get personal data result")
    return {"status": "success", "data": data}

class GetDataReportRequest(BaseModel):
    ban: str
    report_type: str
    start_date: str = None
    end_date: str = None

@app.post("/data/report", summary="Получить отчёт данных (getDataReport)", tags=["SOAP Beeline"])
async def get_data_report_app(
    request: GetDataReportRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_data_report(
        ban=request.ban,
        report_type=request.report_type,
        start_date=request.start_date,
        end_date=request.end_date
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to get data report from Beeline")
    return {"status": "success", "data": data}

class GetBANInfoListRequest(BaseModel):
    ban: str

@app.post("/ban/list", summary="Список лицевых счетов (getBANInfoList)", tags=["SOAP Beeline"])
async def get_ban_info_list_app(
    request: GetBANInfoListRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_ban_info_list(
        ban=request.ban
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to get BAN info list from Beeline")
    return {"status": "success", "data": data}

class GetBANInfoListPagedRequest(GetBANInfoListRequest):
    page: int = None
    records_per_page: int = None

@app.post("/ban/list/paged", summary="Список лицевых счетов с пагинацией (getBANInfoListPaged)", tags=["SOAP Beeline"])
async def get_ban_info_list_paged_app(
    request: GetBANInfoListPagedRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_ban_info_list_paged(
        ban=request.ban,
        page=request.page,
        records_per_page=request.records_per_page
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to get BAN info paged from Beeline")
    return {"status": "success", "data": data}

class CreateBillCallsRequest(BaseModel):
    ban: str
    ctn: str
    start_date: str
    end_date: str

@app.post("/bill/calls/request", summary="Создать запрос детализации звонков (createBillCallsRequest)", tags=["SOAP Beeline"])
async def create_bill_calls_request_app(
    request: CreateBillCallsRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.create_bill_calls_request(
        ban=request.ban,
        ctn=request.ctn,
        start_date=request.start_date,
        end_date=request.end_date
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to create bill calls request")
    return {"status": "success", "data": data}

class CreateBillChargesRequest(BaseModel):
    ban: str
    ctn: str
    start_date: str
    end_date: str

@app.post("/bill/charges/request", summary="Создать запрос детализации начислений (createBillChargesRequest)", tags=["SOAP Beeline"])
async def create_bill_charges_request_app(
    request: CreateBillChargesRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.create_bill_charges_request(
        ban=request.ban,
        ctn=request.ctn,
        start_date=request.start_date,
        end_date=request.end_date
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to create bill charges request")
    return {"status": "success", "data": data}

class CreateDetailsRequest(BaseModel):
    ban: str
    ctn: str
    detail_type: str
    period_from: str
    period_to: str

@app.post("/details/request", summary="Создать запрос на детализацию (createDetailsRequest)", tags=["SOAP Beeline"])
async def create_details_request_app(
    request: CreateDetailsRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.create_details_request(
        ban=request.ban,
        ctn=request.ctn,
        detail_type=request.detail_type,
        period_from=request.period_from,
        period_to=request.period_to,
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to create details request")
    return {"status": "success", "data": data}

class GetDataRequest(BaseModel):
    ban: str
    data_type: str
    date: str = None

@app.post("/data", summary="Получить данные (getData)", tags=["SOAP Beeline"])
async def get_data_app(
    request: GetDataRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_data(
        ban=request.ban,
        data_type=request.data_type,
        date=request.date
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to get data")
    return {"status": "success", "data": data}

# --- API HANDLERS ---
@app.post("/sync/payments", summary="Синхронизация платежей")
async def sync_payments(
    request: PaymentSyncRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client),
    utm5_rest_client: UTM5RestClient = Depends(get_utm5_rest_client)
):
    payments = beeline_soap.get_payment_list_paged(
        ctn=request.ctn,
        ban=request.ban,
        start_date=request.start_date,
        end_date=request.end_date,
        page=request.page,
        records_per_page=request.records_per_page
    )
    if not payments:
        raise HTTPException(status_code=400, detail="Failed to get payments from BeeLine")

    utm5_user = utm5_rest_client.search_user_by_query(
        request.ctn
    )
    if not utm5_user:
        raise HTTPException(status_code=404, detail="User not found in UTM5")
    user_id = None
    if isinstance(utm5_user, list) and len(utm5_user) > 0:
        user_id = utm5_user[0].get('id') or utm5_user[0].get('user_id')
    elif isinstance(utm5_user, dict):
        user_id = utm5_user.get('id') or utm5_user.get('user_id')
    if not user_id:
        logger.error(f"Не удалось извлечь user_id из ответа UTM5: {utm5_user}")
        raise HTTPException(status_code=500, detail="Invalid UTM5 user data structure")

    # payments всегда список
    payments_list = payments if isinstance(payments, list) else [payments]
    total_amount = 0.0
    payment_count = 0
    for p in payments_list:
        amount = p.get('amount') if isinstance(p, dict) else getattr(p, 'amount', 0)
        try:
            total_amount += float(amount or 0)
            payment_count += 1
        except (ValueError, TypeError):
            logger.warning(f"Некорректное значение суммы платежа: {amount}")

    result = utm5_rest_client.pay_user(user_id, total_amount)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update balance in UTM5")

    return {
        "status": "success",
        "payments_synced": payment_count,
        "total_amount": total_amount,
        "utm5_user_id": user_id,
        "utm5_update": result
    }

@app.post("/tariff/change", summary="Смена тарифа: Beeline -> UTM5")
async def change_tariff_endpoint(
    request: TariffChangeRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client),
    utm5_rest_client: UTM5RestClient = Depends(get_utm5_rest_client)
):
    beeline_result = beeline_soap.change_pp(
        ctn=request.ctn,
        price_plan=request.price_plan,
        future_date=request.future_date,
        free_change=request.free_change
    )
    if not beeline_result:
        raise HTTPException(status_code=400, detail="Failed to change tariff in BeeLine")

    utm5_tariff_id = TARIFF_MAPPING.get(
        request.price_plan
    )
    if not utm5_tariff_id:
        logger.error(f"Tarrif mapping not found: {request.price_plan}")
        raise HTTPException(status_code=400, detail=f"Tarrif mapping not found for code: {request.price_plan}")

    utm5_result = utm5_rest_client.set_user_tariff(request.utm5_user_id, utm5_tariff_id)
    if not utm5_result:
        raise HTTPException(status_code=500, detail="Failed to change tariff in UTM5")
    return {
        "status": "success",
        "ctn": request.ctn,
        "beeline_tariff_code": request.price_plan,
        "utm5_tariff_id": utm5_tariff_id,
        "beeline_result": beeline_result,
        "utm5_result": utm5_result
    }

tags_metadata = [
    {
        "name": "REST Beeline",
        "description": "Методы интеграции по REST API Beeline (USSS)",
    },
    {
        "name": "SOAP Beeline",
        "description": "Методы интеграции по SOAP API Beeline (WSAPI)",
    },
    {
        "name": "UTM5",
        "description": "Методы интеграции с UTM5",
    }
]