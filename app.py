import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any, List, Dict
import config.config as config

from client.beeline_soap_client import BeelineSoapClient
from client.beeline_rest_client import BeelineRestClient
from token_api.token_beeline import get_beeline_token, invalidate_token
from routers.utm5_router import router as utm5_router
from dependencies_utm5 import shutdown_utm5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Зависимости и DI-фабрики ---
def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != config.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key

def get_beeline_rest_client():
    token = get_beeline_token()
    client = BeelineRestClient(
        base_url=config.beeline_url_base,
        signature=config.beeline_rest_signature
    )
    client.set_token(token)
    return client

def get_beeline_soap_client():
    return BeelineSoapClient(
        token_provider=get_beeline_token()
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Старт интеграции...")
    try:
        get_beeline_token()
    except Exception as e:
        logger.warning(f"Beeline аутентификация не удалась на старте: {e}")
    yield
    shutdown_utm5()
    logger.info("Завершение работы интеграционной службы...")

app = FastAPI(title="BeeLine-UTM5 Integration Module", version="1.0.0", lifespan=lifespan)
app.include_router(utm5_router)

BRIDGE_API_KEY = config.module_api_key

@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    """
    Проверяет API ключ во всех запросах к мосту.
    """
    if request.url.path in ["/docs", "/redoc", "/openapi.json", "/utm5/health"]:
        return await call_next(request)
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != BRIDGE_API_KEY:
        return JSONResponse(
            status_code=403,
            content={"detail": "Invalid or missing X-API-Key header"}
        )
    return await call_next(request)

# ============================================================================
# REST Beeline (USSS)
# ============================================================================
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

@app.get("/callforward/get/{ctn}", summary="Получить параметры переадресации (объединённый запрос: шаг 1+2)", tags=["REST Beeline"])
async def get_call_forward_combined(
    ctn: str,
    client: Optional[str] = None,
    beeline_rest: BeelineRestClient = Depends(get_beeline_rest_client)
) -> Dict[str, Any]:
    """
    ОБЪЕДИНЁННЫЙ эндпоинт для получения параметров переадресации.
    
    Вместо двух последовательных запросов:
      1. GET /callforward/request/{ctn}
      2. GET /callforward/info/{requestId}
    
    Теперь один запрос:
      GET /callforward/get/{ctn}?client=...
    
    Параметры:
      - ctn: номер абонента (обязательный, строка)
      - client: код клиента (опционально)
      - X-API-Key: API ключ (передаётся в middleware)
    
    Возвращает:
      {
        "status": "success",
        "request_id": 12345,                    # ID запроса для edit_call_forward
        "call_forward_list": [...],             # Список переадресаций
        "call_forward_ext": "79001234567",      # Номер переадресации
        "cf_type": "FORWARDING",                # Тип переадресации
        "raw_response": {...}                   # Полный ответ Beeline (для отладки)
      }
    
    Ошибки:
      - 403: Invalid API key (в middleware)
      - 502: Beeline REST error
    
    Примеры:
      # cURL
      curl -X GET "http://127.0.0.1:9090/callforward/get/79051234567?client=myapp" \\
        -H "X-API-Key: bee_test"
      
      # Python
      import requests
      response = requests.get(
          "http://127.0.0.1:9090/callforward/get/79051234567",
          params={"client": "myapp"},
          headers={"X-API-Key": "bee_test"}
      )
      data = response.json()
      request_id = data["request_id"]
    """
    logger.info(f"CallForward: получение параметров для CTN {ctn}, client={client}")
    logger.debug(f"Шаг 1: создание запроса (request_call_forward)")
    request_response = beeline_rest.request_call_forward(ctn=ctn,client=client)
    if request_response is None:
        logger.error(f"CallForward: ошибка создания запроса для CTN {ctn}")
        raise HTTPException(
            status_code=502,
            detail="Beeline REST error: failed to create call forward request"
        )
    request_id = request_response.get("requestId")
    if not request_id:
        logger.error(f"CallForward: requestId отсутствует в ответе Beeline")
        raise HTTPException(
            status_code=502,
            detail="Beeline REST error: no requestId in response"
        )
    logger.debug(f"Получен requestId: {request_id}")
    logger.debug(f"Шаг 2: получение параметров (get_call_forward_by_request)")
    info_response = beeline_rest.get_call_forward_by_request(request_id=request_id,client=client)
    if info_response is None:
        logger.error(f"CallForward: ошибка получения параметров для requestId {request_id}")
        raise HTTPException(
            status_code=502,
            detail="Beeline REST error: failed to get call forward info"
        )
    logger.debug(f"Получены параметры переадресации")

    call_forward_list = (
        info_response.get("callForwardList") or
        info_response.get("CallForwardListDO") or
        info_response.get("call_forward_list") or
        []
    )
    call_forward_ext = (
        info_response.get("callForwardExt") or
        info_response.get("CallForwardExtDO") or
        info_response.get("call_forward_ext") or
        ""
    )
    cf_type = (
        info_response.get("cfType") or
        info_response.get("cf_type") or
        ""
    )
    logger.info(f"CallForward: успешно получены параметры для CTN {ctn}")
    return {
        "status": "success",
        "request_id": request_id,
        "call_forward_list": call_forward_list,
        "call_forward_ext": call_forward_ext,
        "cf_type": cf_type,
        "raw_response": info_response
    }

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

class PutCallForwardRequestEdit(BaseModel):
    ctn: str
    call_forward_edit_request: list
    call_forward: list
    cf_type: str = None
    cf_ctn: str = None
    client: Optional[str] = None

@app.get("/callforward/edit", summary="Установка параметров переадресации (REST, шаг 3)", tags=["REST Beeline"])
async def edit_call_forward_app(
    request: PutCallForwardRequestEdit,
    beeline_rest: BeelineRestClient = Depends(get_beeline_rest_client)
):
    data = beeline_rest.edit_call_forward(
        ctn=request.ctn,
        call_forward_edit_request=request.call_forward_edit_request,
        call_forward=request.call_forwarsd,
        cf_type=request.cf_type,
        cf_ctn=request.cf_ctn,
        client=request.client
    )
    if data is None:
        raise HTTPException(status_code=502, detail="Beeline REST error /callForward edit")
    return {"status": "success", "requestId": data.get("requestId"), "data": data}

# ============================================================================
# SOAP Beeline (USS WSAPI)
# ============================================================================
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
    ctn_to: str

class SharedNumberDOL(SharedNumber):
    ctn_type: str = None
    soc: str = None
    prepaid_state_chk_cancel: str = None
    check_add_number_registration: str = None

@app.post("/sharednumber/dol/add", summary="Добавить номер в DOL shared list (addSharedNumberDOL)", tags=["SOAP Beeline"])
async def add_shared_number_dol_app(
    request: SharedNumberDOL,
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

class SharedNumberListDOL(SharedNumber):
    ctn_to_list: str = None
    soc: str = None
    prepaid_state_chk_cancel: str = None
    check_add_number_registration: str = None

@app.post("/sharednumber/add", summary="Добавить номер в shared list (addSharedNumberListDOL)", tags=["SOAP Beeline"])
async def add_shared_number_list_app(
    request: SharedNumberListDOL,
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

class SharedNumberDeleteDOL(SharedNumber):
    ctn_to_list: str = None

@app.post("/sharednumber/delete", summary="Удалить номер из shared list (deleteSharedNumberListDOL)", tags=["SOAP Beeline"])
async def delete_shared_number_list_app(
    request: SharedNumberDeleteDOL,
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
    ban: str = None
    statusBan: str = None
    ctn: str = None
    marketCode: str = None
    docName: str = None
    changeDate: str = None
    startServiceDate: str = None
    confDate: str = None
    statusPdn: str = None
    blockDate: str = None
    accessClientPdn: str = None
    introPdn: str = None
    citizenship: str = None
    docNo: str = None
    docType: str = None
    docIssueDate: str = None
    docIssuer: str = None
    docIssuerCode: str = None
    docExpirationDate: str = None
    birthdate: str = None
    frnMigcard: str = None
    frnMigcardEffDate: str = None
    frnMigcardExpDate: str = None
    frnDoc: str = None
    firstName: str = None
    lastName: str = None
    surName: str = None
    birthplace: str = None
    gender: str = None
    taxNumber: str = None
    snils: str = None
    legalPostcode: str = None
    legalCountryCode: str = None
    legalRegion: str = None
    legalArea: str = None
    legalPlaceType: str = None
    legalPlace: str = None
    legalStreetType: str = None
    legalStreetName: str = None
    legalHouseNo: str = None
    legalBuildingType: str = None
    legalBuildingNo: str = None
    legalApartmentType: str = None
    legalApartmentNo: str = None
    legalAddrComment: str = None
    legalFiasId: str = None
    actualPostcode: str = None
    actualCountryCode: str = None
    actualRegion: str = None
    actualArea: str = None
    actualPlaceType: str = None
    actualPlace: str = None
    actualStreetType: str = None
    actualStreetName: str = None
    actualHouseNo: str = None
    actualBuildingType: str = None
    actualBuildingNo: str = None
    actualApartmentType: str = None
    actualApartmentNo: str = None
    actualAddrComment: str = None
    actualFiasId: str = None

@app.post("/personaldata/update", summary="Обновление персональных данных (personalDataUpdate)", tags=["SOAP Beeline"])
async def personal_data_update_app(
    request: PersonalDataUpdate,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data_dict = {k: v for k, v in request.dict().items() if v is not None}
    data = beeline_soap.personal_data_update(
        data=data_dict
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
    request_id: str
    page: int = None
    records_per_page: str = None

@app.post("/data/report", summary="Получить отчёт данных (getDataReport)", tags=["SOAP Beeline"])
async def get_data_report_app(
    request: GetDataReportRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_data_report(
        request_id=request.request_id,
        page=request.page,
        records_per_page=request.records_per_page
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to get data report from Beeline")
    return {"status": "success", "data": data}

@app.post("/ban/list", summary="Список лицевых счетов (getBANInfoList)", tags=["SOAP Beeline"])
async def get_ban_info_list_app(
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_ban_info_list()
    if not data:
        raise HTTPException(status_code=404, detail="Failed to get BAN info list from Beeline")
    return {"status": "success", "data": data}

class GetBANInfoListPagedRequest(BaseModel):
    page: int = None
    records_per_page: int = None

@app.post("/ban/list/paged", summary="Список лицевых счетов с пагинацией (getBANInfoListPaged)", tags=["SOAP Beeline"])
async def get_ban_info_list_paged_app(
    request: GetBANInfoListPagedRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_ban_info_list_paged(
        page=request.page,
        records_per_page=request.records_per_page
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to get BAN info paged from Beeline")
    return {"status": "success", "data": data}

class CreateBillRequest(BaseModel):
    ban: str
    bill_date: str
    ctn_list: str = None

@app.post("/bill/calls/request", summary="Создать запрос детализации звонков (createBillCallsRequest)", tags=["SOAP Beeline"])
async def create_bill_calls_request_app(
    request: CreateBillRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.create_bill_calls_request(
        ban=request.ban,
        bill_date=request.bill_date,
        ctn_list=request.ctn_list
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to create bill calls request")
    return {"status": "success", "data": data}

@app.post("/bill/charges/request", summary="Создать запрос детализации начислений (createBillChargesRequest)", tags=["SOAP Beeline"])
async def create_bill_charges_request_app(
    request: CreateBillRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.create_bill_charges_request(
        ban=request.ban,
        bill_date=request.bill_date,
        ctn_list=request.ctn_list
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to create bill charges request")
    return {"status": "success", "data": data}

class CreateDetailsRequest(BaseModel):
    period_start: str
    period_end: str
    format_: str
    channel: str
    email: str

@app.post("/details/request/{ctn}", summary="Создать запрос на детализацию (createDetailsRequest)", tags=["SOAP Beeline"])
async def create_details_request_app(
    request: CreateDetailsRequest,
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.create_details_request(
        ctn=ctn,
        period_start=request.period_start,
        period_end=request.period_end,
        format_=request.format_,
        channel=request.channel,
        email=request.email,
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to create details request")
    return {"status": "success", "data": data}

class GetDataRequest(BaseModel):
    ban: str
    hierarchy_id: str
    subscriber_no: str

@app.post("/data", summary="Получить данные (getData)", tags=["SOAP Beeline"])
async def get_data_app(
    request: GetDataRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.get_data(
        ban=request.ban,
        hierarchy_id=request.hierarchy_id,
        subscriber_no=request.subscriber_no
    )
    if not data:
        raise HTTPException(status_code=404, detail="Failed to get data")
    return {"status": "success", "data": data}

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