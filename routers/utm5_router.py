"""
Мост Beeline <-> UTM5.

Принцип: роут получает данные, делает 1-2 прямых вызова в utm5/*.py
и отдаёт результат или транслирует исключение UTM5 в HTTP-статус.
Никакой бизнес-логики (нет угадывания полей, нет дублей-проверок,
нет "подобрать похожего абонента") — это ответственность вызывающей
стороны.

Идентификация абонента — ОДИН из двух вариантов на каждый запрос:
  1) ctn        — мост сам сделает один поиск find_by_phone() в UTM5.
                  Если не найден -> 404. Если у абонента несколько
                  счетов, берётся первый (см. resolve_account_id) —
                  это единственное "решение", и оно уже было в UTM5 SDK.
  2) account_id  — прямой номер счёта UTM5, без поиска.
     (+ user_id, если он уже известен вызывающей стороне — тогда
      экономим один GET к UTM5)

Передавать оба варианта одновременно не нужно: если есть account_id,
ctn игнорируется.

Дубли платежей: мост НЕ хранит журнал и не проверяет повторную
отправку одного и того же платежа — если вызвать /payment дважды
с одинаковыми данными, в UTM5 будет два платежа. Защита от повторной
отправки — ответственность вызывающей программы (не дублировать
запрос до получения ответа).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from dependencies_utm5 import get_utm5_client
from utm5 import (
    UTM5AuthError,
    UTM5BadRequest,
    UTM5Client,
    UTM5Error,
    UTM5MappingError,
    UTM5NotFound,
    UTM5ServerError,
    UTM5Unavailable,
    PaymentRequest,
)
from utm5.blocks import BLOCK_VOLUNTARY

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/utm5", tags=["UTM5"])

# ---------------------------------------------------------------------- #
# трансляция ошибок UTM5 -> HTTP (единственное "решение" моста)
# ---------------------------------------------------------------------- #
def _http_error(exc: UTM5Error) -> HTTPException:
    """
    Каждому классу ошибки UTM5 — свой честный HTTP-статус.
    """
    if isinstance(exc, UTM5NotFound):
        return HTTPException(status_code=404, detail=exc.message)
    if isinstance(exc, UTM5AuthError):
        return HTTPException(status_code=502, detail=f"UTM5 авторизация: {exc.message}")
    if isinstance(exc, UTM5BadRequest):
        return HTTPException(status_code=422, detail=exc.message)
    if isinstance(exc, (UTM5Unavailable, UTM5ServerError)):
        return HTTPException(status_code=500, detail=exc.message)
    return HTTPException(status_code=500, detail=exc.message)

def _resolve_account(
    client: UTM5Client,
    *,
    ctn: Optional[str],
    account_id: Optional[int],
    user_id: Optional[int],
) -> tuple[int, int]:
    """
    Возвращает (user_id, account_id) ровно одним путём, без фолбэков:

      - account_id передан            -> берём его как есть (user_id доёргиваем, если не дали)
      - иначе ctn передан             -> один find_by_phone(), не найден -> 404
      - иначе                          -> 422 "не хватает идентификатора"
    """
    if account_id:
        if user_id:
            return user_id, account_id
        account = client.users.get_account(account_id)
        return account.user_id, account.account_id

    if ctn:
        user = client.users.find_by_phone(ctn)
        if not user:
            raise UTM5NotFound(f"UTM5: абонент с номером {ctn!r} не найден")
        resolved_account_id = client.users.resolve_account_id(user)
        return user.user_id, resolved_account_id

    raise UTM5BadRequest("Нужно передать либо ctn, либо account_id")


# ---------------------------------------------------------------------- #
# схемы запросов
# ---------------------------------------------------------------------- #
class SubscriberIdentity(BaseModel):
    """
    Общая часть идентификации — либо ctn, либо account_id/user_id.
    """
    ctn: Optional[str] = Field(None, description="Номер телефона Beeline (если нет account_id)")
    account_id: Optional[int] = Field(None, discriminator="Номер счёта UTM5 (приоритетнее ctn)")
    user_id: Optional[int] = Field(None, description="ID абонента UTM5 (опционально вместе с account_id)")

class BlockBody(SubscriberIdentity):
    block_type: int = Field(2, description="1 — админ, 2 — добровольная, 3 — с сохранением начислений")
    start_ts: int = Field(0, description="Unix-время начала блокировки, 0 — сейчас")
    end_ts: int = Field(0, description="Unix-время окончания, 0 — бессрочно")

class TariffChangeBody(SubscriberIdentity):
    tariff_id: Optional[int] = Field(None, description="ID тарифа UTM5")
    tariff_name: Optional[str] = Field(None, description="Имя тарифа UTM5 (если нет tariff_id)")
    change_now: bool = Field(True, description="True — сменить сразу, False — со следующего периода")

class PaymentBody(SubscriberIdentity):
    amount: float = Field(..., gt=0, description="Сумма платежа, > 0")
    comment: str = Field("", description="Комментарий к платежу")
    external_number: str = Field("", description="Внешний номер платежа (для сверки в UTM5)")
    actual_date: Optional[int] = Field(None, description="Unix-время платежа, по умолчанию — сейчас")

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
# абонент / счёт
# ---------------------------------------------------------------------- #
@router.get("/subscriber", summary="Карточка абонента и счёта (по ctn ИЛИ account_id)")
async def utm5_subscriber(
    ctn: Optional[str] = Query(None),
    account_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    client: UTM5Client = Depends(get_utm5_client),
) -> Dict[str, Any]:
    try:
        uid, aid = _resolve_account(
            client,
            ctn=ctn,
            account_id=account_id,
            user_id=user_id
        )
        user = client.users.get_by_id(uid)
        account = client.users.get_account(aid)
    except UTM5Error as exc:
        raise _http_error(exc) from exc

    return {
        "user_id": user.user_id,
        "login": user.login,
        "full_name": user.full_name,
        "account_id": account.account_id,
        "balance": account.balance,
        "credit": account.credit,
        "is_blocked": account.is_blocked,
    }

# ---------------------------------------------------------------------- #
# блокировки
# ---------------------------------------------------------------------- #
@router.post("/block", summary="Заблокировать счёт (по ctn ИЛИ account_id)")
async def utm5_block(
    body: BlockBody,
    client: UTM5Client = Depends(get_utm5_client),
) -> Dict[str, Any]:
    try:
        _, aid = _resolve_account(
            client,
            ctn=body.ctn,
            account_id=body.account_id,
            user_id=body.user_id
        )
        account = client.users.get_account(aid)
        result = client.blocks.block(
            account,
            block_type=body.block_type,
            start_ts=body.start_ts,
            end_ts=body.end_ts,
        )
    except UTM5Error as exc:
        raise _http_error(exc) from exc
    return {"status": "success", "account_id": aid, "result": result}

@router.post("/unblock", summary="Снять блокировку со счёта (по ctn ИЛИ account_id)")
async def utm5_unblock(
    body: SubscriberIdentity,
    client: UTM5Client = Depends(get_utm5_client),
) -> Dict[str, Any]:
    try:
        _, aid = _resolve_account(
            client,
            ctn=body.ctn,
            account_id=body.account_id,
            user_id=body.user_id
        )
        account = client.users.get_account(aid)
        result = client.blocks.unblock(account)
    except UTM5Error as exc:
        raise _http_error(exc) from exc
    return {"status": "success", "account_id": aid, "result": result}

@router.get("/blocks", summary="История и активные блокировки счёта (по ctn ИЛИ account_id)")
async def utm5_blocks_info(
    ctn: Optional[str] = Query(None),
    account_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    client: UTM5Client = Depends(get_utm5_client),
) -> Dict[str, Any]:
    try:
        _, aid = _resolve_account(
            client,
            ctn=ctn,
            account_id=account_id,
            user_id=user_id
        )
        blocks = client.blocks.get_blocks_info(aid)
    except UTM5Error as exc:
        raise _http_error(exc) from exc
    return {"account_id": aid, "blocks": blocks}


@router.delete("/blocks/{block_id}", summary="Удалить запись о блокировке по её id")
async def utm5_delete_block(
    block_id: int = Path(...),
    client: UTM5Client = Depends(get_utm5_client),
) -> Dict[str, Any]:
    try:
        result = client.blocks.delete_block(block_id)
    except UTM5Error as exc:
        raise _http_error(exc) from exc
    return {"status": "success", "result": result}

# ---------------------------------------------------------------------- #
# тариф
# ---------------------------------------------------------------------- #
@router.post("/tariff/change", summary="Сменить тариф счёта (по ctn ИЛИ account_id)")
async def utm5_tariff_change(
    body: TariffChangeBody,
    client: UTM5Client = Depends(get_utm5_client),
) -> Dict[str, Any]:
    try:
        uid, aid = _resolve_account(
            client,
            ctn=body.ctn,
            account_id=body.account_id,
            user_id=body.user_id
        )
        tariff_id = body.tariff_id
        if not tariff_id:
            if not body.tariff_name:
                raise UTM5BadRequest("Нужно передать tariff_id или tariff_name")
            tariff_id = client.tariffs.require_by_name(body.tariff_name).tariff_id

        result = client.tariffs.assign(
            user_id=uid,
            account_id=aid,
            tariff_id=tariff_id,
            change_now=body.change_now,
        )
    except UTM5Error as exc:
        raise _http_error(exc) from exc
    return {"status": "success", "account_id": aid, "tariff_id": tariff_id, "result": result}

# ---------------------------------------------------------------------- #
# платежи
# ---------------------------------------------------------------------- #
@router.post("/payments", summary="Внести платёж (по ctn ИЛИ account_id); дубли не проверяются")
async def utm5_payment(
    body: PaymentBody,
    client: UTM5Client = Depends(get_utm5_client),
) -> Dict[str, Any]:
    try:
        uid, aid = _resolve_account(
            client,
            ctn=body.ctn,
            account_id=body.account_id,
            user_id=body.user_id,
        )
        request = PaymentRequest(
            account_id=aid,
            user_id=uid,
            amount=body.amount,
            comment=body.comment,
            external_number=body.external_number,
            actual_date=body.actual_date,
        )
        payment = client.payments.create(request)
    except UTM5Error as exc:
        raise _http_error(exc) from exc
    return {"status": "success", "transaction_id": payment.transaction_id, "account_id": payment.account_id, "amount": payment.amount}

@router.delete("/payment/{payment_id}", summary="Отменить ранее проведённый платёж")
async def utm5_cancel_payment(
    payment_id: int = Path(...),
    client: UTM5Client = Depends(get_utm5_client),
) -> Dict[str, Any]:
    try:
        result = client.payments.cancel(payment_id)
    except UTM5Error as exc:
        raise _http_error(exc) from exc
    return {"status": "success", "result": result}