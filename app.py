import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any, List, Dict
import config.config as config
from services.logging_config import setup_logging
from services.token_manager import get_beeline_token, invalidate_token
from services.pydantic_models import (
    PutCallForwardRequestEdit, AddDelSoc, SuspendRestoreCTN, ReplaceSim,
    Details, CTNInfoList, CTNInfoListPaged, ChangePP, SIMList, SIMListPaged,
    RequestList, ServicesList, ServicesListPaged, PaymentList, PaymentListPaged,
    AdjustmentList, GetBillCalls, GetBillCallsPaged, GetBillCharges, GetBillChargesPaged,
    SharedNumberDOL, SharedNumberListDOL, SharedNumberDeleteDOL, PersonalDataUpdate,
    PersonalDataResultRequest, GetDataReportRequest, GetBANInfoListPagedRequest,
    CreateBillRequest, CreateDetailsRequest, GetDataRequest
)
from middleware.rate_limiter import RateLimitMiddleware

from client.beeline_soap_client import BeelineSoapClient
from client.beeline_rest_client import BeelineRestClient
from routers.utm5_router import router as utm5_router
from dependencies_utm5 import shutdown_utm5

setup_logging(
    level=config.log_level,
    log_file=None  # Можно указать путь к файлу: "/var/log/beeline_module/module.log"
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
app.add_middleware(
    RateLimitMiddleware,
    requests_per_window=100,  # 100 запросов в минуту
    window_seconds=60,
    excluded_paths=["/docs", "/redoc", "/openapi.json", "/health", "/utm5/health"],
    admin_api_key=config.module_api_key  # Admin API key освобождает от rate limiting
)
app.include_router(utm5_router)

BRIDGE_API_KEY = config.module_api_key

@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    """
    Проверяет API ключ во всех запросах к мосту.
    """
    if request.url.path in ["/docs", "/redoc", "/openapi.json", "/utm5/health", "/health"]:
        return await call_next(request)
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != BRIDGE_API_KEY:
        return JSONResponse(
            status_code=403,
            content={"detail": "Invalid or missing X-API-Key header"}
        )
    return await call_next(request)

@app.get("/health", summary="Проверка связи с модулем")
async def module_health_check():
    return {
        "status": "health",
        "host": config.module_host,
        "port": config.module_port
    }
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.module_host,
        port=config.module_port,
        log_level=config.log_level
    )