import config
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, Any, Dict, List

from beeline_soap_client import get_subscriber_info, get_payments, change_tariff, get_unbilled_balances, manage_service, suspend_ctn, restore_ctn, replace_sim
from beeline_rest_client import BeelineRestClient
from utm5_client import UTM5Client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Модели данных
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

# Глобальные экземпляры клиентов
beeline_soap_get_subscriber_info: Optional[get_subscriber_info] = None
beeline_rest: Optional[BeelineRestClient] = None
utm5_client: Optional[UTM5Client] = None

TARIFF_MAPPING = {
    "BEELINE_TARIFF_1": "EXCLH11",
    "BEELINE_TARIFF_2": "EXCLH12",
    "BEELINE_TARIFF_3": "EXCLH13",
}

def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != config.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Инициализация клиентов интеграции...")

    beeline_rest = BeelineRestClient(
        base_url=config.beeline_url_base,
        signature=config.beeline_rest_signature
    )
    
    utm5_client = UTM5Client(
        base_url=config.utm5_api_url,
        login=config.utm5_login,
        password=config.utm5_password
    )
    
    # Автоматическая аутентификация при старте
    if not utm5_client.authenticate():
        logger.warning("Не удалось аутентифицироваться в UTM5 при запуске.")
    
    # Для Beeline аутентификация часто делается по запросу, 
    # но можно раскомментировать строку ниже, если нужен глобальный логин при старте:
    # beeline_client.authenticate(config.beeline_login, config.beeline_password)
    # beeline_rest.authenticate(config.beeline_login, config.beeline_password)

    yield

    logger.info("Завершение работы модуля интеграции...")
    if utm5_client and hasattr(utm5_client, 'session'):
        utm5_client.session.close()

