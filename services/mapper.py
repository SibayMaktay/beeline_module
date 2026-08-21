from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from utm5 import UTM5Client, UTM5MappingError, UTM5NotFound

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SubscriberBinding:
    """Результат сопоставления номера Beeline с сущностями UTM5."""

    ctn: str
    user_id: int
    account_id: int
    login: str
    full_name: str


@dataclass(frozen=True)
class NormalizedPayment:
    """Платёж Beeline, приведённый к виду, пригодному для UTM5."""

    amount: float
    external_number: str
    actual_date: Optional[int]
    comment: str
    fingerprint: str
    source: Dict[str, Any]


class BeelineUTM5Mapper:
    """Переводчик между Beeline и UTM5."""

    #: поля, в которых Beeline может прислать сумму платежа
    AMOUNT_KEYS = ("amount", "paymentAmount", "sum", "payment_amount", "value")
    #: поля с уникальным номером платежа
    NUMBER_KEYS = ("paymentId", "payment_id", "id", "documentNumber", "orderId", "externalId")
    #: поля с датой платежа
    DATE_KEYS = ("date", "paymentDate", "payment_date", "actualDate", "createDate")

    def __init__(self, client: UTM5Client, tariff_map: Optional[Dict[str, Any]] = None):
        self._client = client
        self._tariff_map = tariff_map if tariff_map is not None else load_tariff_map()

    # ------------------------------------------------------------------ #
    # абонент
    # ------------------------------------------------------------------ #
    def bind_subscriber(self, ctn: str) -> SubscriberBinding:
        """
        Находит абонента UTM5 по номеру Beeline.

        Порядок поиска: по телефону во всех форматах, затем по логину,
        совпадающему с CTN, — так работает большинство внедрений.
        """
        user = self._client.users.find_by_phone(ctn)
        if not user:
            user = self._client.users.search_one(ctn)
        if not user:
            raise UTM5NotFound(f"UTM5: абонент для CTN {ctn} не найден ни по телефону, ни по логину")

        account_id = self._client.users.resolve_account_id(user)
        return SubscriberBinding(
            ctn=str(ctn),
            user_id=user.user_id,
            account_id=account_id,
            login=user.login,
            full_name=user.full_name,
        )

    # ------------------------------------------------------------------ #
    # тариф
    # ------------------------------------------------------------------ #
    def resolve_tariff_id(self, beeline_price_plan: str) -> int:
        """
        Переводит код тарифного плана Beeline в tariff_id UTM5.

        Карта задаётся файлом TARIFF_MAP_FILE и может содержать как числовые
        id, так и имена тарифов — имя дорезолвится через справочник биллинга.
        """
        key = str(beeline_price_plan).strip()
        target = self._tariff_map.get(key) or self._tariff_map.get(key.upper())
        if target is None:
            raise UTM5MappingError(
                f"Тарифный план Beeline {key!r} отсутствует в карте соответствия. "
                f"Добавьте его в {os.getenv('TARIFF_MAP_FILE', './config/tariff_map.json')}"
            )
        if isinstance(target, int) or str(target).isdigit():
            return int(target)
        return self._client.tariffs.require_by_name(str(target)).tariff_id

    # ------------------------------------------------------------------ #
    # платёж
    # ------------------------------------------------------------------ #
    def normalize_payment(self, raw: Dict[str, Any], *, ctn: str) -> NormalizedPayment:
        """Приводит запись getPaymentList к единому виду и считает отпечаток."""
        if not isinstance(raw, dict):
            raise UTM5MappingError(f"Ожидался словарь платежа, получено {type(raw).__name__}")

        amount = self._extract_amount(raw)
        if amount is None:
            raise UTM5MappingError(f"В записи платежа нет суммы: {self._short(raw)}")

        number = self._first_str(raw, self.NUMBER_KEYS)
        date_raw = self._first_str(raw, self.DATE_KEYS)
        actual_date = self._parse_timestamp(date_raw)

        comment = f"Beeline CTN {ctn}"
        if number:
            comment = f"{comment}, платёж {number}"

        return NormalizedPayment(
            amount=amount,
            external_number=number,
            actual_date=actual_date,
            comment=comment,
            fingerprint=self.fingerprint(ctn=ctn, number=number, amount=amount, date=date_raw),
            source=raw,
        )

    @staticmethod
    def fingerprint(*, ctn: str, number: str, amount: float, date: str) -> str:
        """
        Устойчивый отпечаток платежа.

        Если Beeline прислал номер документа — он и есть ключ. Если номера
        нет, ключ собирается из CTN, суммы и даты: этого достаточно, чтобы
        не провести один и тот же платёж дважды.
        """
        basis = f"{ctn}|{number}" if number else f"{ctn}|{amount:.2f}|{date}"
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32]

    # ------------------------------------------------------------------ #
    # разбор значений
    # ------------------------------------------------------------------ #
    def _extract_amount(self, raw: Dict[str, Any]) -> Optional[float]:
        for key in self.AMOUNT_KEYS:
            if key not in raw or raw[key] in (None, ""):
                continue
            try:
                # Beeline присылает суммы строкой, иногда с запятой и пробелами
                cleaned = str(raw[key]).replace(",", ".").replace("\xa0", "").replace(" ", "")
                return round(float(cleaned), 2)
            except (TypeError, ValueError):
                logger.warning("Не смог разобрать сумму из поля %s=%r", key, raw[key])
        return None

    @staticmethod
    def _first_str(raw: Dict[str, Any], keys) -> str:
        for key in keys:
            value = raw.get(key)
            if value not in (None, ""):
                return str(value).strip()
        return ""

    @staticmethod
    def _parse_timestamp(value: str) -> Optional[int]:
        """Beeline отдаёт даты в нескольких форматах — пробуем известные."""
        if not value:
            return None
        if value.isdigit() and len(value) == 10:
            return int(value)
        formats = (
            "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
            "%d.%m.%Y %H:%M:%S", "%d.%m.%Y", "%Y%m%d%H%M%S",
        )
        text = value.split(".")[0].split("+")[0].strip()
        for fmt in formats:
            try:
                return int(datetime.strptime(text, fmt).timestamp())
            except ValueError:
                continue
        logger.warning("Неизвестный формат даты платежа: %r", value)
        return None

    @staticmethod
    def _short(raw: Any) -> str:
        try:
            return json.dumps(raw, ensure_ascii=False)[:200]
        except (TypeError, ValueError):
            return str(raw)[:200]


def load_tariff_map(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Читает карту тарифов из JSON-файла.

    Формат:
        {"EXCLH11": 12, "EXCLH12": "Безлимитный 100", "BEELINE_TARIFF_3": 7}
    Отсутствие файла не является ошибкой — просто пустая карта.
    """
    file_path = path or os.getenv("TARIFF_MAP_FILE", "./config/tariff_map.json")
    if not os.path.exists(file_path):
        logger.warning("Карта тарифов %s не найдена, смена тарифа будет недоступна", file_path)
        return {}
    with open(file_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise UTM5MappingError(f"{file_path}: ожидался JSON-объект вида {{'план': tariff_id}}")
    return {str(k): v for k, v in data.items()}