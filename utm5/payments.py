from __future__ import annotations

import logging
import time
from typing import Any, Dict

from .errors import UTM5BadRequest
from .models import PaymentRequest, UTM5Payment
from .settings import UTM5Settings
from .transport import UTM5Transport

logger = logging.getLogger(__name__)


class PaymentRepository:
    """Операции с деньгами абонента."""

    def __init__(self, transport: UTM5Transport, settings: UTM5Settings):
        self._transport = transport
        self._settings = settings

    # ------------------------------------------------------------------ #
    def create(self, request: PaymentRequest) -> UTM5Payment:
        """
        POST tariffing/payments — внести платёж на лицевой счёт.

        Сумма должна быть строго положительной: для списаний UTM5 использует
        отдельный механизм начислений, а не отрицательный платёж.
        """
        if request.amount <= 0:
            raise UTM5BadRequest(f"UTM5: сумма платежа должна быть > 0, получено {request.amount}")
        if not request.account_id:
            raise UTM5BadRequest("UTM5: не указан account_id для платежа")

        payload = request.to_api(
            default_method=self._settings.payment_method_id,
            default_currency=self._settings.currency_id,
            default_inet=self._settings.turn_on_inet,
            now_ts=int(time.time()),
        )
        logger.info(
            "UTM5: провожу платёж account_id=%s сумма=%.2f внешний_номер=%r",
            request.account_id, request.amount, request.external_number,
        )
        body = self._transport.post("tariffing/payments", payload)
        payment = UTM5Payment.from_api(
            body if isinstance(body, dict) else {},
            account_id=request.account_id,
            amount=request.amount,
            comment=request.comment,
        )
        logger.info("UTM5: платёж проведён, transaction_id=%s", payment.transaction_id)
        return payment

    # ------------------------------------------------------------------ #
    def cancel(self, payment_id: int, *, admin_comment: str = "", user_comment: str = "") -> Dict[str, Any]:
        """PUT users/cancel_payment — откатить ранее проведённый платёж."""
        if not payment_id:
            raise UTM5BadRequest("UTM5: не указан payment_id для отмены")

        logger.warning("UTM5: отменяю платёж payment_id=%s", payment_id)
        body = self._transport.put(
            "users/cancel_payment",
            {
                "payment_id": payment_id,
                "admin_comment": admin_comment or "cancelled by beeline integration",
                "user_comment": user_comment or "cancelled by beeline integration",
            },
        )
        return body if isinstance(body, dict) else {"result": body}

    # ------------------------------------------------------------------ #
    def set_balance(self, account_id: int, new_balance: float, *, comment: str = "") -> Dict[str, Any]:
        """
        PUT users/change_account_balance — выставить баланс напрямую.

        Метод обходит историю платежей, поэтому применяйте его только для
        сверки/корректировок, а обычные зачисления проводите через create().
        """
        if not account_id:
            raise UTM5BadRequest("UTM5: не указан account_id для смены баланса")

        logger.warning(
            "UTM5: прямая корректировка баланса account_id=%s -> %.2f", account_id, new_balance
        )
        body = self._transport.put(
            "users/change_account_balance",
            {
                "account_id": account_id,
                "new_balance": round(float(new_balance), 2),
                "comment": comment or f"{self._settings.payment_comment_prefix}: корректировка",
            },
        )
        return body if isinstance(body, dict) else {"result": body}