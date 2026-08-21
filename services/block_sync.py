from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict

from utm5 import UTM5Client
from utm5.blocks import BLOCK_NONE, BLOCK_VOLUNTARY

from .mapper import BeelineUTM5Mapper

logger = logging.getLogger(__name__)


@dataclass
class BlockSyncResult:
    """Итог синхронизации блокировки."""

    ctn: str
    user_id: int
    account_id: int
    should_be_blocked: bool
    was_blocked: bool
    changed: bool
    details: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ctn": self.ctn,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "should_be_blocked": self.should_be_blocked,
            "was_blocked": self.was_blocked,
            "changed": self.changed,
            "details": self.details,
        }


class BlockSyncService:
    """Ставит и снимает блокировку счёта вслед за состоянием номера Beeline."""

    def __init__(self, client: UTM5Client, mapper: BeelineUTM5Mapper):
        self._client = client
        self._mapper = mapper

    # ------------------------------------------------------------------ #
    def sync(
        self,
        ctn: str,
        *,
        blocked: bool,
        block_type: int = BLOCK_VOLUNTARY,
        start_ts: int = 0,
        end_ts: int = 0,
    ) -> BlockSyncResult:
        """
        Приводит блокировку счёта к желаемому состоянию.

        Если состояние уже совпадает, обращения к биллингу не происходит:
        повторный вызов безопасен.
        """
        binding = self._mapper.bind_subscriber(ctn)
        account = self._client.users.get_account(binding.account_id)
        was_blocked = account.is_blocked

        if was_blocked == blocked:
            logger.info(
                "CTN %s: состояние блокировки счёта %s уже корректно (blocked=%s)",
                ctn, binding.account_id, blocked,
            )
            return BlockSyncResult(
                ctn=binding.ctn,
                user_id=binding.user_id,
                account_id=binding.account_id,
                should_be_blocked=blocked,
                was_blocked=was_blocked,
                changed=False,
                details={"reason": "already in desired state"},
            )

        if blocked:
            details = self._client.blocks.block(
                account, block_type=block_type, start_ts=start_ts, end_ts=end_ts
            )
        else:
            details = self._client.blocks.unblock(account)

        return BlockSyncResult(
            ctn=binding.ctn,
            user_id=binding.user_id,
            account_id=binding.account_id,
            should_be_blocked=blocked,
            was_blocked=was_blocked,
            changed=True,
            details=details,
        )

    # ------------------------------------------------------------------ #
    def status(self, ctn: str) -> Dict[str, Any]:
        """Текущее состояние блокировки и баланс — для диагностики."""
        binding = self._mapper.bind_subscriber(ctn)
        account = self._client.users.get_account(binding.account_id)
        return {
            "ctn": binding.ctn,
            "user_id": binding.user_id,
            "account_id": account.account_id,
            "balance": account.balance,
            "credit": account.credit,
            "available_funds": account.available_funds,
            "block_type": account.block_type,
            "is_blocked": account.is_blocked,
            "blocks": self._client.blocks.get_blocks_info(account.account_id),
        }

    # ------------------------------------------------------------------ #
    @staticmethod
    def desired_state_from_balance(balance: float, credit: float, threshold: float = 0.0) -> bool:
        """
        Подсказка для автоблокировки: True, если денег меньше порога.

        Вынесено сюда, чтобы политика была в одном месте, а не в контроллере.
        """
        return (balance + credit) < threshold