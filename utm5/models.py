from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _to_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_str(value: Any, default: str = "") -> str:
    return default if value is None else str(value)


@dataclass(frozen=True)
class UTM5User:
    """Абонент UTM5 (ответ users / users/search)."""

    user_id: int
    login: str
    full_name: str = ""
    email: str = ""
    basic_account_id: int = 0
    account_ids: List[int] = field(default_factory=list)
    mobile_telephone: str = ""
    is_blocked: bool = False
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "UTM5User":
        accounts = data.get("accounts") or []
        return cls(
            user_id=_to_int(data.get("user_id") or data.get("id")),
            login=_to_str(data.get("login")),
            full_name=_to_str(data.get("full_name")),
            email=_to_str(data.get("email")),
            basic_account_id=_to_int(data.get("basic_account")),
            account_ids=[_to_int(a) for a in accounts if _to_int(a)],
            mobile_telephone=_to_str(data.get("mobile_telephone")),
            is_blocked=bool(_to_int(data.get("is_blocked"))),
            raw=data,
        )

    @property
    def preferred_account_id(self) -> int:
        """Базовый лицевой счёт, а если его нет — первый из списка."""
        if self.basic_account_id:
            return self.basic_account_id
        return self.account_ids[0] if self.account_ids else 0


@dataclass(frozen=True)
class UTM5Account:
    """Лицевой счёт (ответ users/accounts)."""

    account_id: int
    user_id: int
    balance: float = 0.0
    credit: float = 0.0
    block_type: int = 0
    external_id: str = ""
    contract_number: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "UTM5Account":
        return cls(
            account_id=_to_int(data.get("account_id") or data.get("id")),
            user_id=_to_int(data.get("user_id")),
            balance=_to_float(data.get("balance")),
            credit=_to_float(data.get("credit")),
            block_type=_to_int(data.get("block_type")),
            external_id=_to_str(data.get("external_id")),
            contract_number=_to_str(data.get("contract_number")),
            raw=data,
        )

    @property
    def is_blocked(self) -> bool:
        return self.block_type != 0

    @property
    def available_funds(self) -> float:
        """Сколько абонент реально может потратить с учётом кредита."""
        return self.balance + self.credit


@dataclass(frozen=True)
class UTM5Tariff:
    """Тариф из справочника tariffing/tariffs."""

    tariff_id: int
    name: str
    comments: str = ""
    accounts_linked: int = 0
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "UTM5Tariff":
        return cls(
            tariff_id=_to_int(data.get("id") or data.get("tariff_id")),
            name=_to_str(data.get("name")),
            comments=_to_str(data.get("comments")),
            accounts_linked=_to_int(data.get("accounts_linked")),
            raw=data,
        )


@dataclass(frozen=True)
class UTM5TariffLink:
    """Связка «лицевой счёт ↔ тариф» (users/tarifflinks)."""

    tariff_link_id: int
    account_id: int
    current_tariff_id: int
    next_tariff_id: int = 0
    accounting_period_id: int = 0
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "UTM5TariffLink":
        return cls(
            tariff_link_id=_to_int(data.get("id") or data.get("tariff_link_id")),
            account_id=_to_int(data.get("account_id")),
            current_tariff_id=_to_int(data.get("current_tariff_id")),
            next_tariff_id=_to_int(data.get("next_tariff_id")),
            accounting_period_id=_to_int(data.get("accounting_period_id")),
            raw=data,
        )


@dataclass(frozen=True)
class UTM5Payment:
    """Результат проведённого платежа."""

    transaction_id: int
    account_id: int
    amount: float
    comment: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: Dict[str, Any], *, account_id: int, amount: float, comment: str) -> "UTM5Payment":
        return cls(
            transaction_id=_to_int(data.get("payment_transaction_id") or data.get("payment_id")),
            account_id=account_id,
            amount=amount,
            comment=comment,
            raw=data if isinstance(data, dict) else {"response": data},
        )


@dataclass(frozen=True)
class PaymentRequest:
    """Намерение провести платёж — то, что сервис передаёт репозиторию."""

    account_id: int
    user_id: int
    amount: float
    comment: str
    admin_comment: str = ""
    external_number: str = ""
    actual_date: Optional[int] = None
    method_id: Optional[int] = None
    currency_id: Optional[int] = None
    turn_on_inet: Optional[int] = None

    def to_api(self, *, default_method: int, default_currency: int, default_inet: int, now_ts: int) -> Dict[str, Any]:
        """Сборка тела для POST tariffing/payments."""
        actual = self.actual_date or now_ts
        return {
            "account_id": self.account_id,
            "user_id": self.user_id,
            "payment_incurrency": round(self.amount, 2),
            "currency_id": self.currency_id or default_currency,
            "actual_date": actual,
            "payment_enter_date": now_ts,
            "burn_time": 0,
            "method": self.method_id or default_method,
            "admin_comment": self.admin_comment or self.comment,
            "comment": self.comment,
            "payment_ext_number": self.external_number,
            "payment_to_invoice": 0,
            "turn_on_inet": default_inet if self.turn_on_inet is None else self.turn_on_inet,
        }