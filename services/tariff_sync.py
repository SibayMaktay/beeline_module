from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from utm5 import UTM5Client

from .mapper import BeelineUTM5Mapper

logger = logging.getLogger(__name__)


@dataclass
class TariffSyncResult:
    """Итог смены тарифа."""

    ctn: str
    user_id: int
    account_id: int
    beeline_price_plan: str
    utm5_tariff_id: int
    previous_tariff_id: int
    changed: bool
    change_now: bool
    details: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ctn": self.ctn,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "beeline_price_plan": self.beeline_price_plan,
            "utm5_tariff_id": self.utm5_tariff_id,
            "previous_tariff_id": self.previous_tariff_id,
            "changed": self.changed,
            "change_now": self.change_now,
            "details": self.details,
        }


class TariffSyncService:
    """Приводит тариф в UTM5 в соответствие с тарифным планом Beeline."""

    def __init__(self, client: UTM5Client, mapper: BeelineUTM5Mapper):
        self._client = client
        self._mapper = mapper

    # ------------------------------------------------------------------ #
    def sync(
        self,
        ctn: str,
        beeline_price_plan: str,
        *,
        change_now: bool = True,
        force: bool = False,
    ) -> TariffSyncResult:
        """
        Переключает тариф лицевого счёта.

        force=False (по умолчанию) не трогает биллинг, если нужный тариф уже
        назначен — это делает вызов идемпотентным и безопасным для повторов.
        """
        binding = self._mapper.bind_subscriber(ctn)
        tariff_id = self._mapper.resolve_tariff_id(beeline_price_plan)

        current = self._client.tariffs.get_current_link(
            user_id=binding.user_id, account_id=binding.account_id
        )
        previous_id = current.current_tariff_id if current else 0

        if previous_id == tariff_id and not force:
            logger.info(
                "CTN %s: тариф %s уже назначен счёту %s, изменений не требуется",
                ctn, tariff_id, binding.account_id,
            )
            return TariffSyncResult(
                ctn=binding.ctn,
                user_id=binding.user_id,
                account_id=binding.account_id,
                beeline_price_plan=beeline_price_plan,
                utm5_tariff_id=tariff_id,
                previous_tariff_id=previous_id,
                changed=False,
                change_now=change_now,
                details={"reason": "already assigned"},
            )

        details = self._client.tariffs.assign(
            user_id=binding.user_id,
            account_id=binding.account_id,
            tariff_id=tariff_id,
            change_now=change_now,
            tariff_link_id=current.tariff_link_id if current else 0,
            accounting_period_id=current.accounting_period_id if current else 0,
        )
        logger.info(
            "CTN %s: тариф счёта %s изменён %s -> %s", ctn, binding.account_id, previous_id, tariff_id
        )
        return TariffSyncResult(
            ctn=binding.ctn,
            user_id=binding.user_id,
            account_id=binding.account_id,
            beeline_price_plan=beeline_price_plan,
            utm5_tariff_id=tariff_id,
            previous_tariff_id=previous_id,
            changed=True,
            change_now=change_now,
            details=details,
        )

    # ------------------------------------------------------------------ #
    def current_tariff(self, ctn: str) -> Optional[int]:
        """Возвращает текущий tariff_id счёта абонента или None."""
        binding = self._mapper.bind_subscriber(ctn)
        link = self._client.tariffs.get_current_link(
            user_id=binding.user_id, account_id=binding.account_id
        )
        return link.current_tariff_id if link else None