app = FastAPI(
    title="BeeLine-UTM5 Integration Module",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/subscriber/{phone_number}", summary="Получение информации об абоненте")
async def get_subscriber(phone_number: str, api_key: str = Depends (verify_api_key)):
    """
    Получение информации об абоненте из BeeLine
    """
    info = get_subscriber_info(phone_number)
    if not info:
        raise HTTPException(status_code=404, detail="Failed to get subscriber info from Beeline")
    return {"status": "success", "data": info}

@app.post("/sync/payments", summary="Синхронизация платежей из BeeLine в UTM5")
async def sync_payments(request: PaymentSyncRequest, api_key: str = Depends(verify_api_key)):
    """
    Синхринизация платежей из BeeLine в UTM5
    """
    # 1. Получаем платежи из Beeline
    payments = get_payments(
        request.account_id,
        request.start_date,
        request.end_date
    )
    if not payments:
        raise HTTPException(status_code=400, detail="Failed to get payments from BeeLine")

    # 2. Находим абонента в UTM5 по номеру телефона
    utm5_user = utm5_client.get_user_by_phone(request.phone_number)
    if not utm5_user:
        raise HTTPException(status_code=404, detail="User not found in UTM5")

    # 3. БЕЗОПАСНОЕ извлечение ID пользователя (защита от разных форматов ответа)
    user_id = None
    if isinstance(utm5_user, list) and len(utm5_user) > 0:
        user_id = utm5_user[0].get('id') or utm5_user[0].get('user_id')
    elif isinstance(utm5_user, dict):
        user_id = utm5_user.get('id') or utm5_user.get('user_id')

    if not user_id:
        logger.error(f"Не удалось извлечь user_id из ответа UTM5: {utm5_user}")
        raise HTTPException(status_code=500, detail="Invalid UTM5 user data structure")

    # 4. БЕЗОПАСНЫЙ подсчет суммы платежей (защита от Dict/Object различий Zeep/Requests)
    total_amount = 0.0
    payment_count = 0

    # Приводим к списку, если ответ пришел в другом формате
    payments_list = payments if isinstance(payments, list) else [payments]

    for p in payments_list:
        # Пытаемся получить amount как из словаря, так и из объекта (на случай ответа Zeep)
        amount = p.get('amount') if isinstance(p, dict) else getattr(p, 'amount', 0)
        try:
            total_amount += float(amount or 0)
            payment_count += 1
        except(ValueError,TypeError):
            logger.warning(f"Некоректное значение суммы платежа: {amount}")

    # 5. Обновляем баланс в UTM5
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
async def change_tariff_endpoint(request: TariffChangeRequest, api_key: str = Depends(verify_api_key)):
    """
    Смена тарифа: BeeLine -> UTM5
    """
    # 1. Меняем тариф в Beeline
    beeline_result = change_tariff(
        request.phone_number,
        request.new_tariff_code
    )
    if not beeline_result:
        raise HTTPException(status_code=400, detail="Failed to change tariff in BeeLine")

    # 2. Маппинг тарифов (критически важно для интеграции разных систем)
    utm5_tariff_id = TARIFF_MAPPING.get(request.new_tariff_code)
    if not utm5_tariff_id:
        logger.error(f"Не найден маппинг для тарифа: {request.new_tariff_code}")
        raise HTTPException(
            status_code=400,
            detail=f"Tariff mapping not found for code: {request.new_tariff_code}"
        )

    # 3. Меняем тариф в UTM5
    utm5_result = utm5_client.change_user_tariff(
        request.utm5_user_id,
        utm5_tariff_id
    )
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

# ---------- REST BeeLine (USSS) ----------

@app.get("/rests/{ctn}", summary="Остатки пакетов абонента (REST)")
async def get_rests(ctn:str):
    """
    Остатки пакетов абонента (REST)
    """
    data = beeline_rest.get_rests(ctn)
    if data is None:
        raise HTTPException(status_code=502, detail="Beeline REST error")
    return {
        "status": "success",
        "data": data
    }

@app.get("/subscriptions/{ctn}", summary="Активные подписки абонента (REST)")
async def get_subscriptions(ctn: str):
    """
    Активные подписки абонента (REST)
    """
    data = beeline_rest.get_subscriptions(ctn)
    if data is None:
        raise HTTPException(status_code=502, detail="Beeline REST error")
    return {
        "status": "success",
        "data": data
    }

@app.get("/callforward/{ctn}", summary="Параметры переадресации (REST)")
async def get_call_forward(ctn: str):
    """
    Параметры переадресации (REST)
    """
    data = beeline_rest.get_call_forward(ctn)
    if data is None:
        raise HTTPException(status_code=502,detail="Beeline REST error")
    return {
        "status": "success",
        "data": data
    }

# ---------- SOAP Beeline (USS WSAPI) ----------

@app.get("/balance/{account_id}", summary="Небиллингованный баланс лицевого счёта (SOAP)")
async def get_balance(account_id: str, api_key: str = Depends (verify_api_key)):
    """
    Небиллингованный баланс лицевого счёта (SOAP)
    """
    data = get_unbilled_balances(account_id)
    if not data:
        raise HTTPException(status_code=502,detail="Beeline SOAP error")
    return {
        "status": "success",
        "data": data
    }

@app.post("/service", summary="Подключение/отключение услуги (addDelSOC)")
async def manage_service_1(request: ServiceRequest, api_key: str = Depends (verify_api_key)):
    """
    Подключение/отключение услуги (addDelSOC)
    """
    data = manage_service(request.phone_number, request.soc_code, request.add)
    if not data:
        raise HTTPException(status_code=502,detail="Failed to manage service in Beeline")
    return {
        "status": "success",
        "action": "ADD" if request.add else "DEL",
        "data": data
    }

@app.post("/block/{ctn}", summary="Добровольная блокировка номера (suspendCTN)")
async def block_ctn(ctn: str, api_key: str = Depends(verify_api_key)):
    """
    Добровольная блокировка номера (suspendCTN)
    """
    data = suspend_ctn(ctn)
    if not data:
        raise HTTPException(status_code=502,detail="Failed to suspend CTN")
    return {
        "status": "success",
        "data": data
    }

@app.post("/unblock/{ctn}", summary="Снятие блокировки номера (restoreCTN)")
async def unblock_ctn(ctn: str, api_key: str = Depends(verify_api_key)):
    """
    Снятие блокировки номера (restoreCTN)
    """
    data = restore_ctn(ctn)
    if not data:
        raise HTTPException(status_code=502,detail="Failed to restore CTN")
    return {
        "status": "success",
        "data": data
    }

@app.post("/sim/replace", summary="Замена SIM-карты (replaceSIM)")
async def replace_sim_1(ctn: str, new_sim: str, api_key: str = Depends(verify_api_key)):
    """
    Замена SIM-карты (replaceSIM)
    """
    data = replace_sim(ctn, new_sim)
    if not data:
        raise HTTPException(status_code=502,detail="Failed to replace SIM")
    return {
        "status": "success",
        "data": data
    }

@app.get("/health", summary="Проверка работоспособности модуля")
async def health_check():
    """
    Проверка работоспособности модуля
    """
    is_utm5_ready = utm5_client is not None and utm5_client.session_id is not None
    # is_beeline_ready = token_beeline is not None and beeline.session_id is not None

    return {
        "status": "healthy",
        "service": "beeline-utm5-integration",
        "utm5_authenticated": is_utm5_ready,
        # "beeline_authenticated": is_beeline_ready
    }