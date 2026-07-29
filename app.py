from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging
from beeline_client import BeelineClient
from utm5_client import UTM5Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BeeLine-UTM5 Integration Module")

# Инициализация клиентов
beeline_client = BeelineClient(
    auth_url="https://my.beeline.ru/api/AuthService",
    subsciber_url="https://my.beeline.ru/api/SubscriberService"
)

utm5_client = UTM5Client(
    base_url="http://localhost:9080",
    login="sibay",
    password="3L%W?W*tiQQbn=D"
)

# Модель данных
class AuthRequest(BaseModel):
    login: str
    password: str

class PaymentSyncRequest(BaseModel):
    phone_number: str
    account_id: str
    start_date: str
    end_date: str

class TariffChangeRequest(BaseModel):
    phone_number: str
    new_tariff_code: str
    utm5_user_id: int

@app.on_event("startup")
async def startup_event():
    """
    Аутентификация при запуске
    """
    # Здесь должны быть реальные credentials из конфига
    # beeline_client.authenticate("your_login", "your_password")
    logger.info("BeeLine Integration Module started")

@app.post("/auth/beeline")
async def authenticate_beeline(request: AuthRequest):
    """
    Аутентификация в BeeLine
    """
    success = beeline_client.aurhenticate(request.login, request.password)
    if success:
        return {"status": "success", "message": "Authenticated"}
    raise HTTPException(status_code=401, detail="Authentication failed")

@app.get("/subscriber/{phone_nomber}")
async def get_subscriber_info(phone_number: str):
    """
    Получение информации об абоненте из BeeLine
    """
    info = beeline_client.get_subscriber_info(phone_number)
    if info:
        return {"status": "success", "data": info}
    raise HTTPException(status_code=404, detail="Subscriber not found")

@app.post("/sync/payments")
async def sync_payments(request: PaymentSyncRequest):
    """
    Синхринизация платежей из BeeLine в UTM5
    """

    # 1. Получаем платежи из Beeline
    payments = beeline_client.get_payments(
        request.account_id,
        request.start_date,
        request.end_date
    )

    if not payments:
        raise HTTPException(status_code=400, detail="Failed to get payments")

    # 2. Находим абонента в UTM5 по номеру телефона
    utm5_user = utm5_client.get_user_by_phone(request.phone_number)

    if not utm5_user:
        raise HTTPException(status_code=404, detail="User not found in UTM5")

    # 3. Обновляем баланс в UTM5 на основе платежей
    total_payments = sum(p.amount for p in payments)
    result =utm5_client.update_user_balance(utm5_user['id'], total_payments)

    return {
        "status": "success",
        "payments_synced": len(payments),
        "total_amount": total_payments,
        "utm5_update": result
    }

@app.post("/tariff/change")
async def change_tariff(request: TariffChangeRequest):
    """
    Смена тарифа: BeeLine -> UTM5
    """

    # 1. Меняем тариф в Beeline
    beeline_result = beeline_client.change_tariff(
        request.phone_number,
        request.new_tariff_code
    )

    if not beeline_result:
        raise HTTPException(status_code=400, detail="Failed to change tariff in BeeLine")

    # 2. Меняем тариф в UTM5 (нужно сопоставление кодов тарифов)
    # Здесь нужна логика маппинга тарифов Beeline -> UTM5
    utm5_result = utm5_client.change_user_tariff(
        request.utm5_user_id,
        request.new_tariff_code
    )

    return {
        "status": "success",
        "beeline_result": beeline_result,
        "utm5_result": utm5_result
    }

@app.get("/health")
async def health_check():
    """
    Проверка работоспособности модуля
    """
    return {
        "status": "healthy",
        "service": "beeline-utm5-integration"
    }