import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, Any
import config.config as config

from client.beeline_soap_client import BeelineSoapClient
from client.beeline_rest_client import BeelineRestClient
from client.utm5_client import UTM5Client
from token_api.token_beeline import get_beeline_token, invalidate_token
from token_api.token_utm5 import get_utm5_token

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Модели данных ---
class PaymentSyncRequest(BaseModel):
    phone_number: str
    account_id: str
    start_date: str
    end_date: str

class TariffChangeRequest(BaseModel):
    phone_number: str
    new_tariff_code: str
    utm5_user_id: int

class ServiceRequest(BaseModel):
    phone_number: str
    soc_code: str
    add: bool = True

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

def get_utm5_client():
    return UTM5Client(
        base_url=config.utm5_api_url,
        session_id_provider=get_utm5_token
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

# --- API HANDLERS ---

@app.get("/subscriber/{phone_number}", summary="Получить информацию об абоненте")
async def get_subscriber(
    phone_number: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    # ban = beeline_soap.get_ban_info_list()
    info = beeline_soap.get_ctn_info_list(ban=phone_number)
    if not info:
        raise HTTPException(status_code=404, detail="Failed to get subscriber info from Beeline")
    return {"status": "success", "data": info}

@app.post("/sync/payments", summary="Синхронизация платежей")
async def sync_payments(
    request: PaymentSyncRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client),
    utm5_client: UTM5Client = Depends(get_utm5_client)
):
    payments = beeline_soap.get_payment_list(ban=request.account_id, start_date=request.start_date, end_date=request.end_date)
    if not payments:
        raise HTTPException(status_code=400, detail="Failed to get payments from BeeLine")

    utm5_user = utm5_client.get_user_by_phone(request.phone_number)
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

    result = utm5_client.update_user_balance(user_id, total_amount)
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
    utm5_client: UTM5Client = Depends(get_utm5_client)
):
    beeline_result = beeline_soap.change_pp(request.phone_number, request.new_tariff_code)
    if not beeline_result:
        raise HTTPException(status_code=400, detail="Failed to change tariff in BeeLine")

    utm5_tariff_id = TARIFF_MAPPING.get(request.new_tariff_code)
    if not utm5_tariff_id:
        logger.error(f"Tarrif mapping not found: {request.new_tariff_code}")
        raise HTTPException(status_code=400, detail=f"Tarrif mapping not found for code: {request.new_tariff_code}")

    utm5_result = utm5_client.change_user_tariff(request.utm5_user_id, utm5_tariff_id)
    if not utm5_result:
        raise HTTPException(status_code=500, detail="Failed to change tariff in UTM5")
    return {
        "status": "success",
        "phone_number": request.phone_number,
        "beeline_tariff_code": request.new_tariff_code,
        "utm5_tariff_id": utm5_tariff_id,
        "beeline_result": beeline_result,
        "utm5_result": utm5_result
    }

# --- REST Beeline (USSS) ---
@app.get("/rests/{ctn}", summary="Остатки пакетов абонента (REST)")
async def get_rests(ctn: str, beeline_rest: BeelineRestClient = Depends(get_beeline_rest_client)):
    data = beeline_rest.get_rests(ctn)
    if data is None:
        raise HTTPException(status_code=502, detail="Beeline REST error")
    return {"status": "success", "data": data}

@app.get("/subscriptions/{ctn}", summary="Активные подписки абонента (REST)")
async def get_subscriptions(ctn: str, beeline_rest: BeelineRestClient = Depends(get_beeline_rest_client)):
    data = beeline_rest.get_subscriptions(ctn)
    if data is None:
        raise HTTPException(status_code=502, detail="Beeline REST error")
    return {"status": "success", "data": data}

@app.get("/callforward/{ctn}", summary="Параметры переадресации (REST)")
async def get_call_forward(ctn: str, beeline_rest: BeelineRestClient = Depends(get_beeline_rest_client)):
    data = beeline_rest.get_call_forward(ctn)
    if data is None:
        raise HTTPException(status_code=502, detail="Beeline REST error")
    return {"status": "success", "data": data}

# --- SOAP Beeline (USS WSAPI) ---
@app.get("/balance/{account_id}", summary="Небиллингованный баланс лицевого счёта (SOAP)")
async def get_balance(account_id: str, api_key: str = Depends(verify_api_key), beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)):
    data = beeline_soap.get_unbilled_balance(account_id)
    if not data:
        raise HTTPException(status_code=502, detail="Beeline SOAP error")
    return {"status": "success", "data": data}

@app.post("/service", summary="Подключение/отключение услуги (addDelSOC)")
async def manage_service_1(
    request: ServiceRequest,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.add_del_soc(request.phone_number, request.soc_code, "add" if request.add else "del")
    if not data:
        raise HTTPException(status_code=502, detail="Failed to manage service in Beeline")
    return {"status": "success", "action": "ADD" if request.add else "DEL", "data": data}

@app.post("/block/{ctn}", summary="Добровольная блокировка номера (suspendCTN)")
async def block_ctn(
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.suspend_ctn(ctn)
    if not data:
        raise HTTPException(status_code=502, detail="Failed to suspend CTN")
    return {"status": "success", "data": data}

@app.post("/unblock/{ctn}", summary="Снятие блокировки номера (restoreCTN)")
async def unblock_ctn(
    ctn: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.restore_ctn(ctn)
    if not data:
        raise HTTPException(status_code=502, detail="Failed to restore CTN")
    return {"status": "success", "data": data}

@app.post("/sim/replace", summary="Замена SIM-карты (replaceSIM)")
async def replace_sim_1(
    ctn: str, 
    new_sim: str,
    api_key: str = Depends(verify_api_key),
    beeline_soap: BeelineSoapClient = Depends(get_beeline_soap_client)
):
    data = beeline_soap.replace_sim(ctn, new_sim)
    if not data:
        raise HTTPException(status_code=502, detail="Failed to replace SIM")
    return {"status": "success", "data": data}

@app.get("/health", summary="Проверка работоспособности модуля")
async def health_check(
    utm5_client: UTM5Client = Depends(get_utm5_client)
):
    is_utm5_ready = utm5_client is not None and hasattr(utm5_client, "session_id") and utm5_client.session_id is not None
    return {
        "status": "healthy",
        "service": "beeline-utm5-integration",
        "utm5_authenticated": is_utm5_ready,
    }