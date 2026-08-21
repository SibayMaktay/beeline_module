from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .errors import UTM5NotFound
from .models import UTM5Account, UTM5User
from .transport import UTM5Transport

logger = logging.getLogger(__name__)


class UserRepository:
    """Чтение абонентов и их лицевых счетов."""

    def __init__(self, transport: UTM5Transport):
        self._transport = transport

    # ------------------------------------------------------------------ #
    # поиск
    # ------------------------------------------------------------------ #
    def search(self, value: str) -> List[UTM5User]:
        """
        POST users/search — свободный поиск по логину, ФИО, телефону, e-mail.

        Возвращает пустой список, если совпадений нет (исключение не бросает).
        """
        # поиск — операция чтения, её безопасно повторять при сбое биллинга
        body = self._transport.post("users/search", {"value": value}, idempotent=True)
        return [UTM5User.from_api(item) for item in self._as_list(body)]

    def search_one(self, value: str) -> Optional[UTM5User]:
        """Ровно один абонент или None. Если найдено несколько — пишет warning и берёт первого."""
        found = self.search(value)
        if not found:
            return None
        if len(found) > 1:
            logger.warning(
                "UTM5: по значению %r найдено %s абонентов, беру user_id=%s",
                value, len(found), found[0].user_id,
            )
        return found[0]

    def find_by_phone(self, phone: str) -> Optional[UTM5User]:
        """
        Поиск по номеру телефона с перебором форматов записи.

        Beeline отдаёт CTN как 9XXXXXXXXX, а в биллинге номер может быть
        сохранён как +79XXXXXXXXX, 89XXXXXXXXX или 79XXXXXXXXX.
        """
        for candidate in self._phone_variants(phone):
            user = self.search_one(candidate)
            if user:
                logger.info("UTM5: абонент найден по номеру %s -> user_id=%s", candidate, user.user_id)
                return user
        return None

    # ------------------------------------------------------------------ #
    # чтение по идентификатору
    # ------------------------------------------------------------------ #
    def get_by_id(self, user_id: int) -> UTM5User:
        body = self._transport.get("users", {"user_id": user_id})
        data = self._as_single(body)
        if not data:
            raise UTM5NotFound(f"UTM5: абонент user_id={user_id} не найден")
        return UTM5User.from_api(data)

    def get_by_login(self, login: str) -> UTM5User:
        body = self._transport.get("users", {"login": login})
        data = self._as_single(body)
        if not data:
            raise UTM5NotFound(f"UTM5: абонент с логином {login!r} не найден")
        return UTM5User.from_api(data)

    # ------------------------------------------------------------------ #
    # лицевые счета
    # ------------------------------------------------------------------ #
    def get_accounts(self, user_id: int) -> List[UTM5Account]:
        body = self._transport.get("users/accounts", {"user_id": user_id})
        return [UTM5Account.from_api(item) for item in self._as_list(body)]

    def get_account(self, account_id: int) -> UTM5Account:
        body = self._transport.get("users/accounts", {"account_id": account_id})
        data = self._as_single(body)
        if not data:
            raise UTM5NotFound(f"UTM5: лицевой счёт account_id={account_id} не найден")
        return UTM5Account.from_api(data)

    def resolve_account_id(self, user: UTM5User) -> int:
        """
        Определяет лицевой счёт для операций.

        Сначала берём basic_account из карточки абонента; если биллинг его
        не заполнил — дочитываем список счетов отдельным запросом.
        """
        if user.preferred_account_id:
            return user.preferred_account_id

        accounts = self.get_accounts(user.user_id)
        if not accounts:
            raise UTM5NotFound(f"UTM5: у абонента user_id={user.user_id} нет лицевых счетов")
        if len(accounts) > 1:
            logger.warning(
                "UTM5: у user_id=%s несколько счетов %s, беру первый",
                user.user_id, [a.account_id for a in accounts],
            )
        return accounts[0].account_id

    # ------------------------------------------------------------------ #
    # вспомогательное
    # ------------------------------------------------------------------ #
    @staticmethod
    def _phone_variants(phone: str) -> List[str]:
        digits = "".join(ch for ch in str(phone) if ch.isdigit())
        if not digits:
            return []
        if len(digits) == 11 and digits[0] in ("7", "8"):
            national = digits[1:]
        elif len(digits) == 10:
            national = digits
        else:
            national = digits

        variants = [digits, national, f"7{national}", f"8{national}", f"+7{national}"]
        seen, ordered = set(), []
        for item in variants:
            if item and item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered

    @staticmethod
    def _as_list(body: Any) -> List[Dict[str, Any]]:
        if isinstance(body, list):
            return [item for item in body if isinstance(item, dict)]
        if isinstance(body, dict):
            for key in ("items", "data", "users", "result"):
                nested = body.get(key)
                if isinstance(nested, list):
                    return [item for item in nested if isinstance(item, dict)]
            return [body] if body else []
        return []

    @staticmethod
    def _as_single(body: Any) -> Optional[Dict[str, Any]]:
        if isinstance(body, dict) and body:
            return body
        if isinstance(body, list) and body and isinstance(body[0], dict):
            return body[0]
        return None