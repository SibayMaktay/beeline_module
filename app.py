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

class AddDelSoc(BaseModel):
    soc: str
    inclusion_type: str = None
    eff_date: str = None
    exp_date: str = None

class SuspendRestoreCTN(BaseModel):
    reason_code: str
    actv_date: str = None

class ReplaceSim(BaseModel):
    serial_number: str

class Details(BaseModel):
    request_id: str

class CTNInfoListPaged(BaseModel):
    ban: str
    page: int = None
    records_per_page: str = None

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
@app.get("/balance/{ctn}", summary="Небиллингованный баланс лицевого счёта (SOAP)", tags=["SOAP Beeline"])
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

@app.post("/details/", summary="Создание запроса на подключение/отключение услуги (get_details)", tags=["SOAP Beeline"])
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

@app.post("/subscriber/{ctn}", summary="Получения информации об абонентах на уровне BAN/CTN.", tags=["SOAP Beeline"])
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
        raise HTTPException(status_code=404, detail="Failed to get subscriber info from Beeline")
    return {"status": "success", "data": data}

@app.post("/subscriber/{ctn}", summary="Получения информации об абонентах на уровне BAN/CTN.", tags=["SOAP Beeline"])
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
        raise HTTPException(status_code=404, detail="Failed to get subscriber info from Beeline")
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