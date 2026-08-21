from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from dependencies_utm5 import (
    get_block_sync_service,
    get_payment_sync_service,
    get_tariff_sync_service,
    get_utm5_client,
)
from services import BlockSyncService, PaymentSyncService, TariffSyncService
from utm5 import (
    UTM5AuthError,
    UTM5BadRequest,
    UTM5Client,
    UTM5Error,
    UTM5MappingError,
    UTM5NotFound,
    UTM5ServerError,
    UTM5Unavailable,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/utm5", tags=["UTM5"])


# ---------------------------------------------------------------------- #
# схемы запросов
# ---------------------------------------------------------------------- #
class PaymentSyncBody(BaseModel):
    """Пачка платежей Beeline для зачисления абоненту."""

    ctn: str = Field(..., description="Номер абонента Beeline")
    payments: List[Dict[str, Any]] = Field(
        ..., description="Записи платежей как их вернул getPaymentList"
    )


class TariffSyncBody(BaseModel):
    ctn: str = Field(..., description="Номер абонента Beeline")
    price_plan: str = Field(..., description="Код тарифного плана Beeline")
    change_now: bool = Field(True, description="True — сменить сразу, False — со следующего периода")
    force: bool = Field(False, description="Переназначить тариф, даже если он уже установлен")


class BlockSyncBody(BaseModel):
    ctn: str = Field(..., description="Номер абонента Beeline")
    blocked: bool = Field(..., description="True — заблокировать счёт, False — разблокировать")
    block_type: int = Field(2, description="1 — админ, 2 — добровольная, 3 — с сохранением начислений")
    start_ts: int = Field(0, description="Unix-время начала блокировки, 0 — сейчас")
    end_ts: int = Field(0, description="Unix-время окончания, 0 — бессрочно")


# ---------------------------------------------------------------------- #
# трансляция ошибок
# ---------------------------------------------------------------------- #
def _http_error(exc: UTM5Error) -> HTTPException:
    """Каждому классу ошибки — свой честный HTTP-статус."""
    if isinstance(exc, UTM5NotFound):
        return HTTPException(status_code=404, detail=exc.message)
    if isinstance(exc, UTM5AuthError):
        return HTTPException(status_code=502, detail=f"UTM5 авторизация: {exc.message}")
    if isinstance(exc, UTM5MappingError):
        return HTTPException(status_code=422, detail=exc.message)
    if isinstance(exc, UTM5BadRequest):
        return HTTPException(status_code=400, detail=exc.message)
    if isinstance(exc, (UTM5Unavailable, UTM5ServerError)):
        return HTTPException(status_code=503, detail=exc.message)
    return HTTPException(status_code=502, detail=exc.message)


# ---------------------------------------------------------------------- #
# служебные эндпоинты
# ---------------------------------------------------------------------- #
@router.get("/health", summary="Проверка связи с UTM5")
async def utm5_health(client: UTM5Client = Depends(get_utm5_client)) -> Dict[str, Any]:
    try:
        client.ping()
    except UTM5Error as exc:
        return {"utm5": "unavailable", "detail": exc.message}
    return {"utm5": "ok", "api_url": client.settings.api_url}


@router.get("/subscriber/{ctn}", summary="Карточка абонента UTM5 по номеру Beeline")
async def utm5_subscriber(
    ctn: str = Path(..., description="Номер абонента Beeline"),
    blocks: BlockSyncService = Depends(get_block_sync_service),
) -> Dict[str, Any]:
    try:
        return blocks.status(ctn)
    except UTM5Error as exc:
        raise _http_error(exc) from exc


@router.get("/tariffs", summary="Справочник тарифов UTM5")
async def utm5_tariffs(
    name: Optional[str] = Query(None, description="Фильтр по подстроке имени"),
    client: UTM5Client = Depends(get_utm5_client),
) -> Dict[str, Any]:
    try:
        tariffs = client.tariffs.list_tariffs()
    except UTM5Error as exc:
        raise _http_error(exc) from exc

    if name:
        needle = name.casefold()
        tariffs = [t for t in tariffs if needle in t.name.casefold()]
    return {
        "count": len(tariffs),
        "items": [{"id": t.tariff_id, "name": t.name, "comments": t.comments} for t in tariffs],
    }


# ---------------------------------------------------------------------- #
# сценарии синхронизации
# ---------------------------------------------------------------------- #
@router.post("/sync/payments", summary="Зачислить платежи Beeline в UTM5")
async def utm5_sync_payments(
    body: PaymentSyncBody,
    service: PaymentSyncService = Depends(get_payment_sync_service),
) -> Dict[str, Any]:
    """
    Каждый платёж проводится отдельной транзакцией и ровно один раз:
    повторный вызов с теми же данными вернёт их со статусом duplicate.
    """
    if not body.payments:
        raise HTTPException(status_code=400, detail="Список платежей пуст")
    try:
        report = service.sync(body.ctn, body.payments)
    except UTM5Error as exc:
        raise _http_error(exc) from exc

    # частичный успех — сообщаем честно, но не роняем весь запрос
    status = "success" if not report.failed else "partial"
    return {"status": status, "report": report.as_dict()}


@router.post("/sync/tariff", summary="Синхронизировать тариф Beeline -> UTM5")
async def utm5_sync_tariff(
    body: TariffSyncBody,
    service: TariffSyncService = Depends(get_tariff_sync_service),
) -> Dict[str, Any]:
    try:
        result = service.sync(
            body.ctn, body.price_plan, change_now=body.change_now, force=body.force
        )
    except UTM5Error as exc:
        raise _http_error(exc) from exc
    return {"status": "success", "result": result.as_dict()}


@router.post("/sync/block", summary="Синхронизировать блокировку Beeline -> UTM5")
async def utm5_sync_block(
    body: BlockSyncBody,
    service: BlockSyncService = Depends(get_block_sync_service),
) -> Dict[str, Any]:
    try:
        result = service.sync(
            body.ctn,
            blocked=body.blocked,
            block_type=body.block_type,
            start_ts=body.start_ts,
            end_ts=body.end_ts,
        )
    except UTM5Error as exc:
        raise _http_error(exc) from exc
    return {"status": "success", "result": result.as_dict()}