from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .errors import UTM5BadRequest
from .models import UTM5Account
from .transport import UTM5Transport

logger = logging.getLogger(__name__)

BLOCK_NONE = 0
BLOCK_ADMIN = 1
BLOCK_VOLUNTARY = 2
BLOCK_KEEP_CHARGES = 3


class BlockRepository:
    """Управление блокировками лицевого счёта."""

    def __init__(self, transport: UTM5Transport):
        self._transport = transport

    # ------------------------------------------------------------------ #
    def block(
        self,
        account: UTM5Account,
        *,
        block_type: int = BLOCK_VOLUNTARY,
        start_ts: int = 0,
        end_ts: int = 0,
    ) -> Dict[str, Any]:
        """
        Ставит блокировку на счёт.

        start_ts/end_ts — unix-время начала и конца; нули означают
        «прямо сейчас и бессрочно».
        """
        if block_type == BLOCK_NONE:
            raise UTM5BadRequest("UTM5: для снятия блокировки используйте unblock()")
        logger.info("UTM5: блокирую счёт %s (тип %s)", account.account_id, block_type)
        return self._update_account(account, block_type=block_type, start_ts=start_ts, end_ts=end_ts)

    def unblock(self, account: UTM5Account) -> Dict[str, Any]:
        """Снимает блокировку — выставляет block_type = 0."""
        logger.info("UTM5: снимаю блокировку со счёта %s", account.account_id)
        return self._update_account(account, block_type=BLOCK_NONE)

    # ------------------------------------------------------------------ #
    def get_blocks_info(self, account_id: int) -> List[Dict[str, Any]]:
        """GET users/blocks_info — история и активные блокировки счёта."""
        body = self._transport.get("users/blocks_info", {"account_id": account_id})
        if isinstance(body, list):
            return [item for item in body if isinstance(item, dict)]
        return [body] if isinstance(body, dict) and body else []

    def delete_block(self, block_id: int) -> Dict[str, Any]:
        """DELETE users/blocks — удалить запись о блокировке по её id."""
        if not block_id:
            raise UTM5BadRequest("UTM5: не указан block_id")
        body = self._transport.delete("users/blocks", {"block_id": block_id})
        return body if isinstance(body, dict) else {"result": body}

    # ------------------------------------------------------------------ #
    def _update_account(
        self,
        account: UTM5Account,
        *,
        block_type: int,
        start_ts: int = 0,
        end_ts: int = 0,
    ) -> Dict[str, Any]:
        """
        PUT users/accounts перезаписывает карточку счёта целиком, поэтому
        неизменяемые поля берём из уже прочитанного объекта — иначе биллинг
        обнулит кредит, НДС и номер договора.
        """
        raw = account.raw or {}
        payload: Dict[str, Any] = {
            "account_id": account.account_id,
            "user_id": account.user_id,
            "block_type": block_type,
            "balance": account.balance,
            "credit": account.credit,
            "vat_rate": raw.get("vat_rate", 0.0),
            "sale_tax_rate": raw.get("sale_tax_rate", 0.0),
            "int_status": raw.get("int_status", 1),
            "unlimited": bool(raw.get("unlimited", False)),
            "auto_enable_inet": bool(raw.get("auto_enable_inet", False)),
            "external_id": account.external_id,
            "contract_number": account.contract_number,
            "signature_date": raw.get("signature_date", 0),
            "contract_close_date": raw.get("contract_close_date", 0),
        }
        if block_type != BLOCK_NONE:
            payload["block_start"] = start_ts
            payload["block_end"] = end_ts

        body = self._transport.put("users/accounts", payload)
        return body if isinstance(body, dict) else {"result": body}