from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from utm5 import PaymentRequest, UTM5Client, UTM5Error

from .ledger import PaymentLedger
from .mapper import BeelineUTM5Mapper, SubscriberBinding

logger = logging.getLogger(__name__)


@dataclass
class PaymentResult:
    """Итог обработки одной записи о платеже."""

    fingerprint: str
    amount: float
    status: str                      # applied | duplicate | failed
    transaction_id: Optional[int] = None
    external_number: str = ""
    error: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "amount": self.amount,
            "status": self.status,
            "transaction_id": self.transaction_id,
            "external_number": self.external_number,
            "error": self.error,
        }


@dataclass
class SyncReport:
    """Сводка по всей пачке платежей."""

    ctn: str
    user_id: int
    account_id: int
    results: List[PaymentResult] = field(default_factory=list)

    @property
    def applied(self) -> List[PaymentResult]:
        return [r for r in self.results if r.status == "applied"]

    @property
    def duplicates(self) -> List[PaymentResult]:
        return [r for r in self.results if r.status == "duplicate"]

    @property
    def failed(self) -> List[PaymentResult]:
        return [r for r in self.results if r.status == "failed"]

    @property
    def total_applied(self) -> float:
        return round(sum(r.amount for r in self.applied), 2)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ctn": self.ctn,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "total_received": len(self.results),
            "applied_count": len(self.applied),
            "duplicate_count": len(self.duplicates),
            "failed_count": len(self.failed),
            "total_applied_amount": self.total_applied,
            "items": [r.as_dict() for r in self.results],
        }


class PaymentSyncService:
    """Переносит платежи Beeline в UTM5 ровно один раз каждый."""

    def __init__(
        self,
        client: UTM5Client,
        mapper: BeelineUTM5Mapper,
        ledger: PaymentLedger,
    ):
        self._client = client
        self._mapper = mapper
        self._ledger = ledger

    # ------------------------------------------------------------------ #
    def sync(self, ctn: str, raw_payments: Iterable[Dict[str, Any]]) -> SyncReport:
        """
        Основной сценарий.

        1. Находим абонента и его лицевой счёт.
        2. Нормализуем каждую запись Beeline.
        3. Бронируем отпечаток в журнале (защита от гонки и повторов).
        4. Проводим платёж; при ошибке снимаем бронь, чтобы повторить позже.
        """
        binding = self._mapper.bind_subscriber(ctn)
        report = SyncReport(ctn=binding.ctn, user_id=binding.user_id, account_id=binding.account_id)

        for raw in raw_payments:
            report.results.append(self._process_one(raw, binding))

        logger.info(
            "Синхронизация CTN %s завершена: проведено %s на %.2f, дублей %s, ошибок %s",
            ctn, len(report.applied), report.total_applied,
            len(report.duplicates), len(report.failed),
        )
        return report

    # ------------------------------------------------------------------ #
    def _process_one(self, raw: Dict[str, Any], binding: SubscriberBinding) -> PaymentResult:
        try:
            payment = self._mapper.normalize_payment(raw, ctn=binding.ctn)
        except UTM5Error as exc:
            logger.error("Пропускаю некорректную запись платежа: %s", exc)
            return PaymentResult(fingerprint="", amount=0.0, status="failed", error=str(exc))

        if payment.amount <= 0:
            return PaymentResult(
                fingerprint=payment.fingerprint,
                amount=payment.amount,
                status="failed",
                external_number=payment.external_number,
                error="сумма платежа не положительная",
            )

        claimed = self._ledger.claim(
            payment.fingerprint,
            ctn=binding.ctn,
            account_id=binding.account_id,
            amount=payment.amount,
        )
        if not claimed:
            logger.info("Платёж %s уже проводился ранее — пропуск", payment.fingerprint)
            return PaymentResult(
                fingerprint=payment.fingerprint,
                amount=payment.amount,
                status="duplicate",
                external_number=payment.external_number,
            )

        try:
            created = self._client.payments.create(
                PaymentRequest(
                    account_id=binding.account_id,
                    user_id=binding.user_id,
                    amount=payment.amount,
                    comment=payment.comment,
                    external_number=payment.external_number,
                    actual_date=payment.actual_date,
                )
            )
        except UTM5Error as exc:
            # бронь снимаем, иначе платёж потеряется навсегда
            self._ledger.release(payment.fingerprint)
            logger.error("Платёж %s не проведён: %s", payment.fingerprint, exc)
            return PaymentResult(
                fingerprint=payment.fingerprint,
                amount=payment.amount,
                status="failed",
                external_number=payment.external_number,
                error=str(exc),
            )

        self._ledger.attach_transaction(payment.fingerprint, created.transaction_id)
        return PaymentResult(
            fingerprint=payment.fingerprint,
            amount=payment.amount,
            status="applied",
            transaction_id=created.transaction_id,
            external_number=payment.external_number,
        )