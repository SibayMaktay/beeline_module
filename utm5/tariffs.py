from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .errors import UTM5BadRequest, UTM5NotFound
from .models import UTM5Tariff, UTM5TariffLink
from .transport import UTM5Transport

logger = logging.getLogger(__name__)


class TariffRepository:
    """Справочник тарифов и управление тарифными связками."""

    def __init__(self, transport: UTM5Transport):
        self._transport = transport

    # ------------------------------------------------------------------ #
    # справочник
    # ------------------------------------------------------------------ #
    def list_tariffs(self) -> List[UTM5Tariff]:
        """GET tariffing/tariffs — все тарифы биллинга."""
        body = self._transport.get("tariffing/tariffs")
        return [UTM5Tariff.from_api(item) for item in self._as_list(body)]

    def find_by_name(self, name: str) -> Optional[UTM5Tariff]:
        """Поиск тарифа по имени без учёта регистра и краевых пробелов."""
        needle = name.strip().casefold()
        for tariff in self.list_tariffs():
            if tariff.name.strip().casefold() == needle:
                return tariff
        return None

    def require_by_name(self, name: str) -> UTM5Tariff:
        tariff = self.find_by_name(name)
        if not tariff:
            raise UTM5NotFound(f"UTM5: тариф с именем {name!r} не найден в справочнике")
        return tariff

    # ------------------------------------------------------------------ #
    # тарифные связки
    # ------------------------------------------------------------------ #
    def get_links(self, *, user_id: int, account_id: int) -> List[UTM5TariffLink]:
        """GET users/tarifflinks — действующие связки счёта."""
        body = self._transport.get(
            "users/tarifflinks", {"user_id": user_id, "account_id": account_id}
        )
        return [UTM5TariffLink.from_api(item) for item in self._as_list(body)]

    def get_current_link(self, *, user_id: int, account_id: int) -> Optional[UTM5TariffLink]:
        links = self.get_links(user_id=user_id, account_id=account_id)
        return links[0] if links else None

    def assign(
        self,
        *,
        user_id: int,
        account_id: int,
        tariff_id: int,
        change_now: bool = True,
        tariff_link_id: int = 0,
        accounting_period_id: int = 0,
        second_tariff_id: int = 0,
        new_accounting_period_id: int = 0,
    ) -> Dict[str, Any]:
        """
        POST users/tarifflinks — назначить тариф лицевому счёту.

        change_now=True меняет тариф немедленно, False — со следующего
        расчётного периода. Если tariff_link_id не передан, он берётся из
        текущей связки: так UTM5 обновит существующую, а не создаст дубль.
        """
        if not tariff_id:
            raise UTM5BadRequest("UTM5: не указан tariff_id")
        if not account_id:
            raise UTM5BadRequest("UTM5: не указан account_id")

        if not tariff_link_id or not accounting_period_id:
            current = self.get_current_link(user_id=user_id, account_id=account_id)
            if current:
                tariff_link_id = tariff_link_id or current.tariff_link_id
                accounting_period_id = accounting_period_id or current.accounting_period_id

        payload = {
            "user_id": user_id,
            "account_id": account_id,
            "first_tariff_id": tariff_id,
            "second_tariff_id": second_tariff_id,
            "accounting_period_id": accounting_period_id,
            "new_accounting_period_id": new_accounting_period_id,
            "tariff_link_id": tariff_link_id,
            "change_now": bool(change_now),
        }
        logger.info(
            "UTM5: назначаю тариф %s счёту %s (немедленно=%s)", tariff_id, account_id, change_now
        )
        body = self._transport.post("users/tarifflinks", payload)
        return body if isinstance(body, dict) else {"result": body}

    def unschedule(self, tariff_link_id: int) -> Dict[str, Any]:
        """POST users/unschedule_tarifflink — отменить запланированную смену тарифа."""
        if not tariff_link_id:
            raise UTM5BadRequest("UTM5: не указан tariff_link_id")
        body = self._transport.post("users/unschedule_tarifflink", {"tariff_link_id": tariff_link_id})
        return body if isinstance(body, dict) else {"result": body}

    # ------------------------------------------------------------------ #
    @staticmethod
    def _as_list(body: Any) -> List[Dict[str, Any]]:
        if isinstance(body, list):
            return [item for item in body if isinstance(item, dict)]
        if isinstance(body, dict):
            for key in ("items", "data", "result"):
                nested = body.get(key)
                if isinstance(nested, list):
                    return [item for item in nested if isinstance(item, dict)]
            return [body] if body else []
        return